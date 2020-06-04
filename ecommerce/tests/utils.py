import os

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from ecommerce.models import Shop, Category, Product, ProductDetail, Parameter, ProductParameter

User = get_user_model()

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

product1_data = dict(
    category='Смартфоны',
    name='Смартфон Apple iPhone XS Max 512GB (золотистый)',
    supplied_id=1111,
    price=1000,
    price_rrp=1100,
    qty=100,
    available=True,
    parameter='Диагональ (дюйм)',
    parameter_value='6.5'
)

product2_data = dict(
    category='Смартфоны',
    name='Смартфон Apple iPhone XR 256GB (черный)',
    supplied_id=2222,
    price=2000,
    price_rrp=2200,
    qty=100,
    parameter='Встроенная память (Гб)',
    parameter_value='256'
)

test_products = {'product1': product1_data, 'product2': product2_data}


def load_fixture(fixture_name):
    path = os.path.join(settings.BASE_DIR, 'ecommerce', 'fixtures', fixture_name)
    with open(path, 'rb') as f:
        content = f.read()
    return content


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


def make_test_products(shop):
    category = Category.objects.create(name=product1_data['category'])
    category.shops.add(shop)

    for _, data in test_products.items():
        product1 = Product.objects.create(name=data['name'], category=category)
        product_detail1 = ProductDetail.objects.create(
            product=product1,
            shop=shop,
            supplier_id=data['supplied_id'],
            price=data['price'],
            price_rrp=data['price_rrp'],
            qty=data['qty'],
            available=True,
        )
        parameter1 = Parameter.objects.create(name=data['parameter'])
        ProductParameter.objects.create(
            parameter=parameter1,
            product_detail=product_detail1,
            value=data['parameter_value']
        )


def make_price_list_request(filename, token, path):
    price_file = load_fixture(filename)
    headers = dict(
        HTTP_CONTENT_DISPOSITION=f'attachment; filename={filename}',
        HTTP_AUTHORIZATION=f'Bearer {token}',
    )

    request = APIRequestFactory().post(
        path, price_file, content_type='text/yaml', **headers)

    return request
