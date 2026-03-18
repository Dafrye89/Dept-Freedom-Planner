from core.models import EventLog


def log_event(event_name, *, user=None, session_key="", metadata=None):
    EventLog.objects.create(
        event_name=event_name,
        user=user if getattr(user, "is_authenticated", False) else None,
        session_key=session_key or "",
        metadata=metadata or {},
    )
