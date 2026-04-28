from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        # Check if obj has user attribute or is the user itself
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user

class IsBookingOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        # For Booking model
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # For related models like Payment or UserDocument
        if hasattr(obj, 'booking'):
            return obj.booking.user == request.user
        return False
