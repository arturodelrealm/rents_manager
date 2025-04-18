from typing import Any

from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from models.models import Contract, HistoricalPrice


class ContractForm(forms.ModelForm):
    price = forms.IntegerField(
        label=_("Precio"),
        required=True,
    )
    price_date = forms.DateField(
        label=_('Fecha del precio'),
        help_text=_('Fecha desde cuando el precio actual está activo.'),
        widget=forms.DateInput(attrs={'type': 'month'}),
        required=False
    )
    reason = forms.CharField(
        label=_('Motivo cambio de precio'),
        help_text=_('Motivo del cambio de precio (IPC, acuerdo mutuo, etc).'),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.is_creation = False
            current_price = self.instance.current_price
            if current_price:
                self.fields['price'].initial = int(current_price.price)
                self.fields['price_date'].initial = current_price.date
        else:
            self.is_creation = True
            self.fields['price_date'].widget = forms.HiddenInput()
            self.fields['reason'].widget = forms.HiddenInput()

    def validate_owner_is_not_tenant(self):
        if self.errors:
            return
        apartment = self.cleaned_data.get('apartment')
        tenants = self.cleaned_data.get('tenants')
        if not apartment or tenants is None:
            return
        owner_id = apartment.owner_id
        if tenants.filter(pk=owner_id).exists():
            self.add_error(
                'tenants',
                _('El arrendatario no puede ser el propietario del inmueble.')
            )

    def validate_property_has_no_other_contracts(self):
        if self.errors:
            return
        apartment = self.cleaned_data.get('apartment')
        if not apartment:
            return
        start_date = self.cleaned_data['start_date']
        property_id = self.cleaned_data['apartment'].id
        property_contracts = Contract.objects.filter(apartment_id=property_id)
        overlapping_contracts = property_contracts.filter(
            Q(start_date__lte=start_date) & (
                    Q(end_date__gte=start_date) |
                    Q(end_date__isnull=True)
            )
        ).exclude(pk=self.instance.pk)
        if overlapping_contracts.exists():
            error_message = _(
                'Ya existe un contrato para esta propiedad en la fecha '
                'seleccionada.'
            )
            self.add_error(
                'start_date',
                error_message
            )

    def validate_reason(self):
        reason = (self.cleaned_data.get('reason') or '').strip()
        if 'price' in self.changed_data and self.instance.pk:
            if not reason:
                error_message = _(
                    'Si se modifica el precio se debe ingresar un motivo.'
                )
                self.add_error('reason', error_message)

    def validate_price_date(self):
        price_date = self.cleaned_data.get('price_date')
        if not price_date:
            return
        if price_date < self.cleaned_data['start_date']:
            error_message = _(
                'La fecha del precio no puede ser anterior a la fecha de '
                'inicio del contrato.'
            )
            self.add_error('price_date', error_message)

    def clean(self) -> dict[str, Any] | None:
        super().clean()
        if self.errors:
            return
        self.validate_reason()
        self.validate_price_date()
        self.validate_owner_is_not_tenant()
        self.validate_property_has_no_other_contracts()
        return self.cleaned_data

    def save(self, commit: bool = True):
        obj = super().save(commit)

        if commit:
            self.save_historical_price(obj)
        return obj

    def save_historical_price(self, obj):
        new_price = self.cleaned_data.get('price')
        old_price = obj.price

        if new_price and new_price != old_price:
            if self.is_creation:
                reason = _('Precio inicial')
                price_date = obj.infer_last_price_update()
            else:
                reason = self.cleaned_data.get('reason')
                price_date = self.cleaned_data.get('price_date')
            data = {
                'price': new_price,
                'reason': reason,
                'date': price_date,
                'contract_id': obj.pk,
            }
            HistoricalPrice.create(data)

    class Meta:
        model = Contract
        fields = '__all__'


class ImportContractForm(ContractForm):

    NOT_REQUIRED_FIELDS = (
        'tenants',
        'apartment'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.NOT_REQUIRED_FIELDS:
            self.fields[field_name].required = False
