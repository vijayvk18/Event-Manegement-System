import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not username:
            raise ValueError("The Username field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.OWNER)

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # Role choices as per requirements
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"

    ROLE_CHOICES = [
        (OWNER, "Owner"),
        (EDITOR, "Editor"),
        (VIEWER, "Viewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=VIEWER)

    # Personal Info
    full_name = models.CharField(max_length=255, blank=True)

    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name or self.username

    def has_event_permission(self, event, permission_type):
        """Check if user has specific permission for an event"""
        if self.is_superuser:
            return True

        try:
            event_permission = self.event_permissions.get(event=event)
            if permission_type == "view":
                return True
            elif permission_type == "edit":
                return event_permission.role in [self.OWNER, self.EDITOR]
            elif permission_type == "delete":
                return event_permission.role == self.OWNER
            return False
        except models.ObjectDoesNotExist:
            return False

    @property
    def is_admin(self):
        return self.role == self.OWNER

    @property
    def is_manager(self):
        return self.role == self.EDITOR

    def has_permission(self, permission_type):
        """
        Check if user has specific permission based on their role
        """
        if self.is_admin:
            return True
        elif self.is_manager:
            return permission_type in ["view", "create", "edit"]
        else:
            return permission_type == "view"
