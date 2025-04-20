from datetime import date
from decimal import Decimal

from django.apps import apps
from django.db import models
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from utils import format_int_to_price
from validations.rut import RutValidator


class Person(models.Model):
    name = models.CharField(_('Nombre'), max_length=100)
    last_name = models.CharField(_('Apellido'), max_length=100, blank=True)
    email = models.EmailField(_('Email'), unique=True)
    phone = PhoneNumberField(_('Teléfono'), blank=True)
    rut = models.CharField(
        _('RUT'),
        unique=True,
        max_length=15,
        null=True,
        validators=[RutValidator.validator]
    )

    class Meta:
        verbose_name = _('Persona')
        verbose_name_plural = _('Personas')

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.last_name}"

    def save(self, *args, **kwargs):
        if self.rut:
            self.rut = RutValidator.clean_rut(self.rut)
        super().save(*args, **kwargs)

    @property
    def is_owner(self) -> bool:
        return self.apartments.exists()

    def owner_contracts(self, month: date):
        contract_model = apps.get_model('models', 'Contract')
        return contract_model.objects.filter(
            apartment__owner_id=self.id,
            end_date__isnull=True,
            start_date__lte=month
        )

    def owner_email_text(self, month: date = None) -> str:
        """"""
        month = month or date.today()
        contracts = list(self.owner_contracts(month).iterator())
        net_total = Decimal('0')
        total_rent = Decimal('0')
        total_commission = Decimal('0')
        total_credit = Decimal('0')
        total_discount = Decimal('0')
        formatted_month = date_format(
            month,
            'YEAR_MONTH_FORMAT',
            use_l10n=True
        )
        lines = [
            _(
                'Estimado/a {}, el resumen del mes de {} de sus propiedades '
                'ubicadas en:\n'
            ).format(self.name, formatted_month)
        ]
        for contract in contracts:
            # Basic contract amounts
            net_total += contract.net_price
            total_rent += contract.price
            total_commission += contract.commission_amount

            # Other charges amounts
            charges_data = contract.get_owner_other_charges_data()
            total_credit += charges_data['credit']
            total_discount += charges_data['discount']
            net_total += charges_data['net']

            # Add contract resume
            lines.append(
                contract.get_rent_resume()
            )

        lines.append("\n")
        lines.append(f"Total rentas: {format_int_to_price(int(total_rent))}")
        if total_credit > 0:
            lines.append(
                f"Total abonos: {format_int_to_price(int(total_credit))}"
            )

        if total_discount > 0:
            lines.append(
                f"Total descuentos: {format_int_to_price(int(total_discount))}"
            )

        lines.append(
            f"Total comisión: {format_int_to_price(int(total_commission))}"
        )
        lines.append(f"Total a pagar: {format_int_to_price(int(net_total))}")
        return '\n'.join(lines)
