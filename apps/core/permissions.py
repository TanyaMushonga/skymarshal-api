from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Global permission check for admin role.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (getattr(request.user, 'role', None) == 'admin' or request.user.is_staff or request.user.is_superuser)
        )

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """
    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS or
            (request.user and 
             request.user.is_authenticated and 
             (getattr(request.user, 'role', None) == 'admin' or request.user.is_staff))
        )
