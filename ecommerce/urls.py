from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PriceListUpdateView, ShopView, ProductListView, ProductDetailView, CartView, \
    CreateCartView, CartItemView

router = DefaultRouter()
router.register('shop', ShopView, basename='shop')

urlpatterns = [
    path('shop/price-list/', PriceListUpdateView.as_view(), name='pricelist-update'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('cart/', CreateCartView.as_view(), name='cart-create'),
    path('cart/<int:pk>/', CartView.as_view(), name='cart'),
    path('cart/items/<int:pk>/', CartItemView.as_view(), name='cart-item'),
    # path('checkout/', CheckoutView.as_view(), name='checkout'),
] + router.urls
