from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role and Department', {'fields': ('role', 'department', 'team')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'team', 'is_staff')
    list_filter = ('role', 'department', 'team', 'is_staff', 'is_superuser')
