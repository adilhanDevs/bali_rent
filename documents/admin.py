from django.contrib import admin
from .models import UserDocument

@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'created_at')
    list_filter = ('status', 'document_type')
    search_fields = ('user__email',)
