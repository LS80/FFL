from __future__ import division

from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rc

from FFL.players.models import Player
from FFL.game import telegraph, gameinfo

rc('font', size=8)


def import_players(request):   
    Player.objects.import_players()

    return HttpResponseRedirect(reverse(players_imported))


def players_imported(request):
    return HttpResponse("Players imported successfully.")


def _csv(request, filename='players.csv', sections=False):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=' + filename

    players = telegraph.PlayerList()

    if sections:
        players.csv(response, sections=sections)
    else:
        players.csv(response)

    return response


def players_csv(request):
    return _csv(request)


def goalkeepers_csv(request):
    return _csv(request, 'goalkeepers.csv', ['GK'])

    
def defenders_csv(request):
    return _csv(request, 'defenders.csv', ['DEF'])


def midfielders_csv(request):
    return _csv(request, 'midfielders.csv', ['MID'])


def strikers_csv(request):
    return _csv(request, 'strikers.csv', ['STR'])


def _players(request, position):
    template = position.lower() + 's.html'
    return render(request, template,
                  {'players': Player.objects.position(position),
                   'week': gameinfo.gameWeek()})


def goalkeepers(request):
    return _players(request, "Goalkeeper")


def defenders(request):
    return _players(request, "Defender")


def midfielders(request):
    return _players(request, "Midfielder")


def strikers(request):
    return _players(request, "Striker")


def player(request, code):
    player = Player.objects.code(code)
    return render(request, 'player.html',
                  {'player': player,
                   'playing_for': player.playing_for(),
                   'subbed_by': player.subbed_by(),
                   'week': gameinfo.gameWeek()})


def player_wp(request, code):
    try:
        player = Player.objects.get(code=code)
    except Player.DoesNotExist:
        raise Http404

    points = player.weekly_points.values_list('points', flat=True)
    response = HttpResponse(content_type='image/png')
    
    if points:
        weeks = list(player.weekly_points.values_list('week', flat=True))
        fig = Figure(figsize=(0.4 * min(max(10, weeks[-1]), 22), 3),
                     dpi=100, facecolor='white')
        ax = fig.add_subplot(111)
        rects = ax.bar(weeks, points, align='center', linewidth=1, color='#008ad1', width=1)
        ax.set_xlabel("Week")
        ax.set_ylabel("Points")
        ax.set_xticks(weeks) # add a tick for every week
        for p, rect in zip(points, rects):
            if p != 0:
                if p < 0:
                    h = p * 2 - 1
                elif p > 0:
                    h = p + 1
                ax.text(rect.get_x() + rect.get_width() / 2., h, str(p),
                        fontsize=10, color='black', ha='center')
        ax.set_xlim((0.5, max(10, weeks[-1]) + 0.5))
    else:
        fig = Figure(figsize=(1, 1), dpi=1, facecolor='white') # return one white pixel

    canvas = FigureCanvas(fig)
    canvas.print_png(response)

    return response
