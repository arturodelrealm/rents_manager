from decimal import Decimal
from datetime import date
from typing import Generator, Optional, Iterable, Tuple, List

from dateutils import relativedelta
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..constants import EconomicIndicatorType
from services.economic_indicators import IPCService


class EconomicIndicator(models.Model):
    indicator_type = models.CharField(
        max_length=10,
        choices=EconomicIndicatorType.choices,
        verbose_name=_("Tipo indicador")
    )
    date = models.DateField(verbose_name=_("Fecha"))
    value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name=_("Valor")
    )

    class Meta:
        unique_together = ('indicator_type', 'date')
        ordering = ['-date']
        verbose_name = _("Indicador económico")
        verbose_name_plural = _("Indicadores Económicos")

    @staticmethod
    def get_last_n_months(
            number_of_months: int,
            current_date: Optional[date] = None
    ) -> Generator[date, None, None]:
        """Yield the last N months, including the current month."""
        current_date = current_date or date.today()
        # get the actual historical month, use -1 because we want january to
        # be our month 0.
        actual_month = current_date.year * 12 + current_date.month - 1
        for month_delta in range(number_of_months, -1, -1):
            wanted_month = actual_month - month_delta

            yield date(
                year=wanted_month // 12,
                month=wanted_month % 12 + 1,
                day=1
            )

    @classmethod
    def add_last_n_months_ipc(cls, n_months: int):
        months = list(cls.get_last_n_months(n_months))
        current_ipc_values = cls.objects.filter(
            date__in=months,
            indicator_type=EconomicIndicatorType.IPC
        ).count()
        # Check if we need to update any value. If one is missing, update all
        # the values. (Not going to hurt, only 13 queries).
        if len(months) != current_ipc_values:
            ipc_values = IPCService.get_ipc_data(months[0], months[-1])
            for ipc_value in ipc_values:
                cls.objects.update_or_create(
                    defaults={'value': ipc_value.value},
                    date=ipc_value.date,
                    indicator_type=EconomicIndicatorType.IPC
                )

    @classmethod
    def add_last_year_ipcs(cls):
        # Ensure that we load all the needed ipc values, because they load the
        # ipcs on the 8th day of the month
        cls.add_last_n_months_ipc(13)

    @staticmethod
    def _calculate_accumulative_ipc(
            ipc_values: Iterable['EconomicIndicator']
    ) -> Decimal:
        accumulative_ipc = Decimal(1)
        for ipc_value in ipc_values:
            accumulative_ipc *= (1 + (ipc_value.value / 100))
        # TODO: REVIEW
        return (
                (accumulative_ipc - 1) * 100
        ).quantize(
            Decimal('0.1'),
            rounding='ROUND_FLOOR'
        )

    @classmethod
    def check_month_ipc_exists(
            cls,
            month: date,
            check_from_previous_month: bool = False,
            check_last_n_months=None
    ) -> bool:
        """Return True if the wanted month have a IPC value.
        Add check_previous_month param because sometimes we want the previous
        month ipc value."""
        month = month.replace(day=1)
        check_last_n_months = check_last_n_months or 1
        if check_from_previous_month:
            month = month - relativedelta(months=1)
        # Check if we have all the needed IPC values.
        return cls.objects.filter(
            indicator_type=EconomicIndicatorType.IPC,
            date__lte=month,
            date__gt=month - relativedelta(months=check_last_n_months),
            date__day=1
        ).count() == check_last_n_months

    @classmethod
    def get_accumulative_n_months_ipc(
            cls,
            number_of_months: int,
            month: date = None,
            use_last_ipc_value: bool = False,
    ) -> Decimal:
        # get the ipc from the last month
        month = (month or date.today()).replace(day=1)
        ipc_date = month - relativedelta(months=1)
        if use_last_ipc_value:
            previous_month_ipc_value = cls.objects.filter(
                indicator_type=EconomicIndicatorType.IPC
            ).order_by('-date').first()
        else:
            previous_month_ipc_value = cls.objects.filter(
                indicator_type=EconomicIndicatorType.IPC,
                date=ipc_date
            ).first()
        # Case when no ipc values are loaded
        if previous_month_ipc_value is None:
            return Decimal(0)
        # Get the last n ipc values. Note that we use greater than in the date
        # because we need to use the current ipc value too.
        last_n_ipc_values = cls.objects.filter(
            indicator_type=EconomicIndicatorType.IPC,
            date__gt=previous_month_ipc_value.date - relativedelta(
                months=number_of_months
            ),
            date__lte=previous_month_ipc_value.date
        )
        return cls._calculate_accumulative_ipc(last_n_ipc_values)

    @classmethod
    def get_n_months_ipc_multiplier(
            cls,
            number_of_months: int,
            month: date = None
    ) -> Decimal:
        return cls.get_accumulative_n_months_ipc(
            number_of_months, month
        ) / 100 + 1

    @staticmethod
    def decimal_to_percentage(value: Decimal) -> str:
        return f'{value:.2f}%'

    def display_value(self) -> str:
        return getattr(self, f'_display_{self.indicator_type.lower()}')()

    @classmethod
    def get_useful_economic_indicators(cls) -> List[Tuple[str, str]]:
        ipc_n_months = (3, 6, 12)
        indicators = []
        for n_months in ipc_n_months:
            indicators.append(
                (
                    _('IPC últimos {} meses').format(n_months),
                    cls.decimal_to_percentage(
                        cls.get_accumulative_n_months_ipc(
                            n_months,
                            use_last_ipc_value=True
                        )
                    )
                )
            )
        return indicators

    def _display_ipc(self) -> str:
        return self.decimal_to_percentage(self.value)

    def _display_uf(self) -> str:
        return f'${self.value:_}'

    def __str__(self):
        return f"{self.get_indicator_type_display()} - {self.date}: " \
               f"{self.display_value()}"

