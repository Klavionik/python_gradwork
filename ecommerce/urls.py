from django.urls import path
from .views import PriceListUpdateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token-refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('shop/price-list/', PriceListUpdateView.as_view(), name='pricelist-update')
]
