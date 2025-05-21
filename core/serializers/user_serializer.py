import re

from rest_framework import serializers

from core.models.user import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "role",
            "full_name",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined", "is_active", "username")

    def generate_username(self, full_name):
        if not full_name:
            raise serializers.ValidationError("Full name is required to generate username")

        # Convert full name to lowercase and remove special characters
        base_username = re.sub(r"[^a-z0-9]", "", full_name.lower())
        if not base_username:
            raise serializers.ValidationError("Full name must contain at least one alphanumeric character")

        # Take first 8 characters of the name
        base_username = base_username[:8]

        # Check if username exists, if yes append a number
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        return username

    def create(self, validated_data):
        # Get full_name and ensure it exists
        full_name = validated_data.get("full_name")
        if not full_name:
            raise serializers.ValidationError("Full name is required")

        # Generate username from full name
        username = self.generate_username(full_name)

        # Create user with generated username
        user = User.objects.create_user(
            email=validated_data.pop("email"),
            username=username,
            password=validated_data.pop("password"),
            **validated_data,
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "email")
        read_only_fields = ("id", "username", "role")
