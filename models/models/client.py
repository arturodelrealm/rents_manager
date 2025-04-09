from django.db import models
from django.utils.translation import gettext_lazy as _


class Client(models.Model):
    name = models.CharField(_('Nombre'), max_length=100)
    email = models.EmailField(_('Email'), unique=True)
    phone = models.CharField(_('Teléfono'), max_length=15, null=True)
    rut = models.CharField(_('RUT'), unique=True, null=True)

    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')

    def __str__(self):
        return self.name
