from django.urls import path
from .views import PricingCalculateView, ScooterRentalRateListView

urlpatterns = [
    path('calculate/', PricingCalculateView.as_view(), name='pricing-calculate'),
    path('rental-rates/', ScooterRentalRateListView.as_view(), name='pricing-rental-rates'),
]
