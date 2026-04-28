from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('scooter', 'user', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating')
    search_fields = ('scooter__title', 'user__email', 'comment')
