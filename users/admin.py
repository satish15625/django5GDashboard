# admin.py
from django.contrib import admin
from .models import SMTPConfig

@admin.register(SMTPConfig)
class SMTPConfigAdmin(admin.ModelAdmin):
    list_display = ('username', 'host', 'port', 'use_tls', 'active')
