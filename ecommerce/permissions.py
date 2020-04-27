from rest_framework import permissions


class SellerPermission(permissions.BasePermission):
    message = 'This action allowed only for sellers.'

    def has_permission(self, request, view):
        if request.user.is_seller:
            return True
        return False
