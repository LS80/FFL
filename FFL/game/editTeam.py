from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
from functools import partial

from django.template.loader import render_to_string

from PySide.QtCore import (Qt, QDateTime, QTime, QSettings)
from PySide.QtGui import (QDialog, QMessageBox, QLabel, 
                          QGridLayout, QVBoxLayout, QHBoxLayout, QDialogButtonBox,
                          QCheckBox, QSpacerItem, QSizePolicy, QDateTimeEdit,
                          QStandardItemModel)

from ui_editTeam import Ui_editTeamDialog
from formation import Formation
import gameinfo
import config
from alert import HTMLEmail

from FFL.players.models import Player

class editTeamDialog(QDialog, Ui_editTeamDialog):

    def __init__(self, team, parent=None):
        super(editTeamDialog, self).__init__(parent)
        
        self.team = team
        
        self.setupUi(self)
        
        self.setWindowTitle("Edit Team")
        
        managerNameLabel = QLabel()
        managerNameLabel.setText("<b>{0}</b>".format(team.manager))
        self.teamUserInfoLayout.addWidget(managerNameLabel, 0, 1)
        
        self.teamNameEdit.setText(team.team_name)
        
        if team.email: self.emailEdit.setText(team.email)

        self.type = team.team_type
        
        self.formation = Formation(team.formation)
        self.formationRadioButtons[str(team.formation)].setChecked(True)
        
        self.total_cost = 0
        
        self.team_players = [s.player for s in self.team.squad.current_players()]
                
        self.setupSelections()

        self.setCurrentPlayers()
        
    def setupSelections(self):
        for i, selection in enumerate(self.selections):
            model = PlayerItemModel()
            selection.setModel(model)
            position = self.formation[i]
            selection.clear()
            selection.addItem("")

            for player in Player.objects.position(position):
                selection.addItem("{0} - {1}".format(player.code, player.name), player)
                
            self.positionLabels[i].setText(position)
            selection.currentIndexChanged[int].connect(partial(self.playerSelected, i))
            
    def setCurrentPlayers(self, players=None):
        if players is None:
            players = self.team_players
        for selection, player in zip(self.selections, players):
            selection.setCurrentIndex(selection.findData(player))

    def playerSearch(self, playerNum):
        text = self.searchBoxes[playerNum].text()
        index = self.selections[playerNum].findText(text)
        if index > -1:
            self.selections[playerNum].setCurrentIndex(index)
            self.searchBoxes[playerNum].clear()

    def playerSelected(self, playerNum, index):
        if index > 0:
            player = self.selections[playerNum].itemData(index)
            self.clubLabels[playerNum].setText(player.club)
            self.valueLabels[playerNum].setText(str(player.value))
        else:
            self.clubLabels[playerNum].clear()
            self.valueLabels[playerNum].clear()
            
        self.total_cost = sum([selection.itemData(selection.currentIndex()).value
                               for selection in self.selections if selection.currentIndex() > 0])

        if self.total_cost > config.MAX_COST:
            color = "red"
        else:
            color = "black"
        self.totalCostLabel.setText("<font color={0}>Total Cost {1}</font>".format(color, self.total_cost))

    def formationChanged(self, formation):
        if formation != str(self.formation):
            newFormation = Formation(formation)
            form = changeFormationDialog(self.playerSelections(), self.formation, newFormation, self)
            if form.exec_():
                newPlayers = []
                j=0
                oldPlayers = self.playerSelections()
                for p,q in zip(self.formation.list(),newFormation-self.formation):
                    players=[]
                    for i in range(p):
                        player = oldPlayers.pop(0)
                        if player not in form.playersOut:
                            players.append(player)
                    if q>0:
                        for i in range(q):
                            players.append(None)
                    newPlayers.extend(players)

                self.formation = newFormation
                self.setupSelections()
                self.setCurrentPlayers(newPlayers)
            else:
                self.formationRadioButtons[str(self.formation)].setChecked(True)
            
    def playerSelections(self):
        return [selection.itemData(selection.currentIndex())
                for selection in self.selections if selection.currentIndex() > 0]
            
    def accept(self):
        players = self.playerSelections()
        self.team.team_name = self.teamNameEdit.text()
        self.team.email = unicode(self.emailEdit.text()).lower()

        if self.validTeam(players):
            playersOut = [player for player in self.team_players if player not in players]
            subs_made = len(playersOut)
            if subs_made > 0:
                if self.team.subs_used + subs_made > config.MAX_SUBS:
                    QMessageBox.critical(self, "Substitution Error",
                                         "This manager has insufficient substitutions remaining")
                    self.setCurrentPlayers()
                else:
                    playersIn = [player for player in players if player not in self.team_players]
                    form = confirmSubsDialog(playersOut, playersIn, self)
                    if form.exec_():
                        self.team.subs_used += subs_made
                        self.team.total_cost = self.total_cost
                        self.team.formation = self.formation
                        self.team.squad.substitute(playersIn, playersOut, form.datetime)
                        self.confirmSubs(playersIn, playersOut, form.datetime)
                        QDialog.accept(self)
                    else:
                        self.setCurrentPlayers()
            else:
                QDialog.accept(self)

        self.team.save()
        
    def confirmSubs(self, playersIn, playersOut, datetime):
        week = gameinfo.weekNum(datetime) + 1
        date = gameinfo.weekToDate(week).date()

        html = render_to_string('subs_email.html', {'team': self.team,
                                                    'players_in': playersIn,
                                                    'players_out': playersOut,
                                                    'week': week,
                                                    'date': date}
                                )

        settings = QSettings()
        if settings.contains('SMTP/Server'):
            smtp_server = settings.value('SMTP/Server')
        else:
            smtp_server = None
        
        if not smtp_server:
            QMessageBox.critical(self, "Email Error", "Please add an SMTP server in settings.")
        else:
            email = HTMLEmail([self.team.email],
                              "lee@lee-smith.me.uk",
                              "Fantasy Football League",
                              bcc='lee@lee-smith.me.uk')
            email.sendMail("Sub Confirmation", html, smtp_server)
       
    def validTeam(self, players):
        valid = True
        if players is not None and not len(set(players)) == 11:
            QMessageBox.critical(self, "Player Input Error",
                                 "There are not 11 unique players in the team.")
            valid = False
        if self.total_cost > config.MAX_COST:
            QMessageBox.critical(
                self, "Team Cost Error",
                "The team must not cost more than {0} in total.".format(config.MAX_COST))
            valid = False
        return valid

