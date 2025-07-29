from django.urls import path
from rest_framework.routers import DefaultRouter
from django_rest_passwordreset.views import ResetPasswordRequestToken, ResetPasswordConfirm
from .views import PartnerUpdate, RegisterUser, LoginUser, ProductListView, BasketView, ContactView, OrderConfirmView, OrderListView, ConfirmEmail

router = DefaultRouter()

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('user/register', RegisterUser.as_view(), name='user-register'),
    path('user/login', LoginUser.as_view(), name='user-login'),
    path('products', ProductListView.as_view(), name='product-list'),
    path('basket', BasketView.as_view(), name='basket'),
    path('contacts', ContactView.as_view(), name='contacts'),
    path('order/confirm', OrderConfirmView.as_view(), name='order-confirm'),
    path('orders', OrderListView.as_view(), name='orders'),
    path('user/confirm', ConfirmEmail.as_view(), name='user-confirm'),
    path('password/reset/', ResetPasswordRequestToken.as_view()),
    path('password/reset/confirm/', ResetPasswordConfirm.as_view()),
]