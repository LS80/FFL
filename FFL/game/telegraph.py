from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import re
from decimal import Decimal
from time import sleep
from datetime import datetime, date
import urlparse

import requests
from bs4 import BeautifulSoup


URL_ROOT = "http://fantasyfootball.telegraph.co.uk/premierleague/"

class PlayerList(object):
    POSITIONS = {'GK': "Goalkeeper",
                 'DEF': "Defender",
                 'MID': "Midfielder",
                 'STR': "Striker"}

    SECTIONS = POSITIONS.keys()

    TEAM_SELECT_URL = urlparse.urljoin(URL_ROOT, 'select-team')

    def __init__(self):
        response = requests.get(self.TEAM_SELECT_URL)
        self.soup = BeautifulSoup(response.text, 'lxml')
        
    def __iter__(self):
        return self.players()
        
    def _points(self, player):
        try:
            points = int(player.findAll('td', limit=5)[4].string)
        except TypeError:    
            points = 0
        return points
    
    def _games(self, player):
        return 0 

    def players(self, sections=None):
        today = date.today()
        if sections is None:
            sections = self.SECTIONS

        for abbr in sections:
            section = self.soup.find('div', {'id': 'list-' + abbr})
            if section is None:
                return
            for player in section('tr', {'id': re.compile('p\d{4}')}):
                code = player['id'].lstrip('p')
                if code[0] != '9': # some new players seem to be given a temporary code
                    name, club, value = player('td')[1:4]
                    yield dict(code = int(code),
                               name = name.string,
                               club = club.string,
                               value = Decimal(value.string),
                               position = self.POSITIONS[abbr],
                               games = self._games(player),
                               total_points = self._points(player),
                               is_playing = 'avail' in player['class'],
                               date_added = today)
                
    def games(self, code):
        player = self.soup.find('tr', {'id': 'p' + str(code)})
        return self._games(player)
    
    def points(self, code):
        player = self.soup.find('tr', {'id': 'p' + str(code)})
        return self._points(player)

    def csv(self, f, sections=False):
        if sections is False:
            sections = self.SECTIONS
        writer = csv.writer(f)
        writer.writerow(["Code", "Position", "Name", "Club", "Value",
                         "Games", "Total Points"])
    
        for player in self.players(sections):
            writer.writerow([player['code'], player['position'], player['name'],
                             player['club'], player['value'], player['games'],
                             player['total_points']]) 


class PlayerUpdate(object):
    SLEEP = 10
    NTRYS = 6
    
    PLAYER_URL = urlparse.urljoin(URL_ROOT, 'statistics/points/{0}')
    
    def __init__(self, code):
        trys = 0
        self.soup = None
        while not self.soup and trys < self.NTRYS:
            try:
                response = requests.get(self.PLAYER_URL.format(code))
            except requests.RequestException:
                sleep(self.SLEEP)
                trys += 1
            else:
                self.soup = BeautifulSoup(response.text, 'lxml').find('div', 'l-cont')
    
    def points(self):
        if self.soup is None:
            return

        for game in self.soup.table.tbody('tr'):
            data = [td.string for td in game('td')]
            if data:
                yield int(data[0]), int(data[-1])
            else:
                return
            
    def total_points(self):
        if self.soup is None:
            return 0
        else:
            return int(self.soup.find('p', attrs={'id': 'pla-tot-pts'}).string.split()[-1])
    
    def club(self):
        if self.soup is None:
            return ""
        else:
            return self.soup.find('p', attrs={'id': 'stats-team'}).string
    
    def games(self):
        if self.soup is None:
            return 0
        else:
            return len(self.soup.table.tbody('tr'))


class MatchFacts(object):
    
    class Fixture(object):
        def __init__(self, date, teams):
            self.date = date
            self.teams = teams
            
        def __iter__(self):
            return self.teams
    
    class Team(object):
        def __init__(self, team):
            self.teamname = team.find('div', 'teamname').string
            try:
                self.teamscore = int(team.find('div', 'teamscore').string)
            except ValueError:
                self.teamscore = None
                self.score_events = []
            else:
                self.score_events = [{'type': event['class'][1],
                                      'name': event.string}
                                     for event in team('li', 'score_event')]
    
    MATCH_FACTS_URL = urlparse.urljoin(URL_ROOT, 'match-facts')
    
    def __init__(self):
        response = requests.get(self.MATCH_FACTS_URL)
        self.soup = BeautifulSoup(response.text, 'lxml')
        
    def __iter__(self):
        for fixture in self.soup('div', 'fixture'):
            date_str = fixture.find('div', 'datetime_banner').string.split(' - ')[0]
            date = datetime.strptime(date_str, "%d/%m/%Y")
            teams = (MatchFacts.Team(fixture.find('div', team))
                     for team in ('team1', 'team2'))
            yield MatchFacts.Fixture(date, teams)


if __name__ == "__main__":    
    matches = MatchFacts()
    for match in matches:
        print(match.date.date())
        for team in match:
            print(team.teamname, team.teamscore)
            for event in team.score_events:
                print(event['name'], event['type'])
    
    players = PlayerList()
    
    for player in players:
        print(player)
        updated_info = PlayerUpdate(player['code'])
        print(list(updated_info.points()))
    
    f = open('players.csv', 'wb')
    players.csv(f)
    f.close()
