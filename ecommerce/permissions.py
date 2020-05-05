from rest_framework import permissions


class IsSellerOrReadOnly(permissions.BasePermission):
    message = 'This action is allowed only for suppliers.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_supplier


class IsShopManagerOrReadOnly(permissions.BasePermission):
    message = 'This action is allowed only for a shop manager.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user == obj.manager


class IsBuyer(permissions.BasePermission):
    message = 'This action is allowed only for a buyer.'

    def has_permission(self, request, view):
        if request.user.is_buyer:
            return True
        return False


class IsCartOwner(permissions.BasePermission):
    message = 'This action is allowed only for a cart owner.'

    def has_object_permission(self, request, view, obj):
        if request.user == obj.user:
            return True
        return False


class IsItemOwner(permissions.BasePermission):
    message = 'This action is allowed only for an item owner.'

    def has_object_permission(self, request, view, obj):
        if request.user == obj.cart.user:
            return True
        return False

