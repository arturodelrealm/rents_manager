from django.contrib import admin


class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
