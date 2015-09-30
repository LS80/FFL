# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import platform, sys
import StringIO
import urllib2
from os.path import dirname, join, abspath, basename

import PySide

from PySide.QtCore import (Qt, QSettings, QCoreApplication)
from PySide.QtGui import (QAction, QApplication, QIcon, QLabel, QMainWindow, QMessageBox, QTableWidget,
                          QTableWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QSpinBox,
                          QPushButton, QColor, QBrush, QProgressDialog, QTextEdit, QLineEdit, QCheckBox)

from django.conf import settings as django_settings
    
django_settings.configure(DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                                                   'NAME': 'ffl.db'}
                                       },
                          TEMPLATE_DIRS = (join(dirname(__file__), 'templates').replace('\\','/'),),
                          ROOT_URLCONF = basename(dirname(dirname(__file__))) + '.urls'
                          )
    
path = dirname(dirname(dirname(abspath(__file__))))
if path not in sys.path:
    sys.path.append(path)
    
from django.template.loader import render_to_string
from django.db import transaction

import qrc_resources
import gameinfo

from FFL.teams.models import Team, WeekPoints
from FFL.teams.views import graph_plot_png
from FFL.players.models import Player
from FFL.players.models import WeekPoints as PlayerWeekPoints

from alert import HTMLEmail
import editTeam
from settings import SettingsDialog
import config

__version__ = "0.9.1"
__org__     = "Lee Smith"
__app__     = "Fantasy Football League"
__title__   = "{0} {1}".format(__org__, __app__)
__abbr__    = "".join([word[0].upper() for word in __app__.split()])

