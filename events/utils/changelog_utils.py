from events.models.event_changelog import EventChangeLog


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
        "start_date": event.start_date.isoformat(),
        "end_date": event.end_date.isoformat(),
        "location": event.location,
        "is_recurring": event.is_recurring,
        "recurrence_pattern": event.recurrence_pattern,
        "recurrence_end_date": event.recurrence_end_date.isoformat() if event.recurrence_end_date else None,
        "custom_recurrence": event.custom_recurrence,
        "version": event.version,
        "updated_by": str(event.updated_by.id) if event.updated_by else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
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
        "created_at": permission.created_at.isoformat() if permission.created_at else None,
        "updated_at": permission.updated_at.isoformat() if permission.updated_at else None,
    }
