from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from models.forms import PersonForm
from models.models import Person


class IsOwnerFilter(admin.SimpleListFilter):
    title = _('Es propietario')
    parameter_name = 'is_owner'

    def lookups(self, request, model_admin):
        return [
            ('yes', _('Sí')),
            ('no', _('No')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(apartments__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(apartments__isnull=True)
        return queryset


class PersonAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'email',
        'rut',
        'phone',
        'is_owner',
        'is_tenant',
    )

    list_filter = [IsOwnerFilter]
    show_facets = admin.ShowFacets.NEVER
    search_fields = ['name', 'last_name', 'email', 'rut']

    readonly_fields = ('show_owner_email',)

    fieldsets = [
        (
            None,
            {
                "fields": [
                    'name',
                    'last_name',
                    'email',
                    'rut',
                ],
            },
        ),
        (
            _("Previsualización Mails"),
            {
                "classes": ["collapse"],
                "fields": ["show_owner_email"],
            },
        ),
    ]

    form = PersonForm

    def full_name(self, obj):
        return obj.full_name

    def get_fieldsets(self, request: HttpRequest, obj=None):
        # Only show mails if the user is owner
        if obj is None or not obj.is_owner:
            return self.fieldsets[:1]
        return self.fieldsets

    def is_owner(self, obj: Person) -> bool:
        return obj.is_owner if obj else False

    def is_tenant(self, obj: Person) -> bool:
        return obj.contracts.exists() if obj else False

    def show_owner_email(self, obj):
        text = obj.owner_email_text()
        # Try to show all the mail with a small margin (adding 2).
        # Maybe this could be done with js, but I like this solution
        aprox_size = text.count('\n') + 2
        message = escape(text)

        return mark_safe(f"""
            <textarea rows="{aprox_size}" cols="80" 
            style="font-family: monospace;"
            >{message}</textarea>
        """)

    full_name.short_description = _("Nombre")
    is_owner.short_description = _("Es propietario?")
    is_owner.boolean = True
    is_tenant.short_description = _("Es arrendatario?")
    is_tenant.boolean = True
    show_owner_email.short_description = _('Mail al propietario')