class MainWindow(QMainWindow):
    
    TEAM_COLOURS = dict(N=QColor(128,255,128), O=QColor(50,162,237), J=QColor(255,100,100))

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        
        QCoreApplication.setOrganizationName(__org__)
        QCoreApplication.setApplicationName(__app__)

        fileQuitAction = self.createAction("&Quit", self.close,
                "Ctrl+Q", "exit", "Close the application")
        showTeamsAction = self.createAction("&Teams", self.showTeamTable,
                "Ctrl+T", "team", "Show the list of {0} teams".format(__abbr__))
        updateAction = self.createAction("&Update", self.showUpdate,
                "Ctrl+U", "update", "Download latest player points and update the teams")
        emailAction = self.createAction("&Compose Email", self.showEmail,
                "Ctrl+C", "email", "Compose and send the weekly email")
        settingsAction = self.createAction("&Settings", self.settings, "Ctrl+S", "settings", "Change program settings")
        helpAboutAction = self.createAction("&About", self.helpAbout,
                "F1", "about", tip="About the application")

        fileMenu = self.menuBar().addMenu("&File")
        self.addActions(fileMenu, (fileQuitAction,))
        viewMenu = self.menuBar().addMenu("&View")
        self.addActions(viewMenu, (showTeamsAction, updateAction, emailAction))
        helpMenu = self.menuBar().addMenu("&Help")
        self.addActions(helpMenu, (helpAboutAction,))

        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setObjectName("Main Toolbar")

        self.addActions(toolbar, (showTeamsAction, updateAction,
                                  emailAction, None, settingsAction))

        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.showMessage("Ready")

        settings = QSettings()
        
        if settings.contains('Geometry'):
            self.restoreGeometry(settings.value('Geometry'))
            
        if settings.contains('State'):
            self.restoreState(settings.value('State'))
        
        if settings.contains('HTTP Proxy/IP'):
            if settings.value('HTTP Proxy/Enabled'):
                proxy = str(settings.value('HTTP Proxy/IP'))
                self.installProxy(proxy)
                
        if settings.contains('DB/File'):
            db = settings.value('DB/File')
        else:
            db = "{0}.db".format(__abbr__.lower())
            settings.setValue("DB/File", db)

        self.setWindowTitle("{0} {1}".format(__org__, __abbr__))

        self.showTeamTable()
            
    def installProxy(self, ip=None):
        if ip:
            opener = urllib2.build_opener(urllib2.ProxyHandler({'http': ip}))
        else:
            opener = urllib2.build_opener(urllib2.BaseHandler())
        urllib2.install_opener(opener)

    def showTeamTable(self):
        self.teamWidget = QWidget(self)
        self.teamTable = QTableWidget()
        
        mainLayout = QVBoxLayout()
        topOfTableLayout = QHBoxLayout()
        mainLayout.addLayout(topOfTableLayout)
        mainLayout.addWidget(self.teamTable)
        self.teamWidget.setLayout(mainLayout)
        
        COLUMNS = ("Manager", "Team Name", "Formation", "Team Cost", "Subs Remaining", "Points", "League Position")
        
        self.teamTable.setColumnCount(len(COLUMNS))
        self.teamTable.setHorizontalHeaderLabels(COLUMNS)
        
        self.teamSearchBox = QLineEdit()
        self.teamSearchBox.setPlaceholderText("Search for a manager...")
        self.teamSearchBox.setFixedWidth(150)
        topOfTableLayout.addWidget(self.teamSearchBox)
        self.teamSearchBox.returnPressed.connect(self.teamSearch)
                
        self.editTeamButton = QPushButton("&Edit Team")
        self.editTeamButton.setEnabled(False)
        topOfTableLayout.addWidget(self.editTeamButton)
        self.editTeamButton.clicked.connect(self.editTeam)
        
        self.deleteTeamButton = QPushButton("&Delete Team")
        self.deleteTeamButton.setEnabled(False)
        topOfTableLayout.addWidget(self.deleteTeamButton)
        self.deleteTeamButton.clicked.connect(self.deleteTeam)
        
        topOfTableLayout.addStretch()

        self.teamTable.itemClicked.connect(self.teamSelected)
        self.teamTable.itemDoubleClicked.connect(self.editTeam)
        
        self.teamTable.setAlternatingRowColors(True)
        self.teamTable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.teamTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.teamTable.setSelectionMode(QTableWidget.SingleSelection)
        self.teamTable.clearSelection()

        self.setCentralWidget(self.teamWidget)
        
        self.updateTeamTable()
        
    def teamSearch(self):
        items = self.teamTable.findItems(self.teamSearchBox.text(), Qt.MatchContains)
        if items:
            self.teamTable.selectRow(items[0].row())
            self.teamSearchBox.clear()
            self.editTeam()
        
    def teamSelected(self):
        self.editTeamButton.setEnabled(True)
        self.deleteTeamButton.setEnabled(True)        
            
    def editTeam(self):
        team = self.currentTeam()
        if team is not None:
            form = editTeam.editTeamDialog(team, self)
            if form.exec_():
                self.updateTeamTable()

    def deleteTeam(self):
        team = self.currentTeam()
        if team is not None:
            if (QMessageBox.question(self,
                "{0} - Delete Team",
                "Delete team '{1}' managed by {2}?".format(__title__,
                                                           team.team_name, team.manager),
                                     QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes):
                team.delete()
                self.updateTeamTable()
            
    def currentTeam(self):
        row = self.teamTable.currentRow()
        if row > -1:
            item = self.teamTable.item(row, 0)
            return item.data(Qt.UserRole)
        return None

    def updateTeamTable(self):
        self.teamTable.setRowCount(Team.objects.count())
        
        for row, team in enumerate(Team.objects.all()):
            item = QTableWidgetItem(team.manager)
            item.setData(Qt.UserRole, team)
            item.setBackground(QBrush(self.TEAM_COLOURS[team.team_type]))
            
            item.setTextAlignment(Qt.AlignCenter)
            self.teamTable.setItem(row, 0, item)

            for i, data in enumerate([team.team_name,
                                      team.formation,
                                      '{0}'.format(team.total_cost),
                                      '{0}'.format(config.MAX_SUBS - team.subs_used),
                                      '{0}'.format(team.total_points),
                                      '{0}'.format(team.league_position)
                                      ]):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                self.teamTable.setItem(row, i+1, item)

        self.teamTable.resizeColumnsToContents()
        self.teamTable.resizeRowsToContents()

    def showUpdate(self):
        self.updateWidget = QWidget(self)
        self.updateProgressDisplay = QTextEdit()
        
        mainLayout = QVBoxLayout()
        topOfTableLayout = QHBoxLayout()
        
        self.updateWeek = QSpinBox()
        self.updateWeek.setMinimum(1)
        self.updateWeek.setMaximum(gameinfo.gameWeek())
        self.updateWeek.setValue(WeekPoints.objects.latest_week()+1)

        label = QLabel("Update team points up to &week:")
        label.setBuddy(self.updateWeek)
        
        topOfTableLayout.addWidget(label)
        topOfTableLayout.addWidget(self.updateWeek)
        
        self.force_update = QCheckBox("Force points re-update")
        topOfTableLayout.addWidget(self.force_update)
        
        self.updateButton = QPushButton("&Start")
        topOfTableLayout.addWidget(self.updateButton)
        self.updateButton.clicked.connect(self.gameUpdate)
        
        topOfTableLayout.addStretch()
        
        mainLayout.addLayout(topOfTableLayout)
        
        mainLayout.addWidget(self.updateProgressDisplay)
        self.updateWidget.setLayout(mainLayout)
        
        self.setCentralWidget(self.updateWidget)
        
    def gameUpdate(self):
        progress = QProgressDialog('', 'Stop', 1, 1, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumWidth(300)
        progress.setMinimumHeight(130)
        progress.setWindowTitle('Points Update')
        progress.setLabelText('Downloading latest player points...')
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        len_players = Player.objects.count()
        
        Player.objects.add_new_players()
        
        progress.setMaximum(len_players)
        
        week = self.updateWeek.value()

        self.updateProgressDisplay.append('<b>Downloading latest player points...</b>')

        msg = "Player update complete"
        update_teams = True
        
        if PlayerWeekPoints.objects.latest_week() < week or self.force_update.isChecked():
            #with transaction.commit_manually():
                #try:
                    for i, info in enumerate(Player.objects.update()):
                        self.updateProgressDisplay.append(info)
                        progress.setValue(i+1)
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            msg = "Player update incomplete"
                            update_teams = False
                            raise AssertionError
                #except AssertionError:
                #    transaction.rollback()
                #else:
                #    transaction.commit()
        else:
            msg = "Players already up-to-date"
            progress.hide()
            QApplication.processEvents()

        self.updateProgressDisplay.append("<p><span style='font-weight:bold;'>{0}</span></p>".format(msg))

        if update_teams:
            self.updateProgressDisplay.append('<b>Updating team points...</b>')
            
            progress.setLabelText('Updating team points...')
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()
            
            len_teams = Team.objects.count()
            
            progress.setMaximum(len_teams)         
            
            with transaction.commit_manually():
                try:
                    WeekPoints.objects.all().delete()
        
                    for i, info in enumerate(Team.objects.set_points(week)):
                        self.updateProgressDisplay.append(info)
                        progress.setValue(i+1)
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            msg = "Team update incomplete"
                            raise AssertionError
        
                    list(Team.objects.set_league_positions(week))
                except AssertionError:
                    transaction.rollback()
                else:
                    msg = "Team update complete"
                    transaction.commit()
            
            self.updateProgressDisplay.append("<p><span style='font-weight:bold;'>{0}</span></p>".format(msg))
            
    def showEmail(self):
        self.emailWidget = QWidget(self)
        self.emailEdit = QTextEdit()

        mainLayout = QVBoxLayout()
        bottomLayout = QHBoxLayout()
        mainLayout.addWidget(self.emailEdit)
        mainLayout.addLayout(bottomLayout)
        self.emailWidget.setLayout(mainLayout)

        self.sendButton = QPushButton("&Send Email")
        bottomLayout.addWidget(self.sendButton)
        self.sendButton.clicked.connect(self.sendEmail)
        
        bottomLayout.addStretch()
        
        self.setCentralWidget(self.emailWidget)
        
        addresses = Team.objects.emails()

        self.weekly_email = HTMLEmail(addresses, "lee@lee-smith.me.uk", "{0} {1}".format(__org__, __abbr__))

        week = WeekPoints.objects.latest_week()
        week_winners, week_points = WeekPoints.objects.weekly_winners(week)
 
        WEEK_TOP = 6
        LEAGUE_TOP = 6
        
        settings = QSettings()
        if settings.contains('General/Name'):
            name = settings.value('General/Name')
        else:
            name = ""
 
        context = {"week": week,
                   "date": gameinfo.weekToDate(week),
                   "points": week_points,
                   "week_winners": week_winners,
                   "week_top": WeekPoints.objects.week_best(week)[:WEEK_TOP],
                   "league_top": Team.objects.league(week)[:LEAGUE_TOP],
                   "best_players": PlayerWeekPoints.objects.week_best(week),
                   "new_players": Player.objects.new_players(week),
                   "name": name,
                   "stats": Player.stats}

        self.emailEdit.setHtml(render_to_string('email.html', context))

    def sendEmail(self):
        settings = QSettings()
        if settings.contains('SMTP/Server'):
            smtp_server = settings.value('SMTP/Server')
        else:
            smtp_server = None
        
        if not smtp_server:
            QMessageBox.critical(self, "Email Error", "Please add an SMTP server in settings.")
        else:
            latest_week = WeekPoints.objects.latest_week()
            subject = "*** {0} {1} - Week {2} Results ***".format(__org__, __app__, latest_week)
            html = self.emailEdit.toHtml()

            teams = [team.id for team in Team.objects.league(latest_week)[:10]]

            png = graph_plot_png(StringIO.StringIO(), teams, from_week=latest_week-3, to_week=latest_week)
            png.seek(0)
            
            self.weekly_email.sendMail(subject, html, smtp_server, images=[png])
            
            self.sendButton.setEnabled(False)

#            import codecs
#            html = codecs.open('email.html', 'w', 'utf-8-sig')
#            html.write(self.emailEdit.toHtml())
#            html.close()

    def createAction(self, text, slot=None, shortcut=None, icon=None,
                    tip=None, checkable=False, signal="triggered"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/{0}.png".format(icon)))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            getattr(action, signal).connect(slot)
        if checkable:
            action.setCheckable(True)
        return action

    def addActions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
                
    def closeEvent(self, event):
        settings = QSettings()
        settings.setValue("Geometry", self.saveGeometry())
        settings.setValue('State', self.saveState())
        
    def settings(self):
        dialog = SettingsDialog(parent=self)
        if dialog.exec_():
            if dialog.http_proxy.isChecked():
                self.installProxy(dialog.http_proxy_ip.text())
            else:
                self.installProxy(None)

    def helpAbout(self):
        QMessageBox.about(self, "{0} - About",
                          """<b>{0}</b> v {1}
                          <p>The MIT License (MIT) Copyright (c) 2009 Lee Smith
                          <p>This application is used to manage the {0}.
                          <p>Python {2} - Qt {3} - PySide {4} on {5}""".format(__title__,
                                                                               __version__,
                                                                               platform.python_version(),
                                                                               PySide.QtCore.__version__,
                                                                               PySide.__version__, 
                                                                               platform.system()))

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(__org__)
    app.setApplicationName(__title__)
    app.setWindowIcon(QIcon(":/ffl_logo.png"))
    form = MainWindow()
    form.show()
    app.exec_()

main()
