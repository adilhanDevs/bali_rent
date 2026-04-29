from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CryptoInvoiceCreateView, CryptoInvoiceStatusView, CryptoWebhookView,
    CryptoCurrencyViewSet
)

router = DefaultRouter()
router.register(r'currencies', CryptoCurrencyViewSet, basename='crypto-currency')

urlpatterns = [
    path('', include(router.urls)),
    path('invoice/create/', CryptoInvoiceCreateView.as_view(), name='crypto-invoice-create'),
    path('invoice/<str:provider_invoice_id>/status/', CryptoInvoiceStatusView.as_view(), name='crypto-invoice-status'),
]