class confirmSubsDialog(QDialog):

    def __init__(self, playersOut, playersIn, parent=None):
        super(confirmSubsDialog, self).__init__(parent)
        
        self.now = QDateTime.currentDateTime()
        self.now.setTime(QTime(self.now.time().hour(), self.now.time().minute()))
        
        self.setWindowTitle("Confirm Subs")
        mainVerticalLayout = QVBoxLayout(self)
        
        subsLayout = QGridLayout()
        mainVerticalLayout.addLayout(subsLayout)
        
        subsLayout.addWidget(QLabel("<b>Players Out</b>"), 0, 0)
        subsLayout.addWidget(QLabel("<b>Players In</b>"), 0, 1)

        for i, (playerOut, playerIn) in enumerate(zip(playersOut, playersIn)):
            playerOutLabel = QLabel()
            playerOutLabel.setText("<font color=red>{0}</font>".format(playerOut.name))
            subsLayout.addWidget(playerOutLabel, i+1, 0)
            
            playerInLabel = QLabel()
            playerInLabel.setText("<font color=green>{0}</font>".format(playerIn.name))
            subsLayout.addWidget(playerInLabel, i+1, 1)
            
        mainVerticalLayout.addItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        dateTimeLayout = QHBoxLayout()
        mainVerticalLayout.addLayout(dateTimeLayout)
        dateTimeLayout.addWidget(QLabel("Date and time"))
        
        self.dateTimeEdit = QDateTimeEdit(self.now)
        self.dateTimeEdit.setMaximumDateTime(self.now)
        self.dateTimeEdit.setCalendarPopup(True)
        self.dateTimeEdit.setDisplayFormat("d MMM yy h:mm AP")
        
        dateTimeLayout.addWidget(self.dateTimeEdit)
        dateTimeLayout.addStretch()
        
        mainVerticalLayout.addItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        buttonBox.button(QDialogButtonBox.Ok).setText("&Accept")
        mainVerticalLayout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def accept(self):
        self.datetime = self.dateTimeEdit.dateTime().toPython()
        QDialog.accept(self)
 
class changeFormationDialog(QDialog):

    def __init__(self, players, oldFormation, newFormation, parent=None):
        super(changeFormationDialog, self).__init__(parent)

        self.players = players
        self.formationChanges = oldFormation-newFormation
        
        self.setWindowTitle("Change Formation")
        
        mainVerticalLayout = QVBoxLayout(self)
        
        self.allCheckBoxes = []
        for i,p in enumerate(self.formationChanges):
            checkBoxes = {}
            if p > 0:
                outLabel = QLabel()
                text = "<b>Choose {0} {1}"
                if p > 1:    
                    text+="s"
                text += " to drop</b>"
                position = Formation.labels[i]
                outLabel.setText(text.format(p, position.lower()))
                mainVerticalLayout.addWidget(outLabel)
                #subsLayout.addWidget(outLabel, 0, 0)
                for player in [player for player in players if player.position == position]:
                    checkBox = QCheckBox("{0} {1}".format(str(player), player.value))
                    checkBoxes[player] = checkBox
                    mainVerticalLayout.addWidget(checkBox)
            self.allCheckBoxes.append(checkBoxes)

        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        buttonBox.button(QDialogButtonBox.Ok).setText("&Accept")
        mainVerticalLayout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def accept(self):
        error = False
        self.playersOut = []
        for i,p in enumerate(self.formationChanges):
            if p > 0:
                checked = [(player,checkBox) for (player,checkBox)
                           in self.allCheckBoxes[i].items() if checkBox.isChecked()]
                if len(checked) != p:
                    error = True
                    message = "Choose {0} {1}".format(p, Formation.labels[i])
                    if p > 1:
                        message+"s"
                    QMessageBox.critical(self, "Error", message)
                else:
                    self.playersOut.extend([player for (player,checkBox) in checked])
                    
        if not error:
            QDialog.accept(self)
            
class PlayerItemModel(QStandardItemModel):
    """ This Model is used by the team edit QComboBox so that findData will compare the
    codes of the players instead of the id of the player object """
    def match(self, start, role, value, hits, flags):
        for row in range(start.row(), self.rowCount()):
            index = self.createIndex(row, 0, start.internalId())
            data = self.data(index, role)
            if data is not None and value is not None:
                if role == Qt.DisplayRole:
                    if re.search(value, data, re.IGNORECASE):
                        return [index]
                elif role == Qt.UserRole:
                    if data.code == value.code:
                        return [index]
        return []
