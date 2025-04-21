from datetime import date, datetime

from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.formats import date_format
from dateutils import relativedelta


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


class RecentlyUpdatedFilter(admin.SimpleListFilter):
    title = _('Precio Actualizado En')
    parameter_name = 'price_updated_on'

    MONTH_VALUE_FORMAT = '%Y-%m'

    def lookups(self, request, model_admin):
        this_month = date.today().replace(day=1)
        last_3_months = [
            this_month - relativedelta(months=month_diff)
            for month_diff in range(3)
        ]
        return [
            (
                month.strftime(self.MONTH_VALUE_FORMAT),
                date_format(month, 'YEAR_MONTH_FORMAT', use_l10n=True),
            )
            for month in last_3_months
        ]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        try:
            month = datetime.strptime(
                self.value(), self.MONTH_VALUE_FORMAT).date()
        except ValueError:
            return queryset
        return queryset.filter(
            historical_prices__date__gte=month,
            historical_prices__date__lt=month + relativedelta(months=1),
        ).distinct()
