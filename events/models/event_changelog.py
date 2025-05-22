import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from core.models.user import User
from events.models.event import Event


class EventChangeLog(models.Model):
    CHANGE_TYPES = (
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("permission_add", "Permission Add"),
        ("permission_update", "Permission Update"),
        ("permission_delete", "Permission Delete"),
        ("field_update", "Field Update"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="changelogs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="event_changes")
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    previous_data = models.JSONField(null=True, encoder=DjangoJSONEncoder)
    new_data = models.JSONField(null=True, encoder=DjangoJSONEncoder)
    old_version = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, related_name="old_version_changes")
    new_version = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, related_name="new_version_changes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event.title} - {self.change_type} by {self.user.email} at {self.created_at}"

    @property
    def diff(self):
        """
        Calculate the difference between previous and new data
        Returns a dictionary of changed fields with their old and new values
        """
        if not self.previous_data or not self.new_data:
            return {}

        diff_data = {}
        all_keys = set(self.previous_data.keys()) | set(self.new_data.keys())

        for key in all_keys:
            old_value = self.previous_data.get(key)
            new_value = self.new_data.get(key)

            if old_value != new_value:
                diff_data[key] = {"old": old_value, "new": new_value}

        return diff_data

    @classmethod
    def log_change(cls, event, user, change_type, previous_data=None, new_data=None):
        """
        Create a new changelog entry
        """
        return cls.objects.create(
            event=event,
            user=user,
            change_type=change_type,
            previous_data=previous_data,
            new_data=new_data,
            from_version=event.version - 1 if change_type != "create" else 0,
            to_version=event.version,
        )

    @classmethod
    def get_diff_between_versions(cls, event_id, version1, version2):
        """
        Get the difference between two versions of an event
        """
        try:
            changelog = cls.objects.get(
                event_id=event_id, from_version=min(version1, version2), to_version=max(version1, version2)
            )
            return changelog.diff
        except cls.DoesNotExist:
            # If direct changelog not found, we need to aggregate changes
            changelogs = cls.objects.filter(
                event_id=event_id, from_version__gte=min(version1, version2), to_version__lte=max(version1, version2)
            ).order_by("from_version")

            if not changelogs:
                return {}

            # Aggregate changes
            aggregated_diff = {}
            for log in changelogs:
                diff = log.diff
                for field, changes in diff.items():
                    if field not in aggregated_diff:
                        aggregated_diff[field] = {"old": changes["old"], "new": changes["new"]}
                    else:
                        aggregated_diff[field]["new"] = changes["new"]

            return aggregated_diff
