from __future__ import print_function, division

from operator import attrgetter

from django.db import models

from FFL.game.formation import Formation
from FFL.game import telegraph, gameinfo

POSITION_CHOICES = zip(Formation.labels, Formation.labels)


class WeekPointsManager(models.Manager):
    use_in_related_fields = True
    def points(self, players, week):
        return (self.filter(player__in=players).filter(week=week)
                .aggregate(models.Sum('points'))['points__sum'])

    def latest_week(self):
        week = self.aggregate(models.Max('week'))['week__max']
        if week is None:
            return 0
        else:
            return int(week)
        
    def week_best(self, week):
        if not week:
            week = gameinfo.gameWeek()
            
        query_set = self.none()
        week_points = self.filter(week=week).select_related()
        for position in Formation.labels:
            position_points = week_points.filter(player__position=position)
            points = position_points.aggregate(models.Max('points'))['points__max']
            query_set = query_set | position_points.filter(points=points)
        
        return query_set


class PlayerManager(models.Manager):
    def name(self, name):
        return self.get(name__iexact=name)
    
    def code(self, code):
        return self.get(code=code)
    
    def position(self, position):
        return self.filter(position=position).order_by('-value')

    def new_players(self, week):
        return self.filter(date_added__gte=gameinfo.weekToDate(week))

    def _add_player(self, player):
        p = self.model(**player)
        p.club = telegraph.PlayerUpdate(p.code).club()
        p.save()

    def import_players(self):
        player_list = telegraph.PlayerList()
        for player in player_list.players():
            self._add_player(player)

    def add_new_players(self):
        player_list = telegraph.PlayerList()
        for player in player_list.players():
            if not self.filter(code=player['code']).exists():
                self._add_player(player)
                
    def update(self):
        game_week = gameinfo.gameWeek()
        length = self.count()

        for i, player in enumerate(self.all()):
            player_update = telegraph.PlayerUpdate(player.code)
            
            player.club = player_update.club()

            week_points = [0]*game_week
            if player.club:
                points_list = player_update.points()
            else:
                # keep the points as they are as they may have been removed from the website
                points_list = player.weekly_points.values_list('week', 'points')
            
            for week, points in points_list:
                week_points[week-1] += points

            WeekPoints.objects.filter(player=player).delete()

            for week, points in enumerate(week_points):
                WeekPoints.objects.create(player=player, week=week+1, points=points)
                
            player.games = player_update.games()
            player.total_points = player_update.total_points()
            
            player.save()
            
            yield "{0} ({1:d}/{2:d})".format(player.name, i+1, length)

 
class PlayerStatsManager(models.Manager):
    def most_popular(self):
        return self._best('teams')
    
    def best_value(self):
        return self._best('pv')
    
    def most_points(self):
        return self._best('total_points')
    
    def _best(self, field):
        try:
            self.model._meta.get_field_by_name(field)
        except models.FieldDoesNotExist: # might be a computed property
            return {position: sorted(self.filter(position=position),
                                     key=attrgetter(field))[-1]
                        for position in Formation.labels}
        else:
            return {position: self.filter(position=position).order_by('-'+field)[0]
                        for position in Formation.labels}


class Player(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    value = models.DecimalField(max_digits=2, decimal_places=1)
    club = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=10, choices=POSITION_CHOICES)
    games = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    is_playing = models.IntegerField(default=1) # BooleanField
    date_added = models.DateField(default=gameinfo.startDate)
    
    class Meta:
        ordering = ['code']
        
    def points_sum(self, from_week, to_week):
        points = (self.weekly_points.filter(week__gte=from_week, week__lte=to_week)
                  .aggregate(models.Sum('points'))['points__sum'])
        if points is None:
            return 0
        else:
            return points
    
    def points(self, week):
        try:
            return self.weekly_points.get(week=week).points
        except WeekPoints.DoesNotExist:
            return 0
        
    def subbed_by(self):
        return self.team_set.filter(squad__week_out__isnull=False).order_by('league_position')
    
    def playing_for(self):
        return self.team_set.filter(squad__week_out__isnull=True).order_by('league_position')

    def __unicode__(self):
        return u"{0} {1}".format(self.value, self.name)
    
    def _pv(self):
        return self.total_points / self.value
    
    def _pg(self):
        try:
            return self.total_points / self.games
        except ZeroDivisionError:
            return 0
            
    def _teams(self):
        return self.team_set.count()
    
    pv = property(_pv)
    pg = property(_pg)
    teams = property(_teams)
    
    objects = PlayerManager()
    stats = PlayerStatsManager()


class WeekPoints(models.Model):
    player = models.ForeignKey(Player, related_name="weekly_points")
    week = models.IntegerField()
    points = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['player']
        
    objects = WeekPointsManager()
