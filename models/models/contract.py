from datetime import date
from decimal import Decimal

from dateutils import relativedelta
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from result import Ok, Err, Result

from .apartment import Apartment
from .person import Person
from .historical_price import HistoricalPrice
from .economic_indicator import EconomicIndicator
from ..constants import PriceUpdateFrequency


class Contract(models.Model):

    tenants = models.ManyToManyField(
        Person,
        related_name='contracts',
        verbose_name=_('Arrendatarios')
    )
    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name=_('Departamento')
    )
    start_date = models.DateField(_('Fecha Inicio'))
    end_date = models.DateField(_('Fecha Término'), null=True, blank=True)
    next_price_update = models.DateField(_('Próximo ajuste'), null=True)

    price_update_frequency = models.CharField(
        _('Frecuencia de actualización de precio'),
        max_length=7,
        choices=PriceUpdateFrequency.choices,
        default=PriceUpdateFrequency.MONTHLY,
    )

    class Meta:
        verbose_name = _('Contrato')
        verbose_name_plural = _('Contratos')

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': _(
                        'La fecha de término debe ser posterior a la fecha de'
                        ' inicio.'
                    )
                })

    def __str__(self):
        return _('Contrato: {} ({})').format(
            self.apartment,
            self.formatted_price
        )

    @property
    def last_price(self) -> HistoricalPrice:
        return self.historical_prices.order_by('-date').first()

    @property
    def price(self) -> Decimal:
        last_price = self.last_price
        return last_price.price if last_price else None

    @property
    def formatted_price(self) -> str:
        price = self.price
        return self.format_int_price(int(price)) if \
            self.price else _('No tiene precio')

    @staticmethod
    def format_int_price(price: int) -> str:
        return f'{price:,}$'.replace(',', '.')

    @property
    def number_of_months_for_ipc_update(self) -> int:
        return int(self.price_update_frequency.replace('M', ''))

    def must_update_price_by_ipc(self, update_month: date = None) -> bool:
        update_date = update_month or date.today().replace(day=1)
        # TODO: validation of the IPC existance for the 8th day
        if self.next_price_update is not None:
            return update_date >= self.next_price_update
        last_price_update = self.last_price.date
        month_difference = (update_date.year - last_price_update.year) * 12 \
            + (update_date.month - last_price_update.month)
        return month_difference >= self.number_of_months_for_ipc_update

    @classmethod
    def update_prices_by_ipc(cls, month: date = None) -> Result:
        month = month or date.today()
        updated_contracts = set()
        if not EconomicIndicator.check_month_ipc_exists(month, True, 12):
            return Err(
                _('No existe el valor del IPC para actualizar los precios del '
                  'mes de {}. Puede ir a indicadores Económicos a obtener los '
                  'datos').format(
                    date_format(month, 'YEAR_MONTH_FORMAT', use_l10n=True)
                )
            )
        for contract in cls.objects.all():
            # Update the contract while it must be updated. (Case when more
            # than one update time has passed since the last price update).
            while contract.must_update_price_by_ipc(month):
                contract.update_price(contract.next_price_update)
                updated_contracts.add(contract.id)

        return Ok(len(updated_contracts))

    def update_price(self, month: date):
        month = month.replace(day=1)
        last_price = self.last_price
        if last_price is None:
            return

        ipc_variance = EconomicIndicator.get_n_months_ipc_multiplier(
            self.number_of_months_for_ipc_update,
            month
        )
        new_price = last_price.price * ipc_variance
        reason = _(
            'Actualización por IPC de {}.'
        ).format(
            EconomicIndicator.decimal_to_percentage((ipc_variance - 1) * 100)
        )
        with transaction.atomic():
            data = {
                'contract_id': self.id,
                'date': month,
                'price': new_price,
                'reason': reason,
            }
            HistoricalPrice.create(data)
            self.next_price_update = month + relativedelta(
                months=self.number_of_months_for_ipc_update
            )
            self.save()

    def infer_last_price_update(self) -> date:
        return max(
            self.start_date,
            self.next_price_update - relativedelta(
                months=self.number_of_months_for_ipc_update
            )
        )
