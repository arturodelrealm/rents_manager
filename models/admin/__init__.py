from django.contrib import admin

from .client import ClientAdmin
from .contract import Contract, ContractAdmin
from .economic_indicator import EconomicIndicator, EconomicIndicatorAdmin
from models.models import Client, Tenant, Apartment

admin.site.register(Client, ClientAdmin)
admin.site.register(Tenant, ClientAdmin)
admin.site.register(Contract, ContractAdmin)
admin.site.register(EconomicIndicator, EconomicIndicatorAdmin)

admin.site.register(Apartment)
