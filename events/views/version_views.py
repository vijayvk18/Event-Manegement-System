from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.helpers import api_response
from events.models.event import Event
from events.models.event_changelog import EventChangeLog
from events.serializers.changelog_serializer import EventChangeLogSerializer, EventDiffSerializer
from events.serializers.event_serializer import EventVersionSerializer


class EventVersionView(APIView):
    permission_classes = [IsAuthenticated]

    def get_event(self, pk, user):
        event = get_object_or_404(Event, pk=pk)
        if not user.has_event_permission(event, "view"):
            raise PermissionError("You don't have permission to access this event")
        return event

    def get(self, request, event_id, version_id):
        try:
            event = self.get_event(event_id, request.user)
            version = get_object_or_404(Event, parent_version=event.parent_version or event, version=version_id)
            serializer = EventVersionSerializer(version)
            return api_response(code=status.HTTP_200_OK, message="Version retrieved successfully", data=serializer.data)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)

    def post(self, request, event_id, version_id):
        try:
            event = self.get_event(event_id, request.user)
            if not request.user.has_event_permission(event, "edit"):
                raise PermissionError("You don't have permission to rollback this event")

            version = get_object_or_404(Event, parent_version=event.parent_version or event, version=version_id)
            new_version = event.rollback_to_version(version.version, request.user)

            return api_response(
                code=status.HTTP_200_OK,
                message="Event rolled back successfully",
                data=EventVersionSerializer(new_version).data,
            )
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)


class EventChangeLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get_event(self, pk, user):
        event = get_object_or_404(Event, pk=pk)
        if not user.has_event_permission(event, "view"):
            raise PermissionError("You don't have permission to access this event")
        return event

    def get(self, request, event_id):
        try:
            event = self.get_event(event_id, request.user)
            changelogs = EventChangeLog.objects.filter(event=event)
            serializer = EventChangeLogSerializer(changelogs, many=True)
            return api_response(
                code=status.HTTP_200_OK, message="Changelog retrieved successfully", data=serializer.data
            )
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)


class EventDiffView(APIView):
    permission_classes = [IsAuthenticated]

    def get_event(self, pk, user):
        event = get_object_or_404(Event, pk=pk)
        if not user.has_event_permission(event, "view"):
            raise PermissionError("You don't have permission to access this event")
        return event

    def get(self, request, event_id, version1, version2):
        try:
            event = self.get_event(event_id, request.user)
            diff = EventChangeLog.get_diff_between_versions(event_id, version1, version2)

            serializer = EventDiffSerializer(data={"version1": version1, "version2": version2, "changes": diff})
            serializer.is_valid()  # Will always be valid as we construct it

            return api_response(code=status.HTTP_200_OK, message="Diff retrieved successfully", data=serializer.data)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)
