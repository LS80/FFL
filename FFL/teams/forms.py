import re
from decimal import Decimal

from django.forms import (ModelForm, Form, SelectMultiple, HiddenInput, RadioSelect,
                          ModelMultipleChoiceField, IntegerField, ValidationError)

from models import Team, WeekPoints
from FFL.players.models import Player
from FFL.game.formation import Formation
from FFL.game import config


class SelectTeamForm(ModelForm):
    goalkeeper = ModelMultipleChoiceField(
        queryset=Player.objects.position("Goalkeeper"),
        widget=SelectMultiple(attrs={'title':"Select a Goalkeeper"}))
    
    defenders = ModelMultipleChoiceField(
        queryset=Player.objects.position("Defender"),
        widget=SelectMultiple(attrs={'title':"Select a Defender"}))
    
    midfielders = ModelMultipleChoiceField(
        queryset=Player.objects.position("Midfielder"),
        widget=SelectMultiple(attrs={'title':"Select a Midfielder"}))
    
    strikers = ModelMultipleChoiceField(
        queryset=Player.objects.position("Striker"),
        widget=SelectMultiple(attrs={'title':"Select a Striker"}))  
        
    class Meta:
        model = Team

        fields = ('manager', 'team_name', 'email',
                  'team_type', 'formation', 'total_cost')

        widgets = {'total_cost': HiddenInput(),
                   'team_type': RadioSelect(),
                   'formation': RadioSelect()}
        
    def clean_manager(self):
        manager = self.cleaned_data['manager'].strip()
        if Team.objects.filter(manager__iexact=manager):
            raise ValidationError("This manager already has a team.")
        elif re.search('[^A-Za-z ]', manager):
            raise ValidationError("Please use only letters and ",
                                  "spaces for the manager name")
        return manager
    
    def clean_email(self):
        return self.cleaned_data['email'].lower()
  
    def check_section(self, section):
        players = self.cleaned_data[section]
        formation = Formation(self.cleaned_data['formation'])
        if len(players) != formation[section]:
            raise ValidationError("Select {0} from this section"
                                  .format(formation[section]))
        return players
    
    def clean_goalkeeper(self):
        return self.check_section('goalkeeper')
    
    def clean_defenders(self):
        return self.check_section('defenders')
    
    def clean_midfielders(self):
        return self.check_section('midfielders')
    
    def clean_strikers(self):
        return self.check_section('strikers')
        
    def clean(self):
        cleaned = self.cleaned_data

        # if all the fields are valid check the total cost
        if all(k in cleaned for k in Formation.fields):
            
            total_cost = sum(player.value for field in Formation.fields
                             for player in cleaned[field])
            
            if total_cost > config.MAX_COST:
                raise ValidationError("The total cost must not exceed {0}"
                                      .format(config.MAX_COST))
            else:
                cleaned['total_cost'] = total_cost

        return cleaned


class GraphForm(Form):
    team = ModelMultipleChoiceField(
        queryset=Team.objects.all(), label="",
        error_messages={'invalid_pk_value': "%s is not a valid team id",
                        'invalid_choice': "%s is not a valid team id"})

    from_week = IntegerField(min_value=1,
                             max_value=WeekPoints.objects.latest_week(),
                             required=False)

    to_week = IntegerField(min_value=1,
                           max_value=WeekPoints.objects.latest_week(),
                           required=False)

    def clean(self):
        cleaned = self.cleaned_data
        print(cleaned.values())
        if 'to_week' in cleaned and 'from_week' in cleaned:
            if cleaned['to_week'] < cleaned['from_week']:
                raise ValidationError("'To week' must not be less than 'From week'")

        return cleaned
