import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models.user import User


class RecurrencePattern(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"
    CUSTOM = "custom", "Custom"


class Event(models.Model):
    RECURRENCE_CHOICES = [
        ("none", "None"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_events")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="updated_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    is_latest = models.BooleanField(default=True)
    parent_version = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="versions"
    )

    # Recurring event fields
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=20, choices=RecurrencePattern.choices, null=True, blank=True)
    recurrence_end_date = models.DateTimeField(null=True, blank=True)
    custom_recurrence = models.JSONField(null=True, blank=True)
    parent_event = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_instances"
    )

    # Participant information
    participants = models.ManyToManyField(User, related_name="participating_events", blank=True)

    class Meta:
        db_table = "events"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["is_latest"]),
        ]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        # Basic validation
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("End date must be after start date")

        if self.is_recurring and not self.recurrence_pattern:
            raise ValueError("Recurrence pattern is required for recurring events")

        if not self.pk:  # New event
            self.created_by = self.owner
            self.updated_by = self.owner
        super().save(*args, **kwargs)

    def create_version(self, user):
        """Create a new version of the event"""
        # Get the root event
        root_event = self.parent_version or self

        # Get the latest version
        latest_version = (
            Event.objects.filter(Q(id=root_event.id) | Q(parent_version=root_event)).order_by("-version").first()
        )

        # Set current version as not latest
        latest_version.is_latest = False
        latest_version.save()

        # Create new version by copying current event
        new_version = Event(
            title=latest_version.title,
            description=latest_version.description,
            start_date=latest_version.start_date,
            end_date=latest_version.end_date,
            location=latest_version.location,
            owner=latest_version.owner,
            created_by=latest_version.created_by,
            version=latest_version.version + 1,
            is_latest=True,
            parent_version=root_event,
            updated_by=user,
            is_recurring=latest_version.is_recurring,
            recurrence_pattern=latest_version.recurrence_pattern,
            recurrence_end_date=latest_version.recurrence_end_date,
            custom_recurrence=latest_version.custom_recurrence,
        )
        new_version.save()

        # Copy permissions from root event to new version
        from events.models.event_permission import EventPermission

        for permission in root_event.permissions.all():
            EventPermission.objects.create(
                event=new_version, user=permission.user, role=permission.role, granted_by=permission.granted_by
            )

        return new_version

    def rollback_to_version(self, version_number, user):
        """Rollback to a specific version"""
        try:
            # Get the latest version of this event
            latest_version = (
                Event.objects.filter(parent_version=self.parent_version or self).order_by("-version").first()
            )

            if not latest_version.is_latest:
                raise ValueError("Can only rollback from the latest version")

            # For version 1, use the root event
            if version_number == 1:
                target_version = self.parent_version or self
            else:
                target_version = Event.objects.get(
                    parent_version=self.parent_version or self,
                    version=version_number,
                )

            new_version = latest_version.create_version(user)

            # Copy fields from target version
            fields_to_copy = [
                "title",
                "description",
                "start_date",
                "end_date",
                "location",
                "is_recurring",
                "recurrence_pattern",
                "recurrence_end_date",
                "custom_recurrence",
            ]

            for field in fields_to_copy:
                setattr(new_version, field, getattr(target_version, field))

            new_version.save()
            return new_version
        except Event.DoesNotExist:
            raise ValueError(f"Version {version_number} does not exist")

    def check_conflicts(self):
        """Check for conflicting events in the same time period"""
        return Event.objects.filter(
            models.Q(start_date__lt=self.end_date) & models.Q(end_date__gt=self.start_date)
        ).exclude(id=self.id)

    def generate_recurring_instances(self, until_date=None):
        """Generate recurring event instances based on the recurrence pattern"""
        if not self.is_recurring or self.parent_event:
            return []

        instances = []
        current_date = self.start_date
        end_date = until_date or self.recurrence_end_date or (self.start_date + timezone.timedelta(days=365))

        while current_date <= end_date:
            if self.recurrence_pattern == RecurrencePattern.DAILY:
                next_date = current_date + timezone.timedelta(days=1)
            elif self.recurrence_pattern == RecurrencePattern.WEEKLY:
                next_date = current_date + timezone.timedelta(weeks=1)
            elif self.recurrence_pattern == RecurrencePattern.MONTHLY:
                next_date = current_date + timezone.timedelta(days=30)  # Simplified
            elif self.recurrence_pattern == RecurrencePattern.YEARLY:
                next_date = current_date + timezone.timedelta(days=365)
            elif self.recurrence_pattern == RecurrencePattern.CUSTOM:
                if not self.custom_recurrence:
                    break
                # Handle custom recurrence based on JSON configuration
                interval = self.custom_recurrence.get("interval", 1)
                unit = self.custom_recurrence.get("unit", "days")
                if unit == "days":
                    next_date = current_date + timezone.timedelta(days=interval)
                elif unit == "weeks":
                    next_date = current_date + timezone.timedelta(weeks=interval)
                elif unit == "months":
                    next_date = current_date + timezone.timedelta(days=30 * interval)
                elif unit == "years":
                    next_date = current_date + timezone.timedelta(days=365 * interval)
                else:
                    break

            if next_date > end_date:
                break

            duration = self.end_date - self.start_date
            instance = Event(
                title=self.title,
                description=self.description,
                start_date=next_date,
                end_date=next_date + duration,
                location=self.location,
                created_by=self.created_by,
                parent_event=self,
                is_recurring=False,
            )
            instances.append(instance)
            current_date = next_date

        return instances
