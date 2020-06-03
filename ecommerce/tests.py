import os

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework.reverse import reverse
from ecommerce.views import PriceListUpdateView
from ecommerce.serializers import PriceListSerializer
from ecommerce.models import User, Shop, Product, Cart
from django.conf import settings
import json
import yaml

buyer_data = dict(
    full_name='Petr Petrov',
    company='Some Retailer Inc.',
    position='Manager',
    kind='buyer',
    email='testbuyer@gmail.com',
    password='arandombuyer'
)

supplier_data = dict(
    full_name='Ivan Ivanov',
    company='Some Distributor Inc.',
    position='Manager',
    kind='supplier',
    email='testseller@gmail.com',
    password='arandomsupplier'
)


def make_users():
    supplier = User.objects.create_user(**supplier_data)
    shop_data = dict(
        name='Some Shop Inc.',
        url='http://someshop.com',
        active=True,
        manager=supplier
    )
    shop = Shop.objects.create(**shop_data)
    buyer = User.objects.create_user(**buyer_data)
    return supplier, buyer, shop


def get_access_token(user, client):
    path = reverse('jwt-create')
    payload = json.dumps({'email': user['email'], 'password': user['password']})
    token_response = client.post(path, payload, content_type='application/json')
    assert token_response.status_code == 200, \
        f'Token not acquired: {token_response.status_code} {token_response.content.decode("utf8")}'
    return token_response.json()['access']


def get_fixture(fixture_name):
    path = os.path.join(settings.BASE_DIR, 'ecommerce', 'fixtures', fixture_name)
    with open(path, 'rb') as f:
        content = f.read()
    return content


def load_price_list(filename, shop):
    data = yaml.safe_load(get_fixture(filename))
    serializer = PriceListSerializer(data=data, shop=shop)
    serializer.is_valid(raise_exception=True)
    serializer.save()


def make_price_list_request(filename, token, path):
    price_file = get_fixture(filename)
    headers = dict(
        HTTP_CONTENT_DISPOSITION=f'attachment; filename={filename}',
        HTTP_AUTHORIZATION=f'Bearer {token}',
    )

    request = APIRequestFactory().post(
        path, price_file, content_type='text/yaml', **headers)

    return request


class TestPriceListUpdateView(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        cls.path = reverse('pricelist-update')

    def test_price_list_from_file(self):
        token = get_access_token(supplier_data, self.client)
        request = make_price_list_request('price1.yml', token, self.path)
        response = PriceListUpdateView.as_view()(request)
        products_updated = Product.objects.filter(detail__shop=self.shop).count()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(products_updated, 5)

    def test_only_supplier_allowed(self):
        token = get_access_token(buyer_data, self.client)
        headers = dict(
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        request = APIRequestFactory().post(
            self.path, **headers)
        response = PriceListUpdateView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    def test_invalid_price_list_declined(self):
        token = get_access_token(supplier_data, self.client)
        request = make_price_list_request('price_invalid.yml', token, self.path)
        response = PriceListUpdateView.as_view()(request)

        self.assertEqual(response.status_code, 400)


class TestProductViews(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        load_price_list('price1.yml', cls.shop)
        cls.path_list = reverse('product-list')
        cls.path_detail = reverse('product-detail', args=[1])

    def test_retrieve_product_list(self):
        token = get_access_token(buyer_data, self.client)
        response = self.client.get(self.path_list, HTTP_AUTHORIZATION=f'Bearer {token}')
        products = Product.objects.filter(detail__shop=self.shop).count()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(products, len(response.json()))

    def test_retrieve_product_detail(self):
        token = get_access_token(buyer_data, self.client)
        response = self.client.get(self.path_detail, HTTP_AUTHORIZATION=f'Bearer {token}')
        product = Product.objects.get(id=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['detail']), 1)
        self.assertEqual(response.json()['name'], product.name)


class TestCartViews(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        load_price_list('price1.yml', cls.shop)

    def test_create_cart(self):
        token = get_access_token(buyer_data, self.client)
        path = reverse('cart-create')
        payload = {'user': self.buyer.id}
        response = self.client.post(
            path, payload, format='json', HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        cart = Cart.objects.filter(user=self.buyer).exists()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(cart)
