from django.db import models

class VehicleType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class VehicleModel(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name='models')
    engine_cc = models.IntegerField()
    transmission = models.CharField(max_length=50)
    fuel_consumption = models.FloatField()
    year = models.IntegerField()
    trunk = models.CharField(max_length=100)
    helmets_count = models.IntegerField(default=1)
    description = models.TextField()
    rental_terms = models.TextField()

    def __str__(self):
        return f"{self.brand} {self.name}"

class Vehicle(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
    )
    model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT, related_name='vehicles')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50)
    base_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    mileage = models.IntegerField(default=0)
    rating_avg = models.FloatField(default=0.0)
    reviews_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['base_price_usd']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return f"{self.title} ({self.sku})"

class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='vehicles/')
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.vehicle.title}"

class VehicleTranslation(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    description = models.TextField()
    rental_terms = models.TextField()

    class Meta:
        unique_together = ('vehicle', 'language')

    def __str__(self):
        return f"{self.language} translation for {self.vehicle.title}"

class VehicleMaintenance(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Maintenance for {self.vehicle.sku} ({self.start_at})"
