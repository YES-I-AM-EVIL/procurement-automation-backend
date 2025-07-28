from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import ConfirmEmailToken, Order
from config.celery_app import app

@shared_task
def send_confirmation_email_task(user_id):
    user = User.objects.get(id=user_id)
    token = ConfirmEmailToken.objects.create(user=user)
    message = f"Подтвердите email: http://127.0.0.1:8000/api/user/confirm?token={token.key}"
    send_mail('Подтверждение регистрации', message, settings.EMAIL_HOST_USER, [user.email])

@shared_task
def send_order_confirmation_task(order_id, email):
    order = Order.objects.get(id=order_id)
    items = order.ordered_items.all()
    message = f"Ваш заказ №{order.id} принят!\n\nТовары:\n"
    message += "\n".join(f"{item.product_info.product.name} - {item.quantity} шт." for item in items)
    send_mail('Подтверждение заказа', message, settings.EMAIL_HOST_USER, [email])