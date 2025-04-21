from django.contrib import admin

from .person import PersonAdmin
from .contract import ContractAdmin
from .economic_indicator import EconomicIndicator, EconomicIndicatorAdmin
from models.models import Person, Apartment, Contract

admin.site.register(Person, PersonAdmin)
admin.site.register(Contract, ContractAdmin)
admin.site.register(EconomicIndicator, EconomicIndicatorAdmin)
admin.site.register(Apartment)
