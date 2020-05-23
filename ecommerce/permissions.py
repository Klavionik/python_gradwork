from rest_framework import permissions
from rest_framework.exceptions import ValidationError

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


class IsOrderOwnerOrAdmin(permissions.BasePermission):
    message = "This action is allowed only for an order owner"

    def has_object_permission(self, request, view, obj):
        if request.user.is_buyer:
            return self.test_buyer(request, obj)
        if request.user.is_supplier:
            return self.test_supplier(request, obj)
        if request.user.is_superuser:
            return True

    @staticmethod
    def test_buyer(request, obj):
        return request.user == obj.user

    @staticmethod
    def test_supplier(request, obj):
        if not hasattr(request.user, 'shop'):
            raise ValidationError(detail='Supplier must have a registered shop',
                                  code='shop is none')

        return obj.items.filter(product__shop=request.user.shop).exists()
