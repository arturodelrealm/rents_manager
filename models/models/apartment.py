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

    @staticmethod
    def clean_address(address: str) -> str:
        """Method intended for the address search."""
        return address.lower().strip()

    @property
    def cleaned_address(self) -> str:
        return self.clean_address(self.address)

    @property
    def active_contracts(self):
        return self.contracts.filter(end_date__isnull=True)

    def __str__(self):
        return f'{self.address}'
