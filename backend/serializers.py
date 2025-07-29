from rest_framework import serializers
from .models import User, Product, ProductInfo, Order, OrderItem, Contact
from .validators import validate_password, validate_phone
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
        )
    
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'company', 'position', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

class ContactSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(validators=[validate_phone])
    class Meta:
        model = Contact
        fields = ['id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone']
        extra_kwargs = {
            'user': {'read_only': True}
        }

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category']

class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    shop = serializers.StringRelatedField()
    parameters = serializers.SerializerMethodField()

    class Meta:
        model = ProductInfo
        fields = ['id', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'parameters']

    def get_parameters(self, obj):
        return {param.parameter.name: param.value 
                for param in obj.product_parameters.all()}

class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer()

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    contact = ContactSerializer()

    class Meta:
        model = Order
        fields = ['id', 'dt', 'state', 'items', 'contact']