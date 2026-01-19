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

class IsOfficerOrAdmin(permissions.BasePermission):
    """
    Custom permission for officers and admins
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # Check for role 'officer' or 'admin', or superuser/staff status
        # Also keeping the legacy check for 'is_officer' attribute just in case
        return (
            getattr(user, 'role', None) in ['officer', 'admin'] or
            user.is_staff or 
            user.is_superuser or
            (hasattr(user, 'is_officer') and user.is_officer)
        )

class IsOfficer(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        return getattr(user, 'role', None) == 'officer'