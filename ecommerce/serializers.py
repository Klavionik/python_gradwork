from rest_framework import serializers

from ecommerce.models import Category, ProductParameter, Parameter, Product, ProductInfo
from django.db.models import Q


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('name',)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('name',)


class ProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductInfo
        fields = ('price', 'price_rrp', 'qty')


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ('name',)


class ProductParameterSerializer(serializers.ModelSerializer):
    name = serializers.CharField()

    class Meta:
        model = ProductParameter
        fields = ('name', 'value',)


class PriceListItemSerializer(serializers.Serializer):
    category = CategorySerializer()
    product = ProductSerializer()
    product_info = ProductInfoSerializer()
    parameters = ProductParameterSerializer(many=True)


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
        products = validated_data.get('products')

        for product in products:
            category_obj, _ = Category.objects.get_or_create(
                name=product['category']['name'],
            )
            product_obj, _ = Product.objects.get_or_create(
                name=product['product']['name'],
                category=category_obj,
            )
            product_info_obj = ProductInfo.objects.create(
                product=product_obj,
                shop=self.shop,
                price=product['product_info']['price'],
                price_rrp=product['product_info']['price_rrp'],
                qty=product['product_info']['qty'],
            )
            for parameter in product['parameters']:
                parameter_obj, _ = Parameter.objects.get_or_create(name=parameter['name'])
                ProductParameter(
                    parameter=parameter_obj,
                    product_info=product_info_obj,
                    value=parameter['value'],
                ).save()

            self.updated += 1

        self.clean_after()

        return self.updated
