from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models, transaction


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
    STAFF = 'staff'
    USER_KIND = (
        (SUPPLIER, 'Supplier'),
        (BUYER, 'Buyer'),
        (STAFF, 'Staff'),
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
        return self.kind == self.SUPPLIER

    @property
    def is_buyer(self):
        return self.kind == self.BUYER

    @property
    def is_staff(self):
        return True if self.kind == self.STAFF or self.is_superuser else False

    class Meta:
        db_table = 'users'


class Contact(models.Model):
    phone = models.CharField(
        max_length=32,
    )
    address = models.CharField(
        max_length=100,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contacts',
    )

    class Meta:
        db_table = 'contacts'


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


class ProductDetail(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='detail'
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='product_detail'
    )
    supplier_id = models.PositiveIntegerField()
    price = models.PositiveIntegerField(verbose_name='Price')
    price_rrp = models.PositiveIntegerField(verbose_name='Recommended Retail Price')
    qty = models.PositiveIntegerField(verbose_name='Quantity')
    available = models.BooleanField()

    def __str__(self):
        return f'{self.product.name} {self.shop}'

    class Meta:
        db_table = 'product_details'
        constraints = [models.UniqueConstraint(
            fields=('supplier_id', 'shop', 'product'), name='unique_product'
        )]


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
    product_detail = models.ForeignKey(
        ProductDetail,
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
    NEW = 'new'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (
            NEW, 'Order received'
        ),
        (
            PROCESSING, 'Order is being processed'
        ),
        (
            SHIPPED, 'Order has been shipped'
        ),
        (
            DELIVERED, 'Order is delivered'
        ),
        (
            CANCELLED, 'Order is cancelled'
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
        default=NEW,
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='+',
    )

    def __str__(self):
        return f'{self.id} {self.status}'

    class Meta:
        db_table = 'orders'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        ProductDetail,
        on_delete=models.CASCADE,
        related_name='+',
    )
    qty = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product} {self.qty}'

    class Meta:
        db_table = 'order_items'


class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        unique=True,
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='+',
        null=True,
    )

    def __str__(self):
        return f'{self.user} shopping cart'

    @transaction.atomic()
    def checkout(self):
        order = Order.objects.create(user=self.user, contact=self.contact)
        items = [OrderItem(
            order=order, product=item.product, qty=item.qty)
            for item in self.items.all()]

        OrderItem.objects.bulk_create(items)

        self.items.all().delete()
        self.contact = None
        self.save(update_fields=['contact'])

        return order

    class Meta:
        db_table = 'carts'


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        ProductDetail,
        on_delete=models.SET_NULL,
        related_name='+',
        null=True,
    )
    qty = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product.product.name} in cart'

    class Meta:
        db_table = 'cart_items'
        constraints = [models.UniqueConstraint(
            fields=('cart', 'product'), name='unique_cart_item'
        )]
