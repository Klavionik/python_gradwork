from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from ecommerce.models import Category, ProductParameter, Parameter, Product, ProductDetail, Shop, \
    Cart, CartItem, Order, OrderItem, Contact


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'qty']


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total = serializers.SerializerMethodField()

    def get_total(self, obj):
        return obj.items.aggregate(total=Sum('product__price'))['total']

    class Meta:
        model = Order
        fields = '__all__'


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'created', 'status', 'user')


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                CartItem.objects.all(),
                fields=('cart', 'product'),
                message='This product is already in the cart.',
            )
        ]

    def validate_product(self, value):
        if not value.available:
            raise serializers.ValidationError(
                'Product %s is not available at the moment.' % value.product.name,
                code='not available'
            )
        return value

    def validate(self, data):
        product = self.instance.product if self.instance else data.get('product')
        qty = data.get('qty')

        if product.qty < qty:
            raise serializers.ValidationError(
                'Not enough product in stock: available %s, requested %s.' % (product.qty, qty),
                code='not enough product'
            )
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, required=False)

    class Meta:
        model = Cart
        fields = '__all__'


class ParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        exclude = ('product_detail',)


class ProductSerializer(serializers.ModelSerializer):
    parameters = ParameterSerializer(many=True)

    class Meta:
        model = ProductDetail
        fields = ('id', 'price_rrp', 'price', 'qty', 'shop', 'parameters',)


class ProductDetailSerializer(serializers.ModelSerializer):
    detail = ProductSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'detail')


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = '__all__'


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        exclude = ('manager',)


class PriceListItemSerializer(serializers.Serializer):
    class ParameterSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=100)
        value = serializers.CharField(max_length=100)

    supplier_id = serializers.IntegerField()
    category = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)
    price = serializers.IntegerField()
    price_rrp = serializers.IntegerField()
    qty = serializers.IntegerField()
    parameters = ParameterSerializer(many=True)


class PriceListSerializer(serializers.Serializer):
    products = PriceListItemSerializer(many=True, allow_null=True)

    def __init__(self, *args, **kwargs):
        self.shop = kwargs.pop('shop', None)
        self.updated = 0
        super().__init__(*args, **kwargs)

    def clean_before(self):
        ProductDetail.objects.filter(shop=self.shop).update(available=False)

    def clean_after(self):
        empty_products = Product.objects.filter(Q(detail__isnull=True), Q(detail__shop=self.shop))
        empty_products.delete()

        empty_parameters = Parameter.objects.filter(product_parameters__isnull=True)
        empty_parameters.delete()

    @transaction.atomic()
    def create(self, validated_data):
        self.clean_before()

        products = validated_data.get('products')

        if products is not None:
            for product in products:
                dealer_id, category, name, price, price_rrp, qty, parameters = \
                    self.get_product_data(product)

                self.create_item(dealer_id, category, name, price, price_rrp, qty, parameters)
                self.updated += 1

            self.clean_after()

        return self.updated

    def create_item(self, dealer_id, category, name, price, price_rrp, qty, parameters):
        category = self.create_category(category)
        product, product_detail = \
            self.create_product(dealer_id, name, category, price, price_rrp, qty)
        self.create_parameters(product_detail, parameters)

    def create_category(self, name):
        category_obj, _ = Category.objects.get_or_create(name=name)
        category_obj.shops.add(self.shop)
        return category_obj

    def create_product(self, dealer_id, name, category, price, price_rrp, qty):
        product, _ = Product.objects.get_or_create(name=name, category=category)
        product_detail = self.create_product_detail(dealer_id, product, price, price_rrp, qty)
        return product, product_detail

    def create_product_detail(self, supplier_id, product, price, price_rrp, qty):
        defaults = dict(
            supplier_id=supplier_id,
            product=product,
            shop=self.shop,
            price=price,
            price_rrp=price_rrp,
            qty=qty,
            available=True)

        product_detail, _ = ProductDetail.objects.update_or_create(
            defaults=defaults,
            supplier_id=supplier_id
        )
        return product_detail

    def create_parameters(self, product_detail, parameters):
        new_parameters = []

        for parameter in parameters:
            name, value = self.get_parameter_data(parameter)
            parameter, _ = Parameter.objects.get_or_create(name=name)
            product_parameter = ProductParameter(
                parameter=parameter, product_detail=product_detail, value=value,
            )
            new_parameters.append(product_parameter)

        ProductParameter.objects.bulk_create(new_parameters)

    @staticmethod
    def get_product_data(product):
        return product['supplier_id'], \
               product['category'], \
               product['name'], \
               product['price'], \
               product['price_rrp'], \
               product['qty'], \
               product['parameters']

    @staticmethod
    def get_parameter_data(parameter):
        return parameter['name'], parameter['value']
