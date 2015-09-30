from __future__ import print_function

from django.db import models

from FFL.players.models import Player
from FFL.game.formation import Formation
from FFL.game import gameinfo

TEAM_TYPE_CHOICES = (('N', 'Normal team'),
                     ('J', 'Joke team'))

FORMATION_CHOICES = zip(Formation.formations, Formation.formation_labels)


class TeamManager(models.Manager):
    def manager(self, manager):
        return self.get(manager__iexact=manager)
    
    def league(self, week):
        return self.filter(weekly_points__week__lte=week).annotate(
            sum=models.Sum('weekly_points__points')).order_by('-sum', 'id')
    
    def set_points(self, game_week):
        length = self.count()
        
        for i, team in enumerate(self.select_related().all()):
            #set the points for all the players in the squad
            for player in team.squad.all():
                player.set_points(game_week)
                
            #add up the points for all the players in the squad
            team.total_points = team.squad.aggregate(models.Sum('points'))['points__sum']
    
            #set the points for every game week
            total_weekly_points = 0
            for week in range(1, game_week+1):
                players = team.squad.in_team(week)
                assert players.count() in (0, 11)
                points = sum(p.player.points(week) for p in players)
                total_weekly_points += points
                team.weekly_points.create(week=week, points=points)
                
            #belts and braces check that the totals are consistent
            assert team.total_points == total_weekly_points
            
            team.save()
            
            yield "{0} ({1:d}/{2:d})".format(team.manager, i+1, length)
    
    def set_league_positions(self, game_week, save=True):
        if game_week == 1:
            for team in self.all():
                team.league_movement = 0
                if save:
                    team.save()
                yield team
        else:
            previous_league = list(self.league(game_week-1))
            for i, team in enumerate(self.league(game_week)):
                team.league_position = i+1
                team.league_movement = previous_league.index(team) - i
                if save:
                    team.save()
                yield team

    def emails(self):
        return list(self.values_list('email', flat=True))


class NormalTeamManager(TeamManager):
    def get_queryset(self):
        return super(NormalTeamManager, self).get_queryset().filter(team_type='N')


class JokeTeamManager(TeamManager):
    def get_queryset(self):
        return super(JokeTeamManager, self).get_queryset().filter(team_type='J')


class SquadManager(models.Manager):
    use_for_related_fields = True
    
    def current_players(self):
        players = self.none()
        for position in Formation.labels:
            players = players | self.filter(player__position=position).filter(
                datetime_out__isnull=True)
        return players
    
    def in_team(self, game_week):
        return self.filter(week_in__lte=game_week).exclude(week_out__lt=game_week)
    
    def subs(self, game_week):
        return self.filter(week_out__lt=game_week).order_by('-week_out')
    
    def substitute(self, players_in, players_out, datetime):
        for player in players_in:
            squadmember = self.create(player=player, datetime_in=datetime)
            squadmember.set_week_in()
            squadmember.save()

        for player in players_out:
            squadmember = self.filter(player=player).latest()
            squadmember.datetime_out = datetime
            squadmember.set_week_out()
            squadmember.save()


class SubManager(models.Manager):
    def get_queryset(self):
        return super(SubManager, self).get_queryset().filter(datetime_out__isnull=False)


class PlayerManager(models.Manager):
    def get_queryset(self):
        return super(PlayerManager, self).get_queryset().filter(datetime_out__isnull=True)


class WeekPointsManager(models.Manager):
    def latest_week(self):
        week = self.aggregate(models.Max('week'))['week__max']
        if week is None:
            return 0
        else:
            return int(week)
        
    def week_best(self, week):
        return self.filter(week=week).select_related().order_by('-points')
    
    def weekly_winners(self, week):
        week_points = self.filter(week=week).select_related().filter(
            team__team_type='N').order_by('-points')
        points = week_points[0].points
        winners = [w.team for w in week_points.filter(points=points)]
        return winners, points
    
    def table(self, from_week, to_week):
        return self.select_related().filter(week__gte=from_week, week__lte=to_week)

    
class Team(models.Model):
    manager = models.CharField(max_length=30, db_index=True)
    team_name = models.CharField(max_length=50)
    email = models.EmailField()
    team_type = models.CharField(max_length=1,
                                 choices=TEAM_TYPE_CHOICES, default='N')
    formation = models.CharField(max_length=5, choices=FORMATION_CHOICES,
                                 default='4-4-2')
    
    players = models.ManyToManyField(Player, through="SquadMember")
    
    total_cost = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    
    subs_used = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    league_position = models.IntegerField(null=True)
    league_movement = models.IntegerField(default=0)
    
    objects = TeamManager()
    normal = NormalTeamManager()
    joke = JokeTeamManager()
    
    class Meta:
        ordering = ['manager']
    
    def set_total_cost(self):
        self.total_cost = sum(p.player.value for p in
                              self.squad.filter(datetime_out__isnull=True))
        self.save()
    
    def set_subs_used(self):
        self.subs_used = self.squad.filter(datetime_out__isnull=False).count()
        self.save()

    def __unicode__(self):
        return self.manager


class SquadMember(models.Model):
    team = models.ForeignKey(Team, related_name="squad")
    player = models.ForeignKey(Player)
    week_in = models.IntegerField(default=1)
    week_out = models.IntegerField(null=True)
    datetime_in = models.DateTimeField(null=True)
    datetime_out = models.DateTimeField(null=True)
    points = models.IntegerField(default=0)
    
    objects = SquadManager()
    players = PlayerManager()
    subs = SubManager()
    
    class Meta:
        ordering = ['player', 'datetime_in']
        get_latest_by = 'datetime_in'
    
    def set_week_in(self):
        if self.datetime_in:
            self.week_in = gameinfo.weekNum(self.datetime_in) + 1
        else:
            self.week_in = 1
        self.save()
    
    def set_week_out(self):
        if self.datetime_out:
            self.week_out = gameinfo.weekNum(self.datetime_out)
        else:
            self.week_out = None
        self.save()
    
    def set_points(self, game_week):
        week_to = game_week

        if self.week_out:
            week_to = min(game_week, self.week_out)
        
        points = self.player.points_sum(self.week_in, week_to)
        
        self.points = points
        self.save()
        return points
    
    def __unicode__(self):
        return "{0}".format(self.player.name)


class WeekPoints(models.Model):
    team = models.ForeignKey(Team, related_name="weekly_points")
    week = models.IntegerField()
    points = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['team']

    objects = WeekPointsManager()
