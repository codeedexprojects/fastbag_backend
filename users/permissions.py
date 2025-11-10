from rest_framework.permissions import BasePermission
from vendors.models import Vendor


class IsAdminOrSuperuser(BasePermission):
    """
    Custom permission to allow access only to admin or superuser users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

    
class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, Vendor) and request.user.is_authenticated


class IsSuperUserOrAdmin(BasePermission):
    def has_permission(self, request, view):
        print(f"User authenticated: {request.user.is_authenticated}, Is superuser: {request.user.is_superuser}")

        return request.user and (request.user.is_superuser or request.user.is_staff)
