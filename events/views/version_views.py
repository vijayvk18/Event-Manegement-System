from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.helpers import api_response
from events.models.event import Event
from events.models.event_changelog import EventChangeLog
from events.serializers.changelog_serializer import EventChangeLogSerializer
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

            # Get the root event (original version)
            root_event = event.parent_version or event

            # For version 1, use the root event
            if version_id == 1:
                version = root_event
            else:
                try:
                    version = Event.objects.get(parent_version=root_event, version=version_id)
                except Event.DoesNotExist:
                    return api_response(
                        code=status.HTTP_404_NOT_FOUND,
                        message=f"Version {version_id} not found for this event",
                        data=None,
                    )

            serializer = EventVersionSerializer(version)
            return api_response(code=status.HTTP_200_OK, message="Version retrieved successfully", data=serializer.data)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)
        except Exception as e:
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An error occurred while retrieving the version",
                data=str(e),
            )

    def post(self, request, event_id, version_id):
        try:
            event = self.get_event(event_id, request.user)
            if not request.user.has_event_permission(event, "edit"):
                raise PermissionError("You don't have permission to rollback this event")

            # Get the root event (original version)
            root_event = event.parent_version or event

            # For version 1, use the root event
            if version_id == 1:
                target_version = root_event
            else:
                try:
                    target_version = Event.objects.get(parent_version=root_event, version=version_id)
                except Event.DoesNotExist:
                    return api_response(
                        code=status.HTTP_404_NOT_FOUND,
                        message=f"Version {version_id} not found for this event",
                        data=None,
                    )

            # Check if trying to rollback to current version
            if target_version.version == event.version:
                return api_response(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Cannot rollback to version {target_version.version} (current version)",
                    data=None,
                )

            # Create new version by rolling back
            try:
                new_version = event.rollback_to_version(target_version.version, request.user)
                return api_response(
                    code=status.HTTP_200_OK,
                    message="Event rolled back successfully",
                    data=EventVersionSerializer(new_version).data,
                )
            except ValueError as e:
                return api_response(code=status.HTTP_400_BAD_REQUEST, message=str(e), data=None)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)
        except Exception as e:
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An error occurred while rolling back the event",
                data=str(e),
            )


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

    def get(self, request, event_id, version1, version2):
        try:
            event = Event.objects.get(id=event_id)
            if not request.user.has_event_permission(event, "view"):
                return Response(
                    {"error": "You don't have permission to view this event"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            diff = EventChangeLog.get_diff_between_versions(event_id, version1, version2)
            return api_response(
                code=status.HTTP_200_OK,
                message="Version difference retrieved successfully",
                data={
                    "event_id": event_id,
                    "version1": version1,
                    "version2": version2,
                    "changes": diff,
                },
            )
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
