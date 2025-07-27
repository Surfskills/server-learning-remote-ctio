from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import threading

_thread_locals = threading.local()


# ────────────────
#  User Manager
# ────────────────
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user_type = extra_fields.pop("user_type", User.Types.STUDENT)

        user = self.model(email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_student(self, email, password=None, **extra_fields):
        extra_fields.setdefault("user_type", User.Types.STUDENT)
        return self.create_user(email, password, **extra_fields)

    def create_instructor(self, email, password=None, **extra_fields):
        extra_fields.setdefault("user_type", User.Types.INSTRUCTOR)
        return self.create_user(email, password, **extra_fields)

    def create_support_agent(self, email, password=None, **extra_fields):
        extra_fields.setdefault("user_type", User.Types.SUPPORT_AGENT)
        extra_fields.setdefault("is_staff", True)
        return self.create_user(email, password, **extra_fields)

    def create_admin(self, email, password=None, **extra_fields):
        extra_fields.setdefault("user_type", User.Types.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_admin(email, password, **extra_fields)

    def create_ebook_creator(self, email, password=None, **extra_fields):
        extra_fields.setdefault("user_type", User.Types.EBOOK_CREATOR)
        return self.create_user(email, password, **extra_fields)

    def create_premium_member(self, email, password=None, **extra_fields):
        extra_fields.setdefault("user_type", User.Types.PREMIUM_MEMBER)
        return self.create_user(email, password, **extra_fields)


# ────────────────
#  User Model
# ────────────────
class User(AbstractBaseUser, PermissionsMixin):
    class Types(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"
        STUDENT = "STUDENT", "Student"
        SUPPORT_AGENT = "SUPPORT_AGENT", "Support Agent"
        EBOOK_CREATOR = "EBOOK_CREATOR", "Ebook Creator"
        PREMIUM_MEMBER = "PREMIUM_MEMBER", "Premium Member"

    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    user_type = models.CharField(
        max_length=15,
        choices=Types.choices,
        default=Types.STUDENT
    )

    is_profile_complete = models.BooleanField(default=False)
    profile_completion_percentage = models.PositiveSmallIntegerField(default=0)

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        return self.full_name or self.email.split("@")[0]

    # Role checks
    @property
    def is_admin(self):
        return self.user_type == self.Types.ADMIN

    @property
    def is_instructor(self):
        return self.user_type == self.Types.INSTRUCTOR

    @property
    def is_student(self):
        return self.user_type == self.Types.STUDENT

    @property
    def is_support_agent(self):
        return self.user_type == self.Types.SUPPORT_AGENT
    
    @property
    def is_ebook_creator(self):
        return self.user_type == self.Types.EBOOK_CREATOR

    @property
    def is_premium_member(self):
        return self.user_type == self.Types.PREMIUM_MEMBER

    def calculate_profile_completion(self):
        if not hasattr(_thread_locals, "calculating_completion"):
            _thread_locals.calculating_completion = set()

        key = f"user_{self.pk}"
        if key in _thread_locals.calculating_completion:
            return self.profile_completion_percentage

        try:
            _thread_locals.calculating_completion.add(key)

            fields_present = [
                bool(self.first_name),
                bool(self.last_name),
                bool(self.phone_number),
                bool(self.profile_picture),
            ]
            completed = sum(fields_present)
            total = len(fields_present)

            percentage = int((completed / total) * 100) if total else 0

            User.objects.filter(pk=self.pk).update(
                profile_completion_percentage=percentage,
                is_profile_complete=percentage >= 80,
            )

            self.profile_completion_percentage = percentage
            self.is_profile_complete = percentage >= 80
            return percentage

        finally:
            _thread_locals.calculating_completion.discard(key)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["user_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]


# ────────────────
#  Profile Model
# ────────────────
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    company = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)

    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)

    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def name(self):
        return self.user.full_name or self.user.email

    def __str__(self):
        return f"{self.name}'s profile"

    class Meta:
        indexes = [models.Index(fields=["location"])]