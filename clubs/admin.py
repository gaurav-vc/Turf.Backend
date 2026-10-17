from django.contrib import admin
from .models import Club, ClubMember, ClubTournament, ClubMatch, LiveMatchTimerState, LiveCricketScorecard

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'privacy', 'invite_code', 'created_at']
    search_fields = ['name', 'owner__email', 'invite_code']

@admin.register(ClubMember)
class ClubMemberAdmin(admin.ModelAdmin):
    list_display = ['club', 'user', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['club__name', 'user__email']

@admin.register(ClubTournament)
class ClubTournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'club', 'status', 'is_recurring', 'start_date']
    list_filter = ['status', 'is_recurring']
    search_fields = ['name', 'club__name']

@admin.register(ClubMatch)
class ClubMatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'club', 'team1', 'team2', 'match_date', 'status', 'wickets_allowed', 'is_last_match']
    list_filter = ['status', 'is_last_match']
    search_fields = ['club__name', 'team1__name', 'team2__name']

@admin.register(LiveMatchTimerState)
class LiveMatchTimerStateAdmin(admin.ModelAdmin):
    list_display = ['match', 'current_inning', 'inning_duration_seconds', 'is_running', 'is_paused', 'elapsed_playing_seconds', 'total_pause_stoppage_seconds']

@admin.register(LiveCricketScorecard)
class LiveCricketScorecardAdmin(admin.ModelAdmin):
    list_display = ['match', 'total_runs', 'wickets_down', 'balls_bowled']
