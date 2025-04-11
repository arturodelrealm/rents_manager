from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class PersonAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'rut', 'phone')

    def full_name(self, obj):
        return obj.full_name

    full_name.short_description = _("Nombre")
