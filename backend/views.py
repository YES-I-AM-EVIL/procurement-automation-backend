from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.core.mail import send_mail
from django.conf import settings
from requests import get
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from yaml import load as load_yaml, Loader
from .serializers import UserSerializer, ContactSerializer, ProductInfoSerializer, OrderSerializer
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, ConfirmEmailToken, User, Order, OrderItem
from .permissions import IsSupplier 

class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика через YAML
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            # Валидация URL
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return Response({'Status': False, 'Error': str(e)}, status=400)
            
            # Загрузка и парсинг YAML
            try:
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                
                # Обновление магазина
                shop, _ = Shop.objects.get_or_create(
                    name=data['shop'], 
                    user_id=request.user.id
                )
                
                # Обработка категорий
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(
                        id=category['id'],
                        defaults={'name': category['name']}
                    )
                    category_object.shops.add(shop.id)
                    category_object.save()
                
                # Удаляем старые товары магазина
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                
                # Обработка товаров
                for item in data['goods']:
                    # Создаем продукт
                    product, _ = Product.objects.get_or_create(
                        name=item['name'],
                        category_id=item['category']
                    )
                    
                    # Создаем информацию о продукте
                    product_info = ProductInfo.objects.create(
                        product_id=product.id,
                        external_id=item['id'],
                        model=item['model'],
                        price=item['price'],
                        price_rrc=item['price_rrc'],
                        quantity=item['quantity'],
                        shop_id=shop.id
                    )
                    
                    # Обработка параметров товара
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(
                            product_info_id=product_info.id,
                            parameter_id=parameter_object.id,
                            value=value
                        )
                
                return Response({'Status': True})
                
            except IntegrityError as e:
                return Response({'Status': False, 'Error': f'Ошибка целостности данных: {str(e)}'}, status=400)
            except Exception as e:
                return Response({'Status': False, 'Error': str(e)}, status=400)

        return Response({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)
    
class RegisterUser(generics.CreateAPIView):
    """
    Регистрация пользователя с подтверждением email
    Отправляет токен подтверждения на указанный email
    """
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        user.set_password(request.data['password'])
        user.is_active = False  # Активируется после подтверждения email
        user.save()

        # Создаем и отправляем токен подтверждения
        token = ConfirmEmailToken.objects.create(user=user)
        self._send_confirmation_email(user.email, token.key)
        
        return Response(
            {'Status': True, 'Message': 'Письмо с подтверждением отправлено'},
            status=status.HTTP_201_CREATED
        )

    def _send_confirmation_email(self, email, token):
        """Вспомогательный метод для отправки email"""
        message = f"""
        Для подтверждения регистрации перейдите по ссылке:
        http://127.0.0.1:8000/api/user/confirm?token={token}
        """
        send_mail(
            subject='Подтверждение регистрации',
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        
class LoginUser(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({'Status': True, 'Token': token.key})
        return Response({'Status': False, 'Error': 'Неверные учетные данные'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
class ProductListView(generics.ListAPIView):
    queryset = ProductInfo.objects.select_related('product', 'shop').prefetch_related(
        'product_parameters__parameter').all()
    serializer_class = ProductInfoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        shop_id = self.request.query_params.get('shop_id')
        
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
            
        return queryset
    
class BasketView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        basket = Order.objects.filter(
            user=request.user, 
            state='basket'
        ).prefetch_related('ordered_items__product_info').first()
        
        if not basket:
            return Response({'Status': False, 'Error': 'Корзина пуста'})
            
        serializer = OrderSerializer(basket)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity', 1)
        
        if not product_info_id:
            return Response({'Status': False, 'Error': 'Не указан товар'})
        
        product_info = get_object_or_404(ProductInfo, id=product_info_id)
        
        order, _ = Order.objects.get_or_create(
            user=request.user,
            state='basket'
        )
        
        OrderItem.objects.create(
            order=order,
            product_info=product_info,
            quantity=quantity
        )
        
        return Response({'Status': True})

    def delete(self, request, *args, **kwargs):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'Status': False, 'Error': 'Не указана позиция'})
            
        OrderItem.objects.filter(
            id=item_id,
            order__user=request.user,
            order__state='basket'
        ).delete()
        
        return Response({'Status': True})
    
class ContactView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class OrderConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'Status': False, 'Error': 'Не указан контакт'})
            
        try:
            order = Order.objects.get(user=request.user, state='basket')
            contact = Contact.objects.get(id=contact_id, user=request.user)

            # Проверка перед подтверждением заказа
            for item in order.ordered_items.all():
                if not item.product_info.shop.state:
                    return Response({'Status': False, 'Error': f'Магазин {item.product_info.shop.name} не принимает заказы'})
                if item.product_info.quantity < item.quantity:
                    return Response({'Status': False, 'Error': f'Недостаточно товара {item.product_info.product.name}'})
            
            order.contact = contact
            order.state = 'new'
            order.save()
            
            return Response({'Status': True})
        except Order.DoesNotExist:
            return Response({'Status': False, 'Error': 'Нет активной корзины'})
        except Contact.DoesNotExist:
            return Response({'Status': False, 'Error': 'Контакт не найден'})
        
    def send_order_email(self, order, email):
        items = OrderItemSerializer(
            order.ordered_items.all(), 
            many=True
        ).data
        
        message = f"""
        Ваш заказ №{order.id} принят!
        Дата: {order.dt}
        Статус: {order.get_state_display()}
        
        Состав заказа:
        {''.join(f'{item["product_info"]["product"]["name"]} - {item["quantity"]} шт. по {item["product_info"]["price"]} руб.\n' for item in items)}
        
        Адрес доставки:
        {order.contact.city}, {order.contact.street}, {order.contact.house}
        """
        
        send_mail(
            'Подтверждение заказа',
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )   

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).exclude(state='basket').prefetch_related('ordered_items')
    
class ConfirmEmail(generics.GenericAPIView):
    """
    Класс для подтверждения email через токен
    """
    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({'Status': False, 'Error': 'Токен не указан'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = ConfirmEmailToken.objects.get(key=token)
            user = token.user
            user.is_active = True
            user.save()
            token.delete()
            return Response({'Status': True})
        except ConfirmEmailToken.DoesNotExist:
            return Response({'Status': False, 'Error': 'Неверный токен'}, 
                          status=status.HTTP_404_NOT_FOUND)

    
def send_order_to_admin(order):
    items = OrderItem.objects.filter(order=order)
    message = f"Новый заказ #{order.id}\n\n"
    message += "\n".join(f"{item.product_info.product.name} - {item.quantity} шт." for item in items)
    send_mail(
        'Накладная по заказу',
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        fail_silently=False,
    )

class SupplierOrders(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplier]

    def get(self, request):
        orders = Order.objects.filter(
            ordered_items__product_info__shop__user=request.user
        ).distinct()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
class ExportProducts(APIView):
    def get(self, request):
        products = ProductInfo.objects.all()
        data = [{
            'name': p.product.name,
            'price': p.price,
            'quantity': p.quantity
        } for p in products]
        return Response(data)
    
class IsSupplier(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.type == 'shop'