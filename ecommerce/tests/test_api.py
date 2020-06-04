from unittest.mock import patch

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from ecommerce.models import Product, Cart, ProductDetail, CartItem, Contact, Order
from ecommerce.views import PriceListUpdateView
from .utils import make_price_list_request, make_users, make_test_products


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
        make_test_products(cls.shop)
        cls.path_list = reverse('product-list')
        cls.path_detail = reverse('product-detail', args=[1])
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def _pre_setup(self):
        super()._pre_setup()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')

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
        make_test_products(cls.shop)
        cls.path = reverse('cart-create')
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def _pre_setup(self):
        super()._pre_setup()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')

    def test_create_cart(self):
        payload = {'user': self.buyer.id}
        response = self.client.post(self.path, payload, format='json')
        db_cart = Cart.objects.filter(user=self.buyer).exists()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(db_cart)

    def test_only_one_cart_per_buyer(self):
        cart = Cart.objects.create(user=self.buyer)
        payload = {'user': self.buyer.id}
        response = self.client.post(self.path, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.buyer.cart, cart)


class TestCartView(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        cart = Cart.objects.create(user=cls.buyer)
        cls.path = reverse('cart', args=[cart.id])
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def test_set_contact(self):
        contact_data = {'address': '14 Some St.', 'phone': '+799912345678', 'user': self.buyer}
        contact = Contact.objects.create(**contact_data)
        payload = {'contact': contact.id}
        response = self.client.patch(
            self.path, payload, format='json', HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}'
        )

        db_cart = Cart.objects.get(user=self.buyer)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(db_cart.contact, contact)


class TestCartItemView(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        make_test_products(cls.shop)
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

        db_item = self.cart.items.filter(product=product)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(db_item), 1)

    def test_add_few_items_to_cart(self):
        product1, product2 = ProductDetail.objects.all()[:2]
        payload1, payload2 = {"product": product1.id, "qty": 3}, {"product": product2.id, "qty": 6}
        response1 = self.client.post(self.cart_path, payload1, format='json')
        response2 = self.client.post(self.cart_path, payload2, format='json')

        db_items = self.cart.items.all()

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(len(db_items), 2)

    def test_delete_item_from_cart(self):
        item_data = {'cart': self.cart, 'product': ProductDetail.objects.first(), 'qty': 3}
        item = self.cart.items.create(**item_data)
        path = reverse('item-detail', kwargs={'cart_id': self.cart.id, 'item_id': item.id})
        response = self.client.delete(path)

        self.assertEqual(response.status_code, 204)

    def test_edit_item(self):
        item_data = {'cart': self.cart, 'product': ProductDetail.objects.first(), 'qty': 1}
        item = self.cart.items.create(**item_data)
        payload = {'qty': 10}
        path = reverse('item-detail', kwargs={'cart_id': self.cart.id, 'item_id': item.id})
        response = self.client.patch(path, payload, format='json')

        db_item = CartItem.objects.get(id=item.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(db_item.qty, 10)

    def test_not_enough_items_in_stock(self):
        item_data = {'cart': self.cart, 'product': ProductDetail.objects.first(), 'qty': 5}
        payload = {'qty': 99999999999}
        item = self.cart.items.create(**item_data)
        path = reverse('item-detail', kwargs={'cart_id': self.cart.id, 'item_id': item.id})
        response = self.client.patch(path, payload, format='json')

        db_item = CartItem.objects.get(id=item.id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(db_item.qty, 5)


class TestCheckoutView(APITestCase):

    def create_cart(self):
        self.cart = Cart.objects.create(user=self.buyer)
        item_data = {'cart': self.cart, 'product': ProductDetail.objects.first(), 'qty': 3}
        contact_data = {'address': '14 Some St.', 'phone': '+799912345678', 'user': self.buyer}
        self.cart.items.create(**item_data)
        contact = Contact.objects.create(**contact_data)
        self.cart.contact = contact
        self.cart.save()

    @classmethod
    def setUpTestData(cls):
        cls.supplier, cls.buyer, cls.shop = make_users()
        make_test_products(cls.shop)
        cls.buyer_token = AccessToken.for_user(cls.buyer)

    def _pre_setup(self):
        super()._pre_setup()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')
        self.create_cart()

    def test_checkout(self):
        path = reverse('checkout', kwargs={'cart_id': self.cart.id})
        with patch('ecommerce.views.send_order_confirmation.delay') as mocked_task:
            response = self.client.post(path)

        order = Order.objects.first()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(order.id, response.json().get('id'))
        mocked_task.assert_called_once_with(order.id, order.user.email)