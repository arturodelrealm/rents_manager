from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

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
