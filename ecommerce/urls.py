from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PriceListUpdateView, ShopView, ProductListView, ProductDetailView

router = DefaultRouter()
router.register('shop', ShopView, basename='shop')

urlpatterns = [
    path('shop/price-list/', PriceListUpdateView.as_view(), name='pricelist-update'),
    path('products/', ProductListView.as_view(), name='products-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='products-detail'),
] + router.urls
