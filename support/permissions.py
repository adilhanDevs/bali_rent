from rest_framework import permissions


SUPPORT_WRITE_ROLES = {"admin", "manager"}
SUPPORT_READ_ROLES = {"staff"}


def is_support_team(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.role in SUPPORT_WRITE_ROLES | SUPPORT_READ_ROLES


class IsSupportAdminManagerOrStaffReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role in SUPPORT_WRITE_ROLES:
            return True
        if user.role in SUPPORT_READ_ROLES:
            return request.method in permissions.SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsSupportTicketOwnerOrTeam(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_support_team(user):
            return True

        ticket = getattr(obj, "ticket", obj)
        if hasattr(ticket, "user"):
            return ticket.user_id == user.id
        return False
