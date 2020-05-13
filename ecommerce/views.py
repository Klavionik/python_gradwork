from tempfile import TemporaryFile

import requests
import yaml
from django.db.models import Q
from requests.exceptions import RequestException
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.parsers import FileUploadParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse_lazy
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from yaml.error import YAMLError

from .exceptions import ResourceUnavailableError, YAMLParserError, URLError, InvalidDataError
from .forms import PriceListURLForm
from .models import Shop, Product, Cart, CartItem, Order, Contact
from .permissions import IsSellerOrReadOnly, IsShopManagerOrReadOnly, IsBuyer, IsCartOwner, \
    IsItemOwner
from .serializers import PriceListSerializer, ShopSerializer, ProductListSerializer, \
    ProductDetailSerializer, CartSerializer, CartItemSerializer, OrderListSerializer, \
    ContactSerializer, OrderDetailSerializer
from .tasks import send_order_confirmation


class OrderDetailView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer


class OrderListView(ListAPIView):
    serializer_class = OrderListSerializer

    def get_queryset(self):
        qs = Order.objects.all()

        if self.request.user.is_staff:
            return qs
        elif self.request.user.is_supplier:
            return self.filter_for_supplier(qs)
        else:
            return self.filter_for_buyer(qs)

    def filter_for_supplier(self, qs):
        if not hasattr(self.request.user, 'shop'):
            raise ValidationError(detail='Supplier must have a registered shop',
                                  code='shop is none')

        return qs.filter(items__product__shop=self.request.user.shop)

    def filter_for_buyer(self, qs):
        return qs.filter(user=self.request.user)


class CheckoutView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsCartOwner]
    queryset = Cart.objects.all().select_related('user')
    serializer_class = CartSerializer
    lookup_url_kwarg = 'cart_id'

    def post(self, request, *args, **kwargs):
        return self.checkout()

    def checkout(self):
        cart = self.get_object()

        if not cart.contact:
            raise ValidationError(
                'Contact field must be set in order to proceed with the checkout',
                code='contact is missing'
            )

        order = cart.checkout()
        send_order_confirmation.delay(order.id, order.user.email)

        serializer = OrderDetailSerializer(instance=order)
        headers = self.get_headers(order)
        return Response(data=serializer.data, status=HTTP_201_CREATED, headers=headers)

    def get_headers(self, order):
        return {'Location': reverse_lazy('order-detail', args=[order.id], request=self.request)}


class ContactView(ModelViewSet):
    queryset = Contact.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ContactSerializer

    def get_success_headers(self, data):
        return {'Location': reverse_lazy('contact-detail', args=[data['id']], request=self.request)}


class CartItemView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsItemOwner]
    queryset = CartItem.objects.all().prefetch_related('cart__user')
    serializer_class = CartItemSerializer
    lookup_url_kwarg = 'item_id'

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, instance=self.get_object(), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=HTTP_204_NO_CONTENT)

    def post(self, request, *args, **kwargs):
        request.data['cart'] = kwargs['cart_id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        headers = self.get_headers(item)
        return Response(serializer.data, headers=headers, status=HTTP_201_CREATED)

    def get_headers(self, item):
        return {'Location': reverse_lazy('item-detail',
                                         kwargs={'cart_id': self.kwargs['cart_id'],
                                                 'item_id': item.id}, request=self.request)}


class CartView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsCartOwner]
    queryset = Cart.objects.all().select_related('user')
    serializer_class = CartSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'cart_id'

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = \
            self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CreateCartView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsBuyer]
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    def post(self, request, *args, **kwargs):
        return self.create_cart(request)

    def create_cart(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = serializer.save()
        return Response(self.get_response_data(cart),
                        headers=self.get_headers(cart),
                        status=HTTP_201_CREATED)

    def get_headers(self, cart):
        return {'Location': reverse_lazy('cart', args=[cart.id], request=self.request)}

    def get_response_data(self, cart):
        return {"cart_id": cart.id}


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects. \
        filter(Q(detail__shop__active=True), Q(detail__available=True)). \
        prefetch_related('detail__parameters__parameter')
    serializer_class = ProductDetailSerializer


class ProductListView(ListAPIView):
    queryset = Product.objects. \
        filter(Q(detail__shop__active=True), Q(detail__available=True)). \
        select_related('category')
    serializer_class = ProductListSerializer


class ShopView(ModelViewSet):
    queryset = Shop.objects.all().select_related('manager')
    permission_classes = [IsAuthenticated, IsSellerOrReadOnly, IsShopManagerOrReadOnly]
    serializer_class = ShopSerializer

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)


class PriceListUpdateView(APIView):
    class YAMLUploadParser(FileUploadParser):
        media_type = 'text/yaml'

    parser_classes = [JSONParser, YAMLUploadParser]
    permission_classes = [IsAuthenticated, IsSellerOrReadOnly]

    form = PriceListURLForm
    serializer_class = PriceListSerializer
    success_message = "Price list updated: %s products"

    def get_url(self):
        form = self.form(self.request.data, shop_url=self.request.user.shop.url)

        if form.is_valid():
            source = form.cleaned_data['url']
            return source
        else:
            raise URLError()

    @staticmethod
    def get_content(source):
        try:
            with TemporaryFile() as f:
                for chunk in source:
                    f.write(chunk)
                f.seek(0)

                price_list = yaml.safe_load(f.read())

                return price_list
        except YAMLError:
            raise YAMLParserError()

    def get_price_list(self, source):
        try:
            content = requests.get(source, stream=True)

            if content.status_code == 200:
                price_list = self.get_content(content.iter_content(
                    chunk_size=512, decode_unicode=True)
                )

                return price_list
            else:
                content.raise_for_status()
        except RequestException:
            raise ResourceUnavailableError()

    def post(self, request, *args, **kwargs):
        if self.request.FILES:
            return self.update_from_file()
        else:
            return self.update_from_url()

    def update_from_url(self):
        source = self.get_url()
        return self.update_prices(self.get_price_list(source))

    def update_from_file(self):
        file = self.request.FILES['file']
        return self.update_prices(self.get_content(file))

    def update_prices(self, price_list):
        serializer = self.serializer_class(
            data=price_list,
            shop=self.request.user.shop)

        if serializer.is_valid():
            updated = serializer.save()
            return self.success(updated)
        else:
            raise InvalidDataError()

    def success(self, updated):
        msg = {"response": self.success_message % updated}
        return Response(data=msg)
