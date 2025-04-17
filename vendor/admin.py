# vendor/admin.py
from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from vendor import models as vendor_models
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .models import BankAccount, PayPalAccount

# Standalone approval functions (for direct URL access)
@staff_member_required
def approve_vendor(request, vendor_id):
    vendor = get_object_or_404(vendor_models.Vendor, id=vendor_id)
    vendor.is_approved = True
    vendor.approved_at = timezone.now()
    vendor.save()
    
    # Send approval email
    _send_vendor_email(request, vendor, is_approved=True)
    messages.success(request, f"Vendor {vendor.store_name} approved")
    return redirect('admin:vendor_vendor_changelist')

@staff_member_required
def reject_vendor(request, vendor_id):
    vendor = get_object_or_404(vendor_models.Vendor, id=vendor_id)
    vendor.is_approved = False
    vendor.save()
    
    # Send rejection email
    _send_vendor_email(request, vendor, is_approved=False)
    messages.success(request, f"Vendor {vendor.store_name} rejected")
    return redirect('admin:vendor_vendor_changelist')

def _send_vendor_email(request, vendor, is_approved):
    """Shared function to send vendor approval/rejection emails"""
    status = "approved" if is_approved else "rejected"
    subject = f"Vendor Account {status.capitalize()}"
    
    if is_approved:
        message = f"""Dear {vendor.store_name},

        Your vendor account has been approved.

        You can now access your vendor dashboard and start adding products.

        Thank you,
        The Admin Team"""
    else:
        message = f"""Dear {vendor.store_name},

        Your vendor account has been rejected.

        Please contact support if you believe this was a mistake.

        Thank you,
        The Admin Team"""
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [vendor.user.email],
            fail_silently=False,
        )
    except Exception as e:
        messages.error(request, f"Failed to send email: {str(e)}")

# Admin interface configuration
@admin.register(vendor_models.Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'is_approved', 'approval_status', 'date', 'approval_actions']
    list_editable = ['is_approved']
    search_fields = ['store_name', 'user__username', 'vendor_id']
    prepopulated_fields = {'slug': ('store_name',)}
    list_filter = ['is_approved', 'date', 'country']
    actions = ['approve_selected_vendors', 'reject_selected_vendors']
    readonly_fields = ['approved_at', 'vendor_id', 'created_at']
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: green;">Approved</span>')
        return format_html('<span style="color: orange;">Pending</span>')
    approval_status.short_description = 'Status'
    
    def approval_actions(self, obj):
        if not obj.is_approved:
            return format_html(
                '<a class="button" href="{}">Approve</a>&nbsp;'
                '<a class="button" href="{}">Reject</a>',
                reverse('admin:vendor_vendor_approve', args=[obj.id]),
                reverse('admin:vendor_vendor_reject', args=[obj.id]),
            )
        return format_html('<span style="color: green;">No action needed</span>')
    approval_actions.short_description = 'Actions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/approve/',
                    self.admin_site.admin_view(self.process_approval),
                    name='vendor_vendor_approve'),
            path('<path:object_id>/reject/',
                    self.admin_site.admin_view(self.process_rejection),
                    name='vendor_vendor_reject'),
        ]
        return custom_urls + urls
    
    def process_approval(self, request, object_id):
        return self._process_vendor_status(request, object_id, is_approved=True)
    
    def process_rejection(self, request, object_id):
        return self._process_vendor_status(request, object_id, is_approved=False)
    
    def _process_vendor_status(self, request, object_id, is_approved):
        vendor = self.get_object(request, object_id)
        if vendor:
            vendor.is_approved = is_approved
            if is_approved:
                vendor.approved_at = timezone.now()
            vendor.save()
            _send_vendor_email(request, vendor, is_approved)
            status = "approved" if is_approved else "rejected"
            self.message_user(request, f"Vendor {vendor.store_name} {status}")
        return redirect('admin:vendor_vendor_changelist')
    
    def approve_selected_vendors(self, request, queryset):
        updated = queryset.update(is_approved=True, approved_at=timezone.now())
        for vendor in queryset.filter(is_approved=True):
            _send_vendor_email(request, vendor, is_approved=True)
        self.message_user(request, f"Successfully approved {updated} vendors")
    approve_selected_vendors.short_description = "Approve selected vendors"
    
    def reject_selected_vendors(self, request, queryset):
        updated = queryset.update(is_approved=False)
        for vendor in queryset.filter(is_approved=False):
            _send_vendor_email(request, vendor, is_approved=False)
        self.message_user(request, f"Successfully rejected {updated} vendors")
    reject_selected_vendors.short_description = "Reject selected vendors"
    
    def save_model(self, request, obj, form, change):
        if 'is_approved' in form.changed_data:
            if obj.is_approved:
                obj.approved_at = timezone.now()
            _send_vendor_email(request, obj, obj.is_approved)
        super().save_model(request, obj, form, change)

# Other admin models
@admin.register(vendor_models.Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['payout_id', 'vendor', 'item', 'amount', 'date']
    search_fields = ['payout_id', 'vendor__store_name', 'item__order__order_id']
    list_filter = ['date', 'vendor']
    readonly_fields = ['payout_id', 'date']

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'account_name', 'account_number', 'bank_name', 'is_updated', 'updated_at']
    list_filter = ['is_updated', 'bank_name']
    search_fields = ['vendor__store_name', 'account_name', 'account_number']
    readonly_fields = ['created_at', 'updated_at']
    
@admin.register(PayPalAccount)
class PayPalAccountAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'email', 'is_updated', 'updated_at']
    list_filter = ['is_updated']
    search_fields = ['vendor__store_name', 'email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(vendor_models.Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'order', 'seen', 'date']
    list_filter = ['type', 'seen', 'date']
    search_fields = ['user__username', 'type']
    readonly_fields = ['date']