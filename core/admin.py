from django.contrib import admin

from .models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ("event_name", "user", "session_key", "created_at")
    list_filter = ("event_name", "created_at")
    search_fields = ("event_name", "user__username", "user__email", "session_key")

# Register your models here.
