# vendor/models.py
from django.utils import timezone  
from django.db import models
from shortuuid.django_fields import ShortUUIDField
from userauths.models import User
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

NOTIFICATION_TYPE = (
    ("New Order", "New Order"),
    ("New Review", "New Review"),
)

PAYOUT_METHOD = (
    ("PayPal", "PayPal"),
    ("Stripe", "Stripe"),    
    ("Nigerian Bank Account", "Nigerian Bank Account"),
    ("Indian Bank Account", "Indian Bank Account"),
    ("USA Bank Account", "USA Bank Account"),
)

TYPE = (
    ("New Order", "New Order"),
    ("Item Shipped", "Item Shipped"),
    ("Item Delivered", "Item Delivered"),
)

NIGERIAN_BANKS = [
    # Commercial Banks
    "Access Bank Plc",
    "Citibank Nigeria Limited",
    "Ecobank Nigeria Limited",
    "Fidelity Bank Plc",
    "First Bank of Nigeria Limited",
    "First City Monument Bank Limited",
    "Globus Bank Limited",
    "Guaranty Trust Bank Plc",
    "Heritage Banking Company Limited",
    "Keystone Bank Limited",
    "Parallex Bank Limited",
    "Polaris Bank Limited",
    "PremiumTrust Bank Limited",
    "Providus Bank Limited",
    "Stanbic IBTC Bank Plc",
    "Standard Chartered Bank Nigeria Limited",
    "Sterling Bank Plc",
    "SunTrust Bank Nigeria Limited",
    "Titan Trust Bank Limited",
    "Union Bank of Nigeria Plc",
    "United Bank for Africa Plc",
    "Unity Bank Plc",
    "Wema Bank Plc",
    "Zenith Bank Plc",
    
    # Non-Interest Banks
    "Jaiz Bank Plc",
    "TajBank Limited",
    "Lotus Bank Limited",
    "Alternative Bank Limited",
    
    # Merchant Banks
    "Coronation Merchant Bank Limited",
    "FBNQuest Merchant Bank Limited",
    "FSDH Merchant Bank Limited",
    "Rand Merchant Bank Nigeria Limited",
    "Nova Merchant Bank Limited",
    
    # Microfinance Banks
    "AB Microfinance Bank Nigeria Limited",
    "Addosser Microfinance Bank Limited",
    "Advans La Fayette Microfinance Bank Limited",
    "Baobab Microfinance Bank Limited",
    "Boctrust Microfinance Bank Limited",
    "Branch International Financial Services Limited",
    "CEMCS Microfinance Bank Limited",
    "Fairmoney Microfinance Bank Limited",
    "Finca Microfinance Bank Limited",
    "Firmus Microfinance Bank Limited",
    "Fortis Microfinance Bank Limited",
    "Fullrange Microfinance Bank Limited",
    "Hasal Microfinance Bank Limited",
    "LAPO Microfinance Bank Limited",
    "Mkobo Microfinance Bank Limited",
    "Money Trust Microfinance Bank Limited",
    "Mutual Trust Microfinance Bank Limited",
    "NPF Microfinance Bank Plc",
    "Peace Microfinance Bank Limited",
    "Pennywise Microfinance Bank Limited",
    "Personal Trust Microfinance Bank Limited",
    "Renmoney Microfinance Bank Limited",
    "Sparkle Microfinance Bank Limited",
    "VFD Microfinance Bank Limited",
    
    # Other Financial Institutions
    "AG Mortgage Bank Plc",
    "Brent Mortgage Bank Limited",
    "Infinity Trust Mortgage Bank Plc",
    "Living Trust Mortgage Bank Plc",
    "Refuge Mortgage Bank Limited",
    "SafeTrust Mortgage Bank Limited"
]

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, related_name="vendor")
    image = models.ImageField(upload_to="vendor_images", default="shop-image.jpg", blank=True)
    store_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Store Name")
    description = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True, verbose_name="Country")
    vendor_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    slug = models.SlugField(blank=True, null=True, unique=True)
    is_approved = models.BooleanField(default=False, verbose_name="Is Approved")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.store_name) if self.store_name else f"Vendor {self.vendor_id}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        # Generate slug if not exists
        if not self.slug and self.store_name:
            self.slug = slugify(self.store_name)
            original_slug = self.slug
            counter = 1
            while Vendor.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Handle approval status changes
        if not is_new:
            try:
                old_vendor = Vendor.objects.get(pk=self.pk)
                if not old_vendor.is_approved and self.is_approved:
                    self.approved_at = timezone.now()
                    self.send_approval_notification()
                elif old_vendor.is_approved and not self.is_approved:
                    self.send_rejection_notification()
            except Vendor.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def send_approval_notification(self):
        """Send email notification when vendor is approved"""
        if self.user and self.user.email:
            subject = "Your Vendor Account Has Been Approved!"
            context = {
                'store_name': self.store_name,
                'login_url': f"{settings.SITE_URL}/auth/sign-in/",
                'dashboard_url': f"{settings.SITE_URL}/vendor/dashboard/",
            }
            
            html_message = render_to_string('email/vendor_approved.html', context)
            text_message = render_to_string('email/vendor_approved.txt', context)
            
            send_mail(
                subject,
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                html_message=html_message,
                fail_silently=True,
            )

    def send_rejection_notification(self):
        """Send email notification when vendor is rejected"""
        if self.user and self.user.email:
            subject = "Your Vendor Account Has Been Rejected"
            context = {
                'store_name': self.store_name,
                'contact_url': f"{settings.SITE_URL}/contact/",
            }
            
            html_message = render_to_string('email/vendor_rejected.html', context)
            text_message = render_to_string('email/vendor_rejected.txt', context)
            
            send_mail(
                subject,
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                html_message=html_message,
                fail_silently=True,
            )

    def send_pending_approval_notification(self):
        """Send email when vendor registers and needs approval"""
        if self.user and self.user.email:
            subject = "Vendor Registration Received"
            context = {
                'store_name': self.store_name,
                'contact_url': f"{settings.SITE_URL}/contact/",
            }
            
            html_message = render_to_string('email/vendor_pending.html', context)
            text_message = render_to_string('email/vendor_pending.txt', context)
            
            send_mail(
                subject,
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                html_message=html_message,
                fail_silently=True,
            )

class Payout(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    item = models.ForeignKey("store.OrderItem", on_delete=models.SET_NULL, null=True, related_name="item")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payout_id = ShortUUIDField(unique=True, length=6, max_length=10, alphabet="1234567890")
    date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return str(self.vendor)
    
    class Meta:
        ordering = ['-date']

class BankAccount(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=100, choices=[(bank, bank) for bank in NIGERIAN_BANKS])
    is_updated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

    class Meta:
        verbose_name_plural = "Bank Accounts"

class PayPalAccount(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE)
    email = models.EmailField()
    is_updated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name_plural = "PayPal Accounts"

class Notifications(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="vendor_notifications")
    type = models.CharField(max_length=100, choices=TYPE, default=None)
    order = models.ForeignKey("store.OrderItem", on_delete=models.CASCADE, null=True, blank=True)
    seen = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return self.type