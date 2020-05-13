from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import PriceListUpdateView, ShopView, ProductListView, ProductDetailView, CartView, \
    CreateCartView, CartItemView, CheckoutView, ContactView, OrderListView, OrderDetailView

router = SimpleRouter()
router.register('shop', ShopView, basename='shop')
router.register('contacts', ContactView, basename='contact')

urlpatterns = [
    path('shop/price-list/', PriceListUpdateView.as_view(), name='pricelist-update'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('cart/', CreateCartView.as_view(), name='cart-create'),
    path('cart/<int:cart_id>/', CartView.as_view(), name='cart'),
    path('cart/<int:cart_id>/items/', CartItemView.as_view(), name='cart-items'),
    path('cart/<int:cart_id>/items/<int:item_id>/', CartItemView.as_view(), name='item-detail'),
    path('cart/<int:cart_id>/checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
] + router.urls
