# userauths/admin.py
from django.contrib import admin
from userauths import models as userauths_models

class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'get_user_type']

    def get_user_type(self, obj):
        return obj.profile.user_type if hasattr(obj, 'profile') else '-'
    get_user_type.short_description = 'User Type'

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'user_type', 'image']
    fieldsets = (
        (None, {
            'fields': ('user', 'full_name', 'user_type', 'image', 'mobile', 'vendor_license')
        }),
    )

class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'subject', 'date']

admin.site.register(userauths_models.User, UserAdmin)
admin.site.register(userauths_models.Profile, ProfileAdmin)
admin.site.register(userauths_models.ContactMessage, ContactMessageAdmin)
