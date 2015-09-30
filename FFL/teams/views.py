from datetime import timedelta

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Sum
from django.core.urlresolvers import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from numpy import array, reshape, mean, cumsum

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rc

from FFL.teams.models import Team, SquadMember, WeekPoints
from FFL.teams.forms import GraphForm, SelectTeamForm
from FFL.game.formation import Formation
from FFL.game import config
from FFL.game import gameinfo

rc('font', size=8)
rc('legend', fontsize=8)


def week_from(week=None):
    if week:
        return max(1, int(week))
    else:
        return 1

   
def week_to(week=None): 
    latest = WeekPoints.objects.latest_week()
    if week:
        return min(latest, int(week))
    else:
        return latest


def league(request):
    return render(request, 'league.html',
                  {'week': gameinfo.gameWeek(),
                   'teams': Team.objects.order_by('-total_points','id')})


def joke_league(request):
    week = WeekPoints.objects.latest_week()
    teams = list(Team.joke.set_league_positions(week, save=False))  
    
    return render(request, 'league.html',
                  {'type': "Joke ", 'week': week, 'teams': teams})


def weekly_performance(request, from_week=None, to_week=None):
    week = gameinfo.gameWeek()
    
    if week:
        MAX_WEEKS = 20
    
        to_week = week_to(to_week)
        from_week = max(week_from(from_week), (to_week - MAX_WEEKS + 1))
    
        if from_week <= to_week:
            
            nweeks = to_week - from_week + 1
            weeknums = range(from_week, to_week + 1)
            table = WeekPoints.objects.table(from_week, to_week)

            return render(request, 'weeklyperformance.html',
                          {'ncols': nweeks + 1, 'weeknums': weeknums, 'points': table,
                           'prev': from_week != 1,
                           'next': to_week != WeekPoints.objects.latest_week()})
        else:
            raise Http404()
    else:
        return render(request, 'weeklyperformance.html', {'week': week})


def team(request, manager, week=None):
    manager = manager.replace('-', ' ')
    try:
        team = Team.objects.get(manager__iexact=manager)
    except Team.DoesNotExist:
        raise Http404()
    
    latest_week = WeekPoints.objects.latest_week()
    
    if week is None:
        week = latest_week
    else:
        week = int(week)
        if not 1 <= week <= latest_week + 1:
            raise Http404()
    
    league = list(Team.objects.all())

    index = league.index(team)
    n = len(league)
    team_links = (league[(index - 1) % n], league[(index + 1) % n])
    
    week_links = (week > 1, week < latest_week + 1)

    players = team.squad.in_team(week)
    subs = team.squad.subs(week)
    
    for p in players:
        p.week_points = p.player.points(week)
        
    date_from = gameinfo.weekToDate(week)
    date_to = date_from + timedelta(days=6)
    
    return render(request, 'team.html',
                  {'team': team, 'players': players, 'subs': subs, 'latest_week': latest_week,
                   'week': week, 'date_from': date_from, 'date_to': date_to,
                   'week_links': week_links, 'team_links': team_links})


def team_wp(request, manager):    
    manager = manager.replace('-', ' ')
    try:
        team = Team.objects.get(manager__iexact=manager)
    except Team.DoesNotExist:
        raise Http404()
    
    week = WeekPoints.objects.latest_week()
    
    points = team.weekly_points.values_list('points', flat=True)
    weeks = range(1, week + 1)
    
    teams = list(WeekPoints.objects.values_list('points', flat=True))
    shape = (Team.objects.count(), week)
    avgs = mean(reshape(array(teams), shape), axis=0)
    
    fig = Figure(figsize=(7, 3), dpi=100, facecolor='white')
    ax = fig.add_subplot(111)
    rects = ax.bar(weeks, points, align='center', linewidth=1, color='#008ad1', width=1)
    ax.set_xlabel("Week")
    ax.set_ylabel("Points")
    ax.set_xticks(weeks) # add a tick for every week
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2., height / 2., str(height),
                fontsize=10, color="#ffffff", ha='center')
    ax.set_xlim((0.5, max(10, week) + 0.5))
    ax.plot(weeks, avgs, color='blue', marker='*', label='Week average score')
    ax.legend(markerscale=0, handlelength=3)

    canvas = FigureCanvas(fig)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response


