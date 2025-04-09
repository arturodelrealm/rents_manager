from typing import Any

from admin_extra_buttons.api import ExtraButtonsMixin, button
from django import forms
from django.contrib import admin, messages
from django.utils.formats import date_format
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
        required=True
    )
    reason = forms.CharField(
        label=_('Motivo cambio de precio'),
        help_text=_('Motivo del cambio de precio (IPC, acuerdo mutuo, etc).'),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            last_price = self.instance.last_price
            if last_price:
                self.fields['price'].initial = int(last_price.price)
                self.fields['price_date'].initial = last_price.date

    def clean(self) -> dict[str, Any] | None:
        reason = (self.cleaned_data.get('reason') or '').strip()
        if 'price' in self.changed_data:
            if not reason:
                error_message = _(
                    'Si se modifica el precio se debe ingresar un motivo.'
                )
                self.add_error('reason', error_message)
        # Check that the price date is after the init date

        return self.cleaned_data

    class Meta:
        model = Contract
        fields = '__all__'


class ContractAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "apartment",
        "current_price",
        'next_price_update_formatted',
    )
    form = ContractForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        new_price = form.cleaned_data.get('price')
        old_price = obj.price

        if new_price and new_price != old_price:
            defaults = {
                'price': new_price,
                'reason': form.cleaned_data.get('reason'),
            }
            HistoricalPrice.objects.update_or_create(
                defaults=defaults,
                date=form.cleaned_data.get('price_date'),
                contract_id=obj.pk
            )

    @button(label=_('Calcular precios del mes'))
    def update_ipc(self, request):
        result = Contract.update_prices_by_ipc()
        if result.is_ok():
            total_contracts_updated = result.ok()
            messages.success(
                request,
                _('Precios de {} contratos actualizados').format(
                    total_contracts_updated
                )
            )
        else:
            messages.warning(
                request,
                result.err()
            )

    def current_price(self, obj):
        return obj.formatted_price

    def next_price_update_formatted(self, obj):
        return date_format(
            obj.next_price_update,
            format='YEAR_MONTH_FORMAT',
            use_l10n=True
        )

    def client(self, obj):
        return obj.apartment.clients.first()

    current_price.short_description = _("Precio actual")
    client.short_description = _('Cliente')
    next_price_update_formatted.short_description = _('Próximo ajuste')
