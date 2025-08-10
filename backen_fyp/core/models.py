import uuid
from django.db import models
import pandas as pd

# Create your models here.
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, username, full_name, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError(_("Users must have an email address"))
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            full_name=full_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    
    def create_superuser(
        self, email, username, full_name, password=None, **extra_fields
    ):
        """
        Creates and saves a admin with the given email and password.
        """
        user = self.create_user(
            email,
            username,
            full_name,
            password=password,
            **extra_fields,
        )
        user.is_active = True
        user.staff = True
        user.admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
    
    def search_user(self, name):
        return self.filter(Q(username__icontains=name) | Q(full_name__icontains=name))
    
class User(AbstractBaseUser, PermissionsMixin):
    ADMIN = "admin"
    FIELD_TEAM = "field_team"
    GEOSCIENTIST = "geoscientist"
    RESERVOIR_ENGINEER = "reservoir_engineer"
    ENVIRONMENTAL_OFFICER = "environmental_officer"
    MANAGER = "manager"
    NEW_EMPLOYEE = "new_employee"
    USER = "user"

    ROLE_CHOICES = [
        (ADMIN, _('Admin')),
        (FIELD_TEAM, _('Field Team')),
        (GEOSCIENTIST, _('Geoscientist')),
        (RESERVOIR_ENGINEER, _('Reservoir Engineer')),
        (ENVIRONMENTAL_OFFICER, _('Environmental Officer')),
        (MANAGER, _('Manager')),
        (NEW_EMPLOYEE, _('New Employee')),
        (USER, _('User')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=[
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other')),
    ])
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True
    
    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.username

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return True

    @property
    def is_admin(self):
        "Is the user a admin member?"
        # Simplest possible answer: All admins
        return self.admin
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

class SeismicData(models.Model):
    """
    Model representing seismic data.
    """
    CSV_COLUMN_NAMES =[
        'time',
        'latitude',
        'longitude',
        'depth', # Depth of the event
        'mag', # Magnitude
        'magtype', # Type of magnitude
        'nst', # Number of stations reporting
        'gap', # Azimuthal gap
        'dmin', # Minimum distance to nearest station
        'rms', # Root mean square
        'net', # Network code
        'id', # Event ID
        'updated', # Last updated time
        'place', # Location description
        'type', # Event type
        'horizontalerror', # Horizontal error
        'deptherror', # Depth error
        'magerror', # Magnitude error
        'magnst', # Magnitude number of stations
        'status', # Event status
        'locationsource', # Source of location information
        'magsource', # Source of magnitude information
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    csv_file = models.FileField(upload_to='seismic_data/')
    processing_time = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('seismic data')
        verbose_name_plural = _('seismic data')

class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chats')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_chats')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class RoomChat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_chats_user_1')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_chats_user_2')
    chats = models.ManyToManyField(Chat, related_name='room_chats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
