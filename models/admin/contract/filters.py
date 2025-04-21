from datetime import date

from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class IsActiveFilter(admin.SimpleListFilter):
    title = _('Mostrar inactivos')
    parameter_name = 'show_inactive'

    def lookups(self, request, model_admin):
        return [
            ('yes', _('Sí')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset
        return queryset.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date.today()),
            start_date__lte=date.today(),
        )