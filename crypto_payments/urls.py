from django.urls import path
from .views import (
    CryptoInvoiceCreateView, CryptoInvoiceStatusView, CryptoWebhookView
)

urlpatterns = [
    path('invoice/create/', CryptoInvoiceCreateView.as_view(), name='crypto-invoice-create'),
    path('invoice/<str:provider_invoice_id>/status/', CryptoInvoiceStatusView.as_view(), name='crypto-invoice-status'),
]
