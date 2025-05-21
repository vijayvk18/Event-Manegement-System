from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from events.models.event import Event
from events.models.event_changelog import EventChangeLog
from events.models.event_permission import EventPermission


class EventService:
    @staticmethod
    def check_conflicts(event, participants=None):
        """
        Check for event conflicts and return conflicting events
        """
        conflicts = Event.objects.filter(Q(start_date__lt=event.end_date) & Q(end_date__gt=event.start_date)).exclude(
            id=event.id
        )

        if participants:
            conflicts = conflicts.filter(participants__in=participants)

        return conflicts

    @staticmethod
    def suggest_alternative_slots(event, conflicts, num_suggestions=3):
        """
        Suggest alternative time slots for conflicting events
        """
        suggestions = []
        duration = event.end_date - event.start_date

        # Try slots after the original time
        current_start = event.end_date
        while len(suggestions) < num_suggestions:
            potential_end = current_start + duration
            conflicts = Event.objects.filter(Q(start_date__lt=potential_end) & Q(end_date__gt=current_start))

            if not conflicts.exists():
                suggestions.append({"start_date": current_start, "end_date": potential_end})

            current_start = current_start + duration

        return suggestions

    @staticmethod
    @transaction.atomic
    def create_event(data, user):
        """Create an event with permissions and handle recurring instances"""
        # Check for conflicts
        temp_event = Event(
            start_date=data["start_date"], end_date=data["end_date"], participants=data.get("participants", [])
        )

        conflicts = EventService.check_conflicts(temp_event, data.get("participants"))

        if conflicts.exists():
            if data.get("force_create", False):
                # Create anyway if force flag is set
                pass
            else:
                # Suggest alternative slots
                suggestions = EventService.suggest_alternative_slots(temp_event, conflicts)
                raise ValidationError(
                    {"conflicts": conflicts.values("id", "title", "start_date", "end_date"), "suggestions": suggestions}
                )

        # Start transaction
        with transaction.atomic():
            # Create the event
            event = Event.objects.create(
                title=data["title"],
                description=data.get("description", ""),
                start_date=data["start_date"],
                end_date=data["end_date"],
                location=data.get("location", ""),
                created_by=user,
                owner=user,
                is_recurring=data.get("is_recurring", False),
                recurrence_pattern=data.get("recurrence_pattern"),
                recurrence_end_date=data.get("recurrence_end_date"),
                custom_recurrence=data.get("custom_recurrence"),
            )

            # Create owner permission
            EventPermission.objects.create(event=event, user=user, role="owner")

            # Create change log entry
            EventChangeLog.objects.create(
                event=event,
                user=user,
                action="create",
                changes={
                    "title": event.title,
                    "description": event.description,
                    "start_date": event.start_date.isoformat(),
                    "end_date": event.end_date.isoformat(),
                    "location": event.location,
                },
            )

            # Generate recurring instances if needed
            if event.is_recurring:
                instances = event.generate_recurring_instances()
                for instance in instances:
                    instance.save()
                    # Create permissions for recurring instances
                    EventPermission.objects.create(event=instance, user=user, role="owner")

            return event

    @staticmethod
    @transaction.atomic
    def update_event(event_id, data, user):
        """Update an event with change tracking"""
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)

            # Check permissions
            if not EventPermission.objects.filter(event=event, user=user, role__in=["owner", "editor"]).exists():
                raise ValidationError("User does not have permission to update this event")

            # Track changes
            changes = {}
            for field, value in data.items():
                if hasattr(event, field) and getattr(event, field) != value:
                    changes[field] = value
                    setattr(event, field, value)

            if changes:
                event.updated_by = user
                event.save()

                # Create change log entry
                EventChangeLog.objects.create(event=event, user=user, action="update", changes=changes)

                # Update recurring instances if needed
                if event.is_recurring and not event.parent_event:
                    Event.objects.filter(parent_event=event).delete()
                    instances = event.generate_recurring_instances()
                    for instance in instances:
                        instance.save()

            return event

    @staticmethod
    @transaction.atomic
    def delete_event(event_id, user):
        """Delete an event and its related data"""
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)

            # Check permissions
            if not EventPermission.objects.filter(event=event, user=user, role="owner").exists():
                raise ValidationError("User does not have permission to delete this event")

            # Delete recurring instances if this is a parent event
            if event.is_recurring and not event.parent_event:
                Event.objects.filter(parent_event=event).delete()

            # Create change log entry before deletion
            EventChangeLog.objects.create(event=event, user=user, action="delete", changes={})

            event.delete()

    @staticmethod
    @transaction.atomic
    def batch_create_events(events_data, user):
        """Create multiple events in a single transaction"""
        created_events = []
        with transaction.atomic():
            for event_data in events_data:
                event = EventService.create_event(event_data, user)
                created_events.append(event)
        return created_events

    @staticmethod
    @transaction.atomic
    def update_event_permissions(event_id, permissions_data, user):
        """Update event permissions in a single transaction"""
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)

            # Check if user is owner
            if not EventPermission.objects.filter(event=event, user=user, role="owner").exists():
                raise ValidationError("Only event owner can modify permissions")

            # Update permissions
            current_permissions = set(EventPermission.objects.filter(event=event).values_list("user_id", "role"))
            new_permissions = set((p["user_id"], p["role"]) for p in permissions_data)

            # Remove old permissions
            to_remove = current_permissions - new_permissions
            for user_id, role in to_remove:
                EventPermission.objects.filter(event=event, user_id=user_id, role=role).delete()

            # Add new permissions
            to_add = new_permissions - current_permissions
            for user_id, role in to_add:
                EventPermission.objects.create(event=event, user_id=user_id, role=role)

            # Log changes
            EventChangeLog.objects.create(
                event=event, user=user, action="permission_update", changes={"permissions": permissions_data}
            )
