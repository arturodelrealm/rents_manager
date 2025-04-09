from admin_extra_buttons.api import ExtraButtonsMixin, button
from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from models.models import EconomicIndicator


class EconomicIndicatorAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ('indicator_type', 'date', 'display_value')
    change_list_template = 'admin/models/economicindicator/change_list.html'

    def display_value(self, obj):
        return obj.display_value()

    display_value.short_description = _('Valor')

    def changelist_view(self, request, extra_context=None):
        indicators_text = "<br>".join(
            f"{label}: {value}"
            for label, value in
            EconomicIndicator.get_useful_economic_indicators()
        )
        extra_context = extra_context or {}
        extra_context["indicators_info"] = mark_safe(indicators_text)

        return super().changelist_view(request, extra_context=extra_context)

    @button(label=_('Cargar Datos del INE'))
    def update_ipc(self, request):
        EconomicIndicator.add_last_year_ipcs()
        messages.add_message(request, messages.SUCCESS, _('IPC actualizado'))
