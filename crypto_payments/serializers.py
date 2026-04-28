from rest_framework import serializers
from .models import CryptoCurrency, CryptoInvoice

class CryptoCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoCurrency
        fields = ['id', 'code', 'name', 'network']

class CryptoInvoiceCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    currency_id = serializers.IntegerField()

class CryptoInvoiceResponseSerializer(serializers.ModelSerializer):
    currency = CryptoCurrencySerializer(read_only=True)
    
    class Meta:
        model = CryptoInvoice
        fields = [
            'provider_invoice_id', 'amount_usd', 'amount_crypto', 
            'currency', 'address', 'payment_url', 'status', 'expires_at'
        ]

class CryptoInvoiceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoInvoice
        fields = ['status', 'provider_invoice_id']
