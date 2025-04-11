from django.db import models
from django.utils.translation import gettext_lazy as _

from .person import Person


class Apartment(models.Model):
    owner = models.ForeignKey(
        to=Person,
        on_delete=models.PROTECT,
        verbose_name=_('Propietario'),
        related_name='apartments',
        null=True,
    )
    address = models.TextField(_('Dirección'))
    commune = models.CharField(_('Comuna'), null=True)

    class Meta:
        verbose_name = _('Departamento')
        verbose_name_plural = _('Departamentos')

    def __str__(self):
        return f'{self.address}'
