from django.db import models

class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    polygon_json = models.JSONField(blank=True, null=True)
    center_lat = models.FloatField()
    center_lng = models.FloatField()
    radius_km = models.FloatField(default=5.0)
    free_delivery = models.BooleanField(default=False)
    base_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_km_usd = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name

class DeliveryAddress(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='delivery_addresses', null=True, blank=True)
    address_text = models.TextField()
    lat = models.FloatField()
    lng = models.FloatField()
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.address_text[:50]
