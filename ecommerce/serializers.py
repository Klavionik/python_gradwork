from django.db.models import Q
from rest_framework import serializers

from ecommerce.models import Category, ProductParameter, Parameter, Product, ProductInfo, Shop


class ParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        exclude = ('product_info',)


class ProductInfoSerializer(serializers.ModelSerializer):
    parameters = ParameterSerializer(many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'price_rrp', 'price', 'qty', 'shop', 'parameters',)


class ProductDetailSerializer(serializers.ModelSerializer):
    info = ProductInfoSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'info')


class ProductSerializer(serializers.ModelSerializer):
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

    category = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)
    price = serializers.IntegerField()
    price_rrp = serializers.IntegerField()
    qty = serializers.IntegerField()
    parameters = ParameterSerializer(many=True)


class PriceListSerializer(serializers.Serializer):
    products = PriceListItemSerializer(many=True)

    def __init__(self, *args, **kwargs):
        self.shop = kwargs.pop('shop', None)
        self.updated = 0
        super().__init__(*args, **kwargs)

    def clean_before(self):
        old_products = ProductInfo.objects.filter(shop=self.shop)
        old_products.delete()

    def clean_after(self):
        empty_products = Product.objects.filter(Q(info__isnull=True), Q(info__shop=self.shop))
        empty_products.delete()

        empty_parameters = Parameter.objects.filter(product_parameters__isnull=True)
        empty_parameters.delete()

    def create(self, validated_data):
        self.clean_before()

        for product in validated_data['products']:
            category, name, price, price_rrp, qty = self.get_product_data(product)
            parameters = product['parameters']

            self.create_item(category, name, price, price_rrp, qty, parameters)
            self.updated += 1

        self.clean_after()

        return self.updated

    def create_item(self, category, name, price, price_rrp, qty, parameters):
        category = self.create_category(category)
        product, product_info = self.create_product(name, category, price, price_rrp, qty)
        self.create_parameters(product_info, parameters)

    def create_category(self, name):
        category_obj, _ = Category.objects.get_or_create(name=name)
        category_obj.shops.add(self.shop)
        return category_obj

    def create_product(self, name, category, price, price_rrp, qty):
        product, _ = Product.objects.get_or_create(name=name, category=category)
        product_info = self.create_product_info(product, price, price_rrp, qty)
        return product, product_info

    def create_product_info(self, product, price, price_rrp, qty):
        product_info = ProductInfo.objects.create(
            product=product,
            shop=self.shop,
            price=price,
            price_rrp=price_rrp,
            qty=qty,
        )
        return product_info

    def create_parameters(self, product_info, parameters):
        for parameter in parameters:
            name, value = self.get_parameter_data(parameter)
            parameter, _ = Parameter.objects.get_or_create(name=name)
            ProductParameter.objects.create(
                parameter=parameter, product_info=product_info, value=value,
            )

    @staticmethod
    def get_product_data(product):
        return product['category'], \
                product['name'], \
                product['price'], \
                product['price_rrp'], \
                product['qty']

    @staticmethod
    def get_parameter_data(parameter):
        return parameter['name'], parameter['value']
