from rest_framework import permissions


class IsSellerOrReadOnly(permissions.BasePermission):
    message = 'This action allowed only for sellers.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_supplier


class IsShopManagerOrReadOnly(permissions.BasePermission):
    message = 'This action allowed only for a shop manager.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user == obj.manager
