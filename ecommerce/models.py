from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The e-mail must be set')
        if extra_fields.get('is_seller') and extra_fields.get('is_buyer'):
            raise ValueError('User cannot be both a seller and a buyer')
        if extra_fields.get('is_seller') and not extra_fields.get('shop'):
            raise ValueError('Seller must have a related shop ID')
        if not extra_fields.get('is_seller') and not extra_fields.get('is_buyer')\
                and not extra_fields.get('is_staff'):
            raise ValueError('User muse be either a staff, a seller or a buyer')

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
    name = models.CharField(
        max_length=100,
    )
    surname = models.CharField(
        max_length=100,
    )
    patronymic = models.CharField(
        max_length=100,
    )
    email = models.EmailField(
        unique=True,
    )
    password = models.CharField(
        max_length=255,
    )
    company = models.CharField(
        max_length=100,
    )
    position = models.CharField(
        max_length=100,
    )
    is_seller = models.BooleanField(
        default=False,
    )
    shop = models.ForeignKey(
        'Shop',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    is_buyer = models.BooleanField(
        default=False,
    )
    is_staff = models.BooleanField(
        default=False,
    )
    is_active = models.BooleanField(
        default=True,
    )

    USERNAME_FIELD = EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f'{self.surname} {self.name} {self.company} {self.position}'

    class Meta:
        db_table = 'users'


class Shop(models.Model):
    name = models.CharField(
        unique=True,
        max_length=255,
    )
    url = models.URLField(
        unique=True,
        max_length=50,
    )
    status = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return f'{self.name} {"Open" if self.status else "Closed"}'

    def update_price_list(self, data):
        pass

    class Meta:
        db_table = 'shops'


class Category(models.Model):
    name = models.CharField(
        max_length=255,
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
        max_length=255,
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
        max_length=255,
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
        max_length=255,
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
        return f'{self.type} {self.user.id}'

    class Meta:
        db_table = 'contacts'
