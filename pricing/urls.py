from django.urls import path
from .views import PricingCalculateView

urlpatterns = [
    path('calculate/', PricingCalculateView.as_view(), name='pricing-calculate'),
]
