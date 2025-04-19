# userauths/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


USER_TYPE = (    
    ("Customer", "Customer"),
    ("Vendor", "Vendor"),    
)

class User(AbstractUser):
    username = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):  # sourcery skip: none-compare
        email_username, _ = self.email.split('@')
        if self.username == "" or self.username == None:
            self.username = email_username
        super(User, self).save(*args, **kwargs)
    

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='accounts/users', default='default/default-user.jpg', null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    mobile = models.CharField(max_length=255, null=True, blank=True)
    user_type = models.CharField(max_length=255, choices=USER_TYPE, null=True, blank=True, default=None)
    vendor_license = models.FileField(upload_to='accounts/vendor_licenses/', null=True, blank=True)
    is_approved = models.BooleanField(default=True)  # For customers, it's true by default

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if self.full_name == "" or self.full_name is None:
            self.full_name = self.user.get_full_name()  # safer alternative
        if self.user_type == "Vendor" and self.is_approved is None:
            self.is_approved = False
        super(Profile, self).save(*args, **kwargs)

    

class ContactMessage(models.Model):
    full_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return self.full_name
    
    class Meta:
        ordering = ['-date']