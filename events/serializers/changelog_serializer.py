from rest_framework import serializers

from core.serializers.user_serializer import UserSerializer
from events.models.event_changelog import EventChangeLog


class EventChangeLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    old_version_number = serializers.SerializerMethodField()
    new_version_number = serializers.SerializerMethodField()

    class Meta:
        model = EventChangeLog
        fields = (
            "id",
            "event",
            "user",
            "change_type",
            "previous_data",
            "new_data",
            "old_version",
            "new_version",
            "old_version_number",
            "new_version_number",
            "created_at",
        )
        read_only_fields = fields

    def get_old_version_number(self, obj):
        return obj.old_version.version if obj.old_version else None

    def get_new_version_number(self, obj):
        return obj.new_version.version if obj.new_version else None


class EventDiffSerializer(serializers.Serializer):
    version1 = serializers.IntegerField()
    version2 = serializers.IntegerField()
    changes = serializers.DictField(read_only=True)
