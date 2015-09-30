from datetime import timedelta

from django.shortcuts import render

from game import config
from game.gameinfo import startDate

def home(request):
    return render(request, 'home.html',
                  {'MAX_COST': config.MAX_COST,
                   'MAX_SUBS': config.MAX_SUBS,
                   'DEADLINE': startDate + timedelta(days=3),
                   'START_DAY': startDate})
