from django import forms
from django.core.exceptions import ValidationError

from models.models import Apartment
from django.utils.translation import gettext_lazy as _


class ApartmentForm(forms.ModelForm):

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if not address:
            return
        cleaned_address = Apartment.clean_address(address)
        if Apartment.objects.filter(address__iexact=cleaned_address).exclude(
                pk=self.instance.pk
        ):
            raise ValidationError(
                _('Ya existe un departamento con esta dirección.')
            )
        return address

    class Meta:
        model = Apartment
        fields = '__all__'


class ImportApartmentForm(ApartmentForm):
    class Meta:
        model = Apartment
        exclude = ('owner',)
