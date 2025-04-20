from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from models.constants import ChargeTarget
from utils import format_int_to_price


class Charge(models.Model):

    contract = models.ForeignKey(
        'Contract',
        related_name='charges',
        on_delete=models.CASCADE,
        verbose_name=_("Contrato")
    )
    description = models.CharField(
        max_length=255,
        verbose_name=_("Descripción")
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Monto"),
        validators=[MinValueValidator(0)]
    )
    is_credit = models.BooleanField(
        default=False,
        verbose_name=_("¿Es abono?"),
        help_text=_(
            'Si es abono entonces es un saldo a favor sobre quien se aplica '
            'el cargo.'
        )
    )
    start_date = models.DateField(
        verbose_name=_("Fecha de inicio")
    )
    end_date = models.DateField(
        verbose_name=_("Fecha de término"),
        null=True
    )
    target = models.CharField(
        max_length=10,
        choices=ChargeTarget.choices,
        default=ChargeTarget.OWNER,
        verbose_name=_("Aplicar a")
    )

    class Meta:
        verbose_name = _("Cargo del contrato")
        verbose_name_plural = _("Cargos del contrato")
        ordering = ['-start_date']

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': _(
                        'La fecha de término debe ser posterior a la fecha de'
                        ' inicio.'
                    )
                })

    def is_active(self, on: date = None) -> bool:
        if self.start_date is None:
            return False
        on = on or date.today()
        return self.start_date <= on and \
            (self.end_date is None or self.end_date >= on)

    @property
    def real_amount(self) -> Decimal:
        return self.amount if self.is_credit else -self.amount

    @property
    def formatted_amount(self) -> str:
        return f'{self.sign}{format_int_to_price(int(self.amount))}'

    @property
    def sign(self) -> str:
        return " " if self.is_credit else "-"

    def display_resume(self) -> str:
        description = f'{self.description}:'
        return f'  - {description:<15} {self.formatted_amount}'

    def __str__(self):
        active_period = f'Desde: {self.start_date}'
        if self.end_date:
            active_period += f' - Hasta: {self.end_date}'
        return f"{self.get_target_display()}: {self.description} " \
            f"{self.formatted_amount} ({active_period})"
