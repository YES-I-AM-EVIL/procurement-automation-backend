from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django_rest_passwordreset.tokens import get_token_generator

# Константы для выбора значений
STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL

class UserManager(BaseUserManager):
    """Кастомный менеджер пользователей с email в качестве идентификатора"""
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    type = models.CharField(verbose_name='Тип пользователя', 
                          choices=USER_TYPE_CHOICES, 
                          max_length=5, 
                          default='buyer')
    is_active = models.BooleanField(default=False)
    
    # Добавляем эти строки для решения конфликта
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="backend_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="backend_user_permissions",
        related_query_name="user",
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


    def send_confirmation_email(self):
        token, _ = ConfirmEmailToken.objects.get_or_create(user=self)
        message = f"""
        Добро пожаловать в наш магазин!
        Для подтверждения email перейдите по ссылке:
        http://127.0.0.1:8000/api/user/confirm?token={token.key}
        """
        send_mail(
            'Подтверждение регистрации',
            message,
            DEFAULT_FROM_EMAIL,
            [self.email],
            fail_silently=False
        )


class Shop(models.Model):
    """Модель магазина"""
    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка', null=True, blank=True)
    user = models.OneToOneField(User, verbose_name='Пользователь',
                              blank=True, null=True,
                              on_delete=models.CASCADE)
    state = models.BooleanField(verbose_name='Статус получения заказов', default=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    """Модель категории товаров"""
    name = models.CharField(max_length=40, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', 
                                 related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Модель продукта"""
    name = models.CharField(max_length=80, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', 
                               related_name='products', blank=True,
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = "Список продуктов"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """Модель информации о продукте (цена, количество в конкретном магазине)"""
    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
    product = models.ForeignKey(Product, verbose_name='Продукт', 
                              related_name='product_infos', blank=True,
                              on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', 
                           related_name='product_infos', blank=True,
                           on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.PositiveIntegerField(verbose_name='Цена')
    price_rrc = models.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Информационный список о продуктах"
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'external_id'], 
                                  name='unique_product_info'),
        ]


class Parameter(models.Model):
    """Модель параметра товара"""
    name = models.CharField(max_length=40, verbose_name='Название')

    class Meta:
        verbose_name = 'Имя параметра'
        verbose_name_plural = "Список имен параметров"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """Модель связи параметра с продуктом"""
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                   related_name='product_parameters', blank=True,
                                   on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', 
                                related_name='product_parameters', blank=True,
                                on_delete=models.CASCADE)
    value = models.CharField(verbose_name='Значение', max_length=100)

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = "Список параметров"
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], 
                                  name='unique_product_parameter'),
        ]


class Contact(models.Model):
    """Модель контактов пользователя"""
    user = models.ForeignKey(User, verbose_name='Пользователь',
                           related_name='contacts', blank=True,
                           on_delete=models.CASCADE)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом', blank=True)
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'


class Order(models.Model):
    """Модель заказа"""
    user = models.ForeignKey(User, verbose_name='Пользователь',
                           related_name='orders', blank=True,
                           on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True)
    state = models.CharField(verbose_name='Статус', 
                            choices=STATE_CHOICES, 
                            max_length=15)
    contact = models.ForeignKey(Contact, verbose_name='Контакт',
                              blank=True, null=True,
                              on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказов"
        ordering = ('-dt',)

    def __str__(self):
        return str(self.dt)


class OrderItem(models.Model):
    """Модель позиции в заказе"""
    order = models.ForeignKey(Order, verbose_name='Заказ', 
                            related_name='ordered_items', blank=True,
                            on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте', 
                                   related_name='ordered_items', blank=True,
                                   on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'product_info'], 
                                  name='unique_order_item'),
        ]


class ConfirmEmailToken(models.Model):
    """Модель токена подтверждения email"""
    user = models.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name=_("The User which is associated to this password reset token")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("When was this token generated")
    )
    key = models.CharField(
        _("Key"),
        max_length=64,
        db_index=True,
        unique=True
    )

    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return f"Токен подтверждения для пользователя {self.user}"