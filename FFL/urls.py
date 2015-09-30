from django.conf.urls import url

from FFL import views
from FFL.players import views as players_views
from FFL.teams import views as teams_views

urlpatterns = [
    url(r'^$', views.home),

    url(r'^submit-team/$', teams_views.submit_team),
    url(r'^league/$', teams_views.league),
    url(r'^weeklyperformance/$', teams_views.weekly_performance),
    url(r'^graph/$', teams_views.graph),

    url(r'^goalkeepers/$', players_views.goalkeepers),
    url(r'^defenders/$', players_views.defenders),
    url(r'^midfielders/$', players_views.midfielders),
    url(r'^strikers/$', players_views.strikers),

    url(r'^player/(\d{4})/$', players_views.player, name='player'),
    url(r'^player/wp/([1-4]\d{3})/$', players_views.player_wp),
    
    url(r'^team/([a-z-]+)/$', teams_views.team),
    url(r'^team/wp/([a-z-]+)/$', teams_views.team_wp),
    url(r'^graph/([\d-]+)/$', teams_views.graph),
    url(r'^graph/plot/([\d-]+)/$', teams_views.graph_plot),
    url(r'^league/joke/$', teams_views.joke_league),
    url(r'^team/([a-z-]+)/week/(\d{1,2})/$', teams_views.team),
    url(r'^weeklyperformance/(\d{1,2})-(\d{1,2})/$', teams_views.weekly_performance),
    url(r'^graph/teams/([\d-]+)/weeks/(\d+)-(\d+)/$', teams_views.graph),
    url(r'^graph/teams/([\d-]+)/$', teams_views.graph),
    url(r'^graph/plot/teams/([\d-]+)/weeks/(\d+)-(\d+)/$', teams_views.graph_plot),
    url(r'^graph/plot/teams/([\d-]+)/$', teams_views.graph_plot),
    url(r'^formations/pie/$', teams_views.formations_pie),   
    
    url(r'^export-players/csv/$', players_views.players_csv),
    url(r'^export-players/goalkeepers/csv/$', players_views.goalkeepers_csv),
    url(r'^export-players/defenders/csv/$', players_views.defenders_csv),
    url(r'^export-players/midfielders/csv/$', players_views.midfielders_csv),
    url(r'^export-players/strikers/csv/$', players_views.strikers_csv),
    
    url(r'^import-players/$', players_views.import_players),
    
    url(r'^team-submitted/$', teams_views.team_submitted),
    url(r'^players-imported/$', players_views.players_imported)
]
