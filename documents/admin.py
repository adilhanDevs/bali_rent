from django.contrib import admin

from .models import DocumentVerification, UserDocument


class DocumentVerificationInline(admin.TabularInline):
    model = DocumentVerification
    extra = 0
    readonly_fields = ('verified_by', 'status', 'created_at')
    can_delete = False


@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'reviewed_by', 'reviewed_at', 'created_at')
    list_filter = ('status', 'document_type')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    autocomplete_fields = ('user', 'reviewed_by')
    inlines = [DocumentVerificationInline]


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = ('document', 'verified_by', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('document__user__email', 'document__user__full_name', 'verified_by__email')
    autocomplete_fields = ('document', 'verified_by')
