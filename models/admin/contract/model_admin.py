from datetime import date

import tablib
from admin_extra_buttons.api import ExtraButtonsMixin, button
from django.contrib import admin, messages
from django.db.models import Prefetch
from django.http import HttpResponse, HttpRequest
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportMixin

from models.forms import ContractForm
from models.import_export_resources.contract import UnifiedContractResource
from models.models import Contract, HistoricalPrice
from .inlines import ChargeInline, CommentInline, HistoricalPriceInline
from .filters import IsActiveFilter, RecentlyUpdatedFilter


class ContractAdmin(ImportMixin, ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "apartment_address",
        "owner",
        'tenant',
        "current_price",
        'next_price_update_formatted',
    )
    fields = [
        'apartment',
        'tenants',
        ('start_date', 'end_date', 'next_price_update'),
        'price_update_frequency',
        'price',
        ('price_date', 'reason'),
        'commission',
    ]
    search_fields = [
        'apartment__address',
        'apartment__owner__name',
        'apartment__owner__last_name',
        'tenants__name',
        'tenants__last_name',
    ]
    list_filter = [IsActiveFilter, RecentlyUpdatedFilter]
    form = ContractForm
    resource_classes = [UnifiedContractResource]
    skip_admin_log = True
    inlines = [ChargeInline, CommentInline, HistoricalPriceInline]
    list_select_related = ('apartment', 'apartment__owner')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        historical_qs = HistoricalPrice.objects.filter(
            date__lte=date.today()
        ).order_by('-date')
        return qs.prefetch_related(
            Prefetch(
                'historical_prices',
                queryset=historical_qs,
                to_attr='prefetched_prices'
            ),
            'tenants'
        )

    def get_fields(self, request: HttpRequest, obj: None = ...):
        if not obj:
            return self.fields
        # Remove apartments selector if the contract is already created
        return [field for field in self.fields if field != 'apartment']

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

    @button(label=_('Actualizar precios según IPC'))
    def update_ipc(self, request):
        result = Contract.update_prices_by_ipc()
        if result.is_ok():
            update_data = result.ok()

            total_contracts_updated = update_data['total_contracts_updated']
            month_updated = update_data['month_updated']
            messages.success(
                request,
                _('Precios de {} contratos actualizados').format(
                    total_contracts_updated
                )
            )
            messages.info(
                request,
                _(
                    'Los precios fueron actualizados para el último'
                    ' mes con datos del IPC ({}).'
                ).format(
                    date_format(
                        month_updated,
                        'YEAR_MONTH_FORMAT',
                        use_l10n=True)
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

    def tenant(self, obj):
        tenants = list(obj.tenants.all())

        first_tenant = tenants[0] if tenants else None
        if len(tenants) > 1:
            return f'{first_tenant} (+{len(tenants) - 1})'
        return first_tenant

    def owner(self, obj):
        return obj.apartment.owner

    def apartment_address(self, obj):
        return obj.apartment.address

    current_price.short_description = _("Precio actual")
    owner.short_description = _('Propietario')
    tenant.short_description = _('Arrendatario')
    next_price_update_formatted.short_description = _('Próximo ajuste')
    apartment_address.short_description = _('Departamento')
