from django.db import models
from django.utils.translation import gettext_lazy as _


class PriceUpdateFrequency(models.TextChoices):
    # NOTE: part of the code assumes the format {Number}M tow ork properly
    MONTHLY = '1M', _('Cada 1 mes')
    QUARTERLY = '3M', _('Cada 3 meses')
    SEMIANNUALLY = '6M', _('Cada 6 meses')
    ANNUALLY = '12M', _('Cada 12 meses')


class EconomicIndicatorType(models.TextChoices):
    IPC = 'IPC', _('Índice Precio del Consumidor')
    UF = 'UF', _('Unidad de Fomento')
