from django.db import models
from django.utils.translation import gettext_lazy as _


class HistoricalPrice(models.Model):
    contract = models.ForeignKey(
        "Contract",
        on_delete=models.CASCADE,
        related_name="historical_prices",
        verbose_name=_("Contrato")
    )
    date = models.DateField(verbose_name=_("Fecha"))
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Precio")
    )
    reason = models.CharField(
        max_length=255,
        verbose_name=_("Motivo"),
        blank=True,
        null=True,
        help_text=_(
            "Motivo del cambio de precio (IPC, acuerdo mutuo, etc)."
        )
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = _("Precio histórico")
        verbose_name_plural = _("Precios históricos")

    def __str__(self):
        return f"{self.contract} - {self.date}: {self.price}"