def graph(request, teams=None, from_week=None, to_week=None):
    week = gameinfo.gameWeek()
    
    if week:
        if request.GET:
            # form has been submitted - redirect to the full url.
            form = GraphForm(request.GET)
            if form.is_valid():
                teams = '-'.join([str(team.id) for team in form.cleaned_data['team']])
                from_week = week_from(form.cleaned_data['from_week'])
                to_week = week_to(form.cleaned_data['to_week'])

                return HttpResponseRedirect(reverse(graph,
                                                    args=[teams, from_week, to_week]))
        else:
            if teams is None:
                # we are at the basic url so render an empty form.
                form = GraphForm()
            else:
                # we are at the full url - add the values into the form and render the page.
                try:
                    ids = map(int, teams.split('-'))
                except ValueError:
                    raise Http404()
                
                for team_id in ids:
                    if not Team.objects.filter(id=team_id):
                        raise Http404()
                
                from_week = week_from(from_week)
                to_week = week_to(to_week)
                
                form = GraphForm(initial={'team': Team.objects.filter(id__in=ids),
                                          'from_week': from_week,
                                          'to_week': to_week})

        return render(request, 'graph.html',
                      {'form': form, 'teams': teams,
                       'from_week': from_week,
                       'to_week': to_week})
    else:
        # the game has yet to start so there is nothing to graph.
        return render('graph.html', {'week': week})


def graph_plot_png(f, teams, from_week=None, to_week=None):
    to_week = week_to(to_week)
    from_week = week_from(from_week)

    weeks = range(from_week, to_week + 1)
        
    fig = Figure(figsize=(8, 4), dpi=100, facecolor='white')
    ax = fig.add_subplot(111)

    for team_id in teams:
        team = Team.objects.get(id=team_id)
        points = team.weekly_points.filter(week__in=weeks)
        if not points:
            raise Http404()
        
        if from_week > 1:
            prev_points = (team.weekly_points.filter(week__lt=from_week)
                           .aggregate(Sum('points'))['points__sum'])
        else:
            prev_points = 0

        cum_points = cumsum(points.values_list('points', flat=True)) + prev_points
        
        ax.plot(weeks, cum_points, linewidth=1,
                label="{0} ({1})".format(team.manager, team.total_points))

    ax.legend(bbox_to_anchor=(1.02, 1), markerscale=0, handlelength=3, loc='upper left')
    ax.set_xlabel("Week")
    ax.set_ylabel("Points")
    ax.set_xticks(weeks) # add a tick for every week
    ax.set_xlim(from_week, to_week)
    
    fig.subplots_adjust(left=0.06, right=0.70, top=0.95, bottom=0.08)
      
    canvas = FigureCanvas(fig)
    canvas.print_png(f)
    return f


def graph_plot(request, teams, from_week, to_week):
    response = HttpResponse(content_type='image/png')
    return graph_plot_png(response, map(int, teams.split('-')), from_week, to_week)


def formations_pie(request):    
    fig = Figure(figsize=(6, 6), dpi=100, facecolor='white')
    ax = fig.add_subplot(111)

    formations = list(Team.objects.values_list('formation', flat=True))
    counts = [formations.count(f) for f in Formation.formations]
    ax.pie(counts, labels=Formation.formations, autopct='%1.1f%%')
      
    canvas = FigureCanvas(fig)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response


def team_submitted(request):
    return render(request, 'team_submitted.html')


def submit_team(request):
    if request.method == 'POST':
        form = SelectTeamForm(request.POST)
        if form.is_valid():
            team = form.save()

            for field in Formation.fields:
                for player in form.cleaned_data[field]:
                    SquadMember.objects.create(team=team,
                                               player=player,
                                               week_in=gameinfo.gameWeek() + 1)
   
            week = WeekPoints.objects.latest_week()
            if week is not None:
                for w in range(1, week + 1):
                    WeekPoints.objects.create(team=team, week=w)

            html = render_to_string('team_email.html', {'team': team})

            email = EmailMessage('Your Team', html, 'lee@lee-smith.me.uk',
                                 to=[team.email],
                                 bcc=['lee@lee-smith.me.uk'],
                                 headers={'Reply-To': 'lee@lee-smith.me.uk',
                                          'From': 'Fantasy Football'})
            email.content_subtype = 'html'
            email.send()
            
            return HttpResponseRedirect(reverse(team_submitted))
    else:        
        form = SelectTeamForm()
    
    return render(request, 'submit_team.html',
                  {'form': form,
                   'budget': config.MAX_COST,
                   'week': gameinfo.gameWeek() + 1})
