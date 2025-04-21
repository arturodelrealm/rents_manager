from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from models.models import Charge, Comment, HistoricalPrice


class ChargeInline(admin.StackedInline):
    model = Charge
    extra = 0
    ordering = ('-start_date',)
    readonly_fields = ('is_active',)
    classes = ['collapse']

    def is_active(self, obj: Charge) -> bool:
        return obj.is_active()

    is_active.boolean = True
    is_active.short_description = _('¿Está activo?')


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    readonly_fields = ('created_at',)
    classes = ['collapse']


class HistoricalPriceInline(admin.TabularInline):
    model = HistoricalPrice
    extra = 0
    ordering = ('-date',)
    readonly_fields = ('date', 'price', 'reason')
    classes = ['collapse']