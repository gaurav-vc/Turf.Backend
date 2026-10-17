from django.contrib import admin
from .models import Sport, RuleSet, Team, Player, Tournament, TournamentTeam, Match

@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'team_size_min', 'team_size_max')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(RuleSet)
admin.site.register(Team)
admin.site.register(Player)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'organizer', 'tournament_type', 'status')
    list_filter = ('tournament_type', 'status', 'privacy')

admin.site.register(TournamentTeam)
admin.site.register(Match)
