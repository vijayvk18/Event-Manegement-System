from rest_framework import serializers

from core.serializers.user_serializer import UserSerializer
from events.models.event_changelog import EventChangeLog


class EventChangeLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = EventChangeLog
        fields = (
            "id",
            "event",
            "user",
            "change_type",
            "previous_data",
            "new_data",
            "from_version",
            "to_version",
            "created_at",
        )
        read_only_fields = fields


class EventDiffSerializer(serializers.Serializer):
    version1 = serializers.IntegerField()
    version2 = serializers.IntegerField()
    changes = serializers.DictField(read_only=True)
