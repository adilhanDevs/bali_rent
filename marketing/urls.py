from django.urls import path

from .views import PromoCodeValidateView

urlpatterns = [
    path('promocodes/validate/', PromoCodeValidateView.as_view(), name='promocode-validate'),
]
