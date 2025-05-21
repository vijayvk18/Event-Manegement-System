from rest_framework.response import Response


def api_response(code, message, data, status=None):
    data = {
        "status": status if status is not None else code,
        "message": message,
        "data": data,
    }
    return Response(data=data, status=code)
