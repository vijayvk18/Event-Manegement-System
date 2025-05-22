from datetime import datetime

from events.models.event_changelog import EventChangeLog


def serialize_datetime(dt):
    """
    Serialize datetime object to ISO format string
    """
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


def create_changelog_entry(
    event, user, change_type, previous_data=None, new_data=None, old_version=None, new_version=None
):
    """
    Create a changelog entry for any event-related change

    Args:
        event: The event object
        user: The user making the change
        change_type: Type of change (create, update, delete, permission_update, etc.)
        previous_data: Data before the change (dict)
        new_data: Data after the change (dict)
        old_version: Previous version of the event
        new_version: New version of the event
    """
    return EventChangeLog.objects.create(
        event=event,
        user=user,
        change_type=change_type,
        previous_data=previous_data,
        new_data=new_data,
        old_version=old_version,
        new_version=new_version,
    )


def get_event_data(event):
    """
    Get complete event data for changelog

    Args:
        event: The event object
    """
    return {
        "title": event.title,
        "description": event.description,
        "start_date": serialize_datetime(event.start_date),
        "end_date": serialize_datetime(event.end_date),
        "location": event.location,
        "is_recurring": event.is_recurring,
        "recurrence_pattern": event.recurrence_pattern,
        "recurrence_end_date": serialize_datetime(event.recurrence_end_date),
        "custom_recurrence": event.custom_recurrence,
        "version": event.version,
        "updated_by": str(event.updated_by.id) if event.updated_by else None,
        "updated_at": serialize_datetime(event.updated_at),
    }


def get_permission_data(permission):
    """
    Get complete permission data for changelog

    Args:
        permission: The permission object
    """
    return {
        "user_id": str(permission.user.id),
        "role": permission.role,
        "granted_by": str(permission.granted_by.id) if permission.granted_by else None,
        "created_at": serialize_datetime(permission.created_at),
        "updated_at": serialize_datetime(permission.updated_at),
    }
