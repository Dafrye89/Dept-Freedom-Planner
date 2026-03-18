from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Profile, SubscriptionAccess


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "username", "is_staff", "is_superuser", "created_at")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = UserAdmin.fieldsets + (
        ("Planner Metadata", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("email",)}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "timezone", "marketing_opt_in")
    search_fields = ("user__username", "user__email", "display_name")


@admin.register(SubscriptionAccess)
class SubscriptionAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "lifetime_override", "paid_activated_at")
    list_filter = ("tier", "lifetime_override")
    search_fields = ("user__username", "user__email")

# Register your models here.
