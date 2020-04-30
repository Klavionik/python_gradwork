from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The e-mail must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    SUPPLIER = 'supplier'
    BUYER = 'buyer'
    USER_KIND = (
        (SUPPLIER, 'Supplier'),
        (BUYER, 'Buyer'),
    )

    full_name = models.CharField(
        max_length=100,
    )
    email = models.EmailField(
        unique=True,
    )
    password = models.CharField(
        max_length=100,
    )
    company = models.CharField(
        max_length=100,
    )
    position = models.CharField(
        max_length=100,
    )
    kind = models.CharField(
        max_length=10,
        choices=USER_KIND,
        blank=False,
    )
    is_active = models.BooleanField(
        default=True,
    )

    USERNAME_FIELD = EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'company', 'position', 'kind']

    objects = UserManager()

    def __str__(self):
        return f'{self.full_name}'

    @property
    def is_supplier(self):
        return True if self.kind == self.SUPPLIER else False

    @property
    def is_buyer(self):
        return True if self.kind == self.BUYER else False

    class Meta:
        db_table = 'users'


class Shop(models.Model):
    name = models.CharField(
        max_length=100,
    )
    url = models.URLField(
        unique=True,
        max_length=50,
    )
    active = models.BooleanField(
        default=False,
    )
    manager = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='shop',
    )

    def __str__(self):
        return f'{self.name}'

    class Meta:
        db_table = 'shops'


class Category(models.Model):
    name = models.CharField(
        max_length=100,
    )
    shops = models.ManyToManyField(
        Shop,
        related_name='categories',
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'categories'


class Product(models.Model):
    name = models.CharField(
        max_length=100,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
    )

    def __str__(self):
        return f'{self.category} {self.name}'

    class Meta:
        db_table = 'products'


class ProductInfo(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='info'
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='products'
    )
    price = models.PositiveIntegerField(verbose_name='Price')
    price_rrp = models.PositiveIntegerField(verbose_name='Recommended Retail Price')
    qty = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product.name} {self.shop}'

    class Meta:
        db_table = 'product_info'


class Parameter(models.Model):
    name = models.CharField(
        unique=True,
        max_length=100,
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'parameters'


class ProductParameter(models.Model):
    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.CASCADE,
        related_name='product_parameters',
    )
    product_info = models.ForeignKey(
        ProductInfo,
        on_delete=models.CASCADE,
        related_name='parameters',
    )
    value = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return f'{self.parameter} {self.value}'

    class Meta:
        db_table = 'product_parameters'


class Order(models.Model):
    STATUS_CHOICES = (
        (
            'new', 'Order received'
        ),
        (
            'processing', 'Order is being processed'
        ),
        (
            'shipped', 'Order has been shipped'
        ),
        (
            'delivered', 'Order is delivered'
        ),
        (
            'cancelled', 'Order is cancelled'
        )
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    created = models.DateTimeField(
        auto_now_add=True,
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
    )

    def __str__(self):
        return f'{self.id} {self.status}'

    class Meta:
        db_table = 'orders'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    product = models.ForeignKey(
        ProductInfo,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    qty = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product} {self.qty}'

    class Meta:
        db_table = 'order_items'


class Contact(models.Model):
    TYPE_CHOICES = (
        (
            'phone', 'Phone number'
        ),
        (
            'address', 'Address'
        )
    )

    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contacts',
    )
    value = models.CharField(
        max_length=500,
    )

    def __str__(self):
        return f'{self.type} {self.value}'

    class Meta:
        db_table = 'contacts'
