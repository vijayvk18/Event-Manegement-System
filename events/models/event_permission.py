import uuid

from django.db import models
from django.utils import timezone

from core.models.user import User
from events.models.event import Event


class EventPermission(models.Model):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="permissions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_permissions")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="granted_permissions")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_permissions"
        unique_together = ("event", "user")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "user"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.event.title} ({self.role})"

    def save(self, *args, **kwargs):
        # Ensure owner role is unique per event
        if self.role == "owner":
            existing_owner = EventPermission.objects.filter(event=self.event, role="owner").exclude(pk=self.pk).exists()

            if existing_owner:
                raise ValueError("Event already has an owner")

        super().save(*args, **kwargs)

    @property
    def can_edit(self):
        return self.role in ["owner", "editor"]

    @property
    def can_delete(self):
        return self.role == "owner"

    @property
    def can_manage_permissions(self):
        return self.role == "owner"
