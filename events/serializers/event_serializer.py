from rest_framework import serializers

from core.serializers.user_serializer import UserSerializer
from events.models.event import Event
from events.models.event_permission import EventPermission


class EventSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "description",
            "start_date",
            "end_date",
            "location",
            "is_recurring",
            "recurrence_pattern",
            "owner",
            "created_by",
            "updated_by",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_by", "updated_by", "version", "created_at", "updated_at")

    def validate(self, data):
        if data.get("start_date") and data.get("end_date"):
            if data["start_date"] >= data["end_date"]:
                raise serializers.ValidationError("End date must be after start date")
        return data


class EventPermissionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    event = EventSerializer(read_only=True)

    class Meta:
        model = EventPermission
        fields = ("id", "event", "user", "user_id", "role", "granted_by", "created_at", "updated_at")
        read_only_fields = ("id", "granted_by", "created_at", "updated_at")

    def validate(self, data):
        # Ensure user exists
        from core.models.user import User

        try:
            user = User.objects.get(id=data["user_id"])
            data["user"] = user
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return data


class EventVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = (
            "id",
            "version",
            "title",
            "description",
            "start_time",
            "end_time",
            "location",
            "is_recurring",
            "recurrence_pattern",
            "updated_by",
            "updated_at",
        )
        read_only_fields = fields


class BatchEventCreateSerializer(serializers.Serializer):
    events = EventSerializer(many=True)

    def create(self, validated_data):
        events_data = validated_data.pop("events")
        events = []
        for event_data in events_data:
            # Set the created_by field to the current user
            event_data["created_by"] = self.context["request"].user
            event_data["owner"] = self.context["request"].user
            event_data["updated_by"] = self.context["request"].user
            event = Event.objects.create(**event_data)
            events.append(event)
        return events
