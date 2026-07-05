from django.contrib import admin

from outfit.models import Clothing, DressRule, Location

admin.site.register(Location)
admin.site.register(DressRule)
admin.site.register(Clothing)
