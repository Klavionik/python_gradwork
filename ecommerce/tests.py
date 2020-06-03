import os

from rest_framework.test import APITestCase, APIRequestFactory, APIClient
from rest_framework.reverse import reverse
from rest_framework_simplejwt.tokens import AccessToken
from ecommerce.views import PriceListUpdateView
from ecommerce.serializers import PriceListSerializer
from ecommerce.models import User, Shop, Product, Cart, ProductDetail
from django.conf import settings
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
        cls.supplier_token = AccessToken.for_user(cls.supplier)
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def test_price_list_from_file(self):
        request = make_price_list_request('price1.yml', self.supplier_token, self.path)
        response = PriceListUpdateView.as_view()(request)
        products_updated = Product.objects.filter(detail__shop=self.shop).count()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(products_updated, 5)

    def test_only_supplier_allowed(self):
        request = make_price_list_request('price1.yml', self.buyer_token, self.path)
        response = PriceListUpdateView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    def test_invalid_price_list_declined(self):
        request = make_price_list_request('price_invalid.yml', self.supplier_token, self.path)
        response = PriceListUpdateView.as_view()(request)

        self.assertEqual(response.status_code, 400)


class TestProductViews(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        load_price_list('price1.yml', cls.shop)
        cls.path_list = reverse('product-list')
        cls.path_detail = reverse('product-detail', args=[1])
        cls.buyer_token = AccessToken.for_user(cls.buyer)
        cls.client = APIClient().credentials(HTTP_AUTHORIZATION=f'Bearer {cls.buyer_token}')

    def test_retrieve_product_list(self):
        response = self.client.get(self.path_list)
        products = Product.objects.filter(detail__shop=self.shop).count()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(products, len(response.json()))

    def test_retrieve_product_detail(self):
        response = self.client.get(self.path_detail)
        product = Product.objects.get(id=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['detail']), 1)
        self.assertEqual(response.json()['name'], product.name)


class TestCreateCartView(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        load_price_list('price1.yml', cls.shop)
        cls.path = reverse('cart-create')
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def _pre_setup(self):
        super()._pre_setup()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')

    def test_create_cart(self):
        payload = {'user': self.buyer.id}
        response = self.client.post(self.path, payload, format='json')
        cart = Cart.objects.filter(user=self.buyer).exists()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(cart)

    def test_only_one_cart_per_buyer(self):
        cart = Cart.objects.create(user=self.buyer)
        payload = {'user': self.buyer.id}
        response = self.client.post(self.path, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.buyer.cart, cart)


class TestCartItemsView(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        load_price_list('price1.yml', cls.shop)
        cls.cart = Cart.objects.create(user=cls.buyer)
        cls.cart_path = reverse('cart-items', args=[cls.cart.id])
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def _pre_setup(self):
        super()._pre_setup()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')

    def test_add_item_to_cart(self):
        product = ProductDetail.objects.first()
        payload = {"product": product.id, "qty": 3}
        response = self.client.post(self.cart_path, payload, format='json')

        item = self.cart.items.filter(product=product)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(item), 1)

    def test_add_few_items_to_cart(self):
        product1, product2 = ProductDetail.objects.all()[:2]
        payload1, payload2 = {"product": product1.id, "qty": 3}, {"product": product2.id, "qty": 6}
        response1 = self.client.post(self.cart_path, payload1, format='json')
        response2 = self.client.post(self.cart_path, payload2, format='json')

        items = self.cart.items.all()

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(len(items), 2)

    def test_delete_item_from_cart(self):
        item_data = {'cart': self.cart, 'product': ProductDetail.objects.first(), 'qty': 3}
        item = self.cart.items.create(**item_data)
        path = reverse('item-detail', kwargs={'cart_id': self.cart.id, 'item_id': item.id})
        response = self.client.delete(path)

        self.assertEqual(response.status_code, 204)

