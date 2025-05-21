from django.contrib.auth import authenticate, logout
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from core.helpers import api_response
from core.models import User
from core.serializers.user_serializer import UserLoginSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            data = {
                "user_data": serializer.data,
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            }
            return api_response(code=status.HTTP_201_CREATED, message="User registered successfully", data=data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Get user by email
            try:
                user = User.objects.get(email=serializer.validated_data["email"])
                # Authenticate with username and password
                user = authenticate(username=user.username, password=serializer.validated_data["password"])
                if user:
                    # Create refresh token
                    refresh = RefreshToken.for_user(user)
                    data = {
                        "user_data": UserSerializer(user).data,
                        "refresh_token": str(refresh),
                        "access_token": str(refresh.access_token),
                    }
                    return api_response(code=status.HTTP_200_OK, message="Login successful", data=data)
            except User.DoesNotExist:
                pass
            return api_response(code=status.HTTP_401_UNAUTHORIZED, message="Invalid credentials", data=None)
        return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            # Get the access token from the Authorization header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid token format", data=None)

            token = auth_header.split(" ")[1]

            try:
                # Verify and decode the token
                decoded_token = AccessToken(token)
                user_id = decoded_token["user_id"]

                # Get all outstanding tokens for this user
                user_tokens = OutstandingToken.objects.filter(user_id=user_id)

                # Blacklist all tokens for this user
                for token_obj in user_tokens:
                    BlacklistedToken.objects.get_or_create(token=token_obj)

                # Clear the session
                if request.session:
                    request.session.flush()

                # Logout the user
                logout(request)

                return api_response(code=status.HTTP_200_OK, message="Logout successful", data="done")

            except (TokenError, InvalidToken) as e:
                return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid token", data=str(e))

        except Exception as e:
            return api_response(code=status.HTTP_400_BAD_REQUEST, message="Logout failed", data=str(e))
