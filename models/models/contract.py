from datetime import date
from decimal import Decimal
from typing import List, Dict

from dateutils import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from result import Ok, Result

from utils import format_int_to_price
from .apartment import Apartment
from .person import Person
from .historical_price import HistoricalPrice
from .economic_indicator import EconomicIndicator
from ..constants import PriceUpdateFrequency, ChargeTarget


class Contract(models.Model):
    DEFAULT_COMMISSION = Decimal('6.00')

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
    commission = models.DecimalField(
        _('Comisión'),
        max_digits=4,
        decimal_places=2,
        default=DEFAULT_COMMISSION,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Porcentaje de comisión sobre el valor del arriendo.')
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
    def current_price(self) -> HistoricalPrice:
        return self.historical_prices.filter(
            date__lte=date.today()
        ).order_by('-date').first()

    @property
    def price(self) -> Decimal:
        current_price = self.current_price
        return current_price.price if current_price else None

    @property
    def formatted_price(self) -> str:
        price = self.price
        return self.format_int_price(int(price)) if \
            self.price else _('No tiene precio')

    @staticmethod
    def format_int_price(price: int) -> str:
        return format_int_to_price(price)

    @property
    def number_of_months_for_ipc_update(self) -> int:
        return int(self.price_update_frequency.replace('M', ''))

    def must_update_price_by_ipc(self, update_month: date = None) -> bool:
        update_date = update_month or date.today().replace(day=1)
        # TODO: validation of the IPC existance for the 8th day
        return update_date >= self.next_price_update

    @staticmethod
    def filter_active_contracts(queryset):
        """Return a filtered queryset with only the active contracts."""
        return queryset.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date.today()),
            start_date__lte=date.today(),
        )

    @classmethod
    def get_active_contracts(cls, with_prices=True):
        """Return all contracts that are active."""
        active_contracts = cls.filter_active_contracts(cls.objects)
        if with_prices:
            active_contracts = active_contracts.filter(
                historical_prices__isnull=False).distinct()
        return active_contracts

    @classmethod
    def update_prices_by_ipc(cls) -> Result:
        updated_contracts = set()
        last_month_with_ipc = EconomicIndicator.get_latest_month_with_ipc(12)
        if last_month_with_ipc.is_err():
            return last_month_with_ipc
        last_month_with_ipc = last_month_with_ipc.ok()
        # The last updatable month is the next of the last IPC value.
        month = last_month_with_ipc + relativedelta(months=1)
        for contract in cls.get_active_contracts(True):
            # Update the contract while it must be updated. (Case when more
            # than one update time has passed since the last price update).
            while contract.must_update_price_by_ipc(month):
                contract.update_price(contract.next_price_update)
                updated_contracts.add(contract.id)
        return_data = {
            'total_contracts_updated': len(updated_contracts),
            'month_updated': month
        }
        return Ok(return_data)

    def update_price(self, month: date):
        month = month.replace(day=1)
        current_price = self.current_price
        if current_price is None:
            return

        ipc_variance = EconomicIndicator.get_n_months_ipc_multiplier(
            self.number_of_months_for_ipc_update,
            month
        )
        new_price = current_price.price * ipc_variance
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

    def get_commission(self) -> Decimal:
        """Return the commission that the client must pay as multiplier,
        not as percent"""
        return self.commission / 100

    @property
    def commission_amount(self) -> Decimal:
        return self.price * self.get_commission()

    def get_owner_other_charges_data(self) -> Dict:
        charges = self.get_other_charges(ChargeTarget.OWNER)
        other_charges_discount = sum(
            charge.amount for charge in charges
            if not charge.is_credit
        )
        other_charges_credit = sum(
            charge.amount for charge in charges
            if charge.is_credit
        )
        other_charges_net = other_charges_credit - other_charges_discount
        return {
            'credit': other_charges_credit,
            'discount': other_charges_discount,
            'net': other_charges_net,
        }

    @property
    def formatted_commission_amount(self) -> str:
        return self.format_int_price(int(self.commission_amount))

    @property
    def net_price(self) -> Decimal:
        return self.price - self.commission_amount

    @property
    def owner_net_price(self) -> Decimal:
        owner_other_charges = self.get_owner_other_charges_data()
        return self.net_price + owner_other_charges['net']

    @property
    def formatted_owner_net_price(self) -> str:
        return self.format_int_price(int(self.owner_net_price))

    def get_other_charges(self, target: ChargeTarget = None) -> List:
        charges = self.charges.all()
        if target:
            charges = charges.filter(target=target)
        return [charge for charge in charges if charge.is_active()]

    @staticmethod
    def format_charge(charge) -> str:
        return charge.display_resume()

    def get_rent_resume(self) -> str:
        lines = [
            f"  * Propiedad: {self.apartment.address}",
            f"  - Arriendo:        {self.formatted_price}"
        ]
        lines.extend(
            map(
                self.format_charge,
                self.get_other_charges(ChargeTarget.OWNER)
            )
        )
        lines.append(
            f"  - Comisión:       -{self.formatted_commission_amount}"
        )
        lines.append(f"  - Neto:            {self.formatted_owner_net_price}")
        lines.append("")
        return '\n'.join(lines)
