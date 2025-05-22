from rest_framework import serializers

from events.models.event_permission import EventPermission


class EventPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventPermission
        fields = ["id", "user", "role", "granted_by", "created_at", "updated_at"]
        read_only_fields = ["id", "granted_by", "created_at", "updated_at"]

    def validate(self, data):
        # Ensure only one owner per event
        if data.get("role") == "owner":
            event = self.context.get("event")
            if event and EventPermission.objects.filter(event=event, role="owner").exists():
                raise serializers.ValidationError("An event can only have one owner")
        return data
