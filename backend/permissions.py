from rest_framework.permissions import BasePermission

class IsSupplier(BasePermission):
    """Проверяет, является ли пользователь поставщиком"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.type == 'shop'