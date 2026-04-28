from django.contrib import admin
from .models import CustomerSegment, PromoCode, StaffTask, SeasonPriceRule, DynamicPriceRule

admin.site.register(CustomerSegment)
admin.site.register(PromoCode)
admin.site.register(StaffTask)
admin.site.register(SeasonPriceRule)
admin.site.register(DynamicPriceRule)
