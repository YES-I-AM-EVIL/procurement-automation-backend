from django.core.exceptions import ValidationError
import re

def validate_password(password):
    if len(password) < 8:
        raise ValidationError("Пароль должен содержать минимум 8 символов")
    if not re.findall('[A-Z]', password):
        raise ValidationError("Пароль должен содержать хотя бы одну заглавную букву")

def validate_phone(phone):
    if not re.match(r'^\+7\d{10}$', phone):
        raise ValidationError("Телефон должен быть в формате +7XXXXXXXXXX")