from django.contrib import admin
from .models import LiveStream

@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'is_live', 'viewer_count', 'created_at')
    list_filter = ('is_live',)
    search_fields = ('title', 'organizer__username', 'organizer__first_name')
    list_editable = ('is_live',)
