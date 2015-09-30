from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import urllib2
import sys
from os.path import dirname, abspath

path = dirname(dirname(dirname(abspath(__file__))))
if path not in sys.path:
    sys.path.append(path)
    
from django.conf import settings
settings.configure(DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                                            'NAME': 'ffl.db'}
                                }
                   )

from FFL.teams.models import Team, WeekPoints
from FFL.players.models import Player

def updatePlayers(players):
    Player.objects.add_new_players()
    for progress in Player.objects.update():
        print(progress)

def updateTeams(teams, week=None):
    for i, team in Team.objects.set_points(week):
        print(i, team)

    for i, team in Team.objects.set_league_positions(week):
        print(i, team)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    parser.add_argument("-p", "--players", action="store_true", default=False,
                        help="update the player points before running the team update.")
                    
    parser.add_argument("-w", "--week", type=int, default=None,
                        help="update the points for the specified week.")
    
    parser.add_argument("-s", "--proxy", action="store_true", default=False,
                        help="use the http proxy server.")

    args = parser.parse_args()

    if args.proxy:
        proxy = urllib2.ProxyHandler({'http': '212.118.224.147'})
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
        
    if args.players:
        updatePlayers()
            
    if args.week:
        week = args.week
    else:
        week = WeekPoints.objects.latest_week()+1
        
    updateTeams(week)