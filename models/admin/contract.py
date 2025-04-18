import tablib
from admin_extra_buttons.api import ExtraButtonsMixin, button
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportMixin

from models.forms import ContractForm
from models.import_export_resources.contract import UnifiedContractResource
from models.models import Contract


class ContractAdmin(ImportMixin, ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "apartment",
        "current_price",
        'next_price_update_formatted',
    )
    form = ContractForm
    resource_classes = [UnifiedContractResource]
    skip_admin_log = True

    def save_model(self, request, obj, form, change):
        obj.save()
        form.save_historical_price(obj)
        return obj

    @button(label=_('Descargar excel de ejemplo'))
    def download_example_excel(self, __):

        data = tablib.Dataset(headers=UnifiedContractResource.FILE_HEADERS)

        response = HttpResponse(
            data.export("xlsx"),
            content_type="application/vnd.ms-excel"
        )
        response[
            "Content-Disposition"
        ] = 'attachment; filename="plantilla_importacion.xlsx"'
        return response

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

    def owner(self, obj):
        return obj.apartment.owner

    current_price.short_description = _("Precio actual")
    owner.short_description = _('Propietario')
    next_price_update_formatted.short_description = _('Próximo ajuste')
