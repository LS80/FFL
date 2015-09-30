# -*- coding: utf-8 -*-
from functools import partial

from PySide.QtCore import QSize
from PySide.QtGui import (QBoxLayout, QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox,
                          QComboBox, QRadioButton, QPushButton, QLabel, QLineEdit,
                          QSizePolicy, QSpacerItem)

from formation import Formation

class RadioButtonGroup(QGroupBox):
    def __init__(self, title, labels):
        QGroupBox.__init__(self, title)
        self.layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.buttons = {}
        for label in labels:
            button = QRadioButton(label)
            self.buttons[label] = button
            self.layout.addWidget(button)
        self.setLayout(self.layout)

    def __getitem__(self, label):
        return self.buttons[str(label)]
            
    def __iter__(self):
        return self.buttons.itervalues()
        
    def setVertical(self):
        self.layout.setDirection(QBoxLayout.TopToBottom)
    
    def setHorizontal(self):
        self.layout.setDirection(QBoxLayout.LeftToRight)
            
    def checkedText(self):
        for button in self:
            if button.isChecked():
                return button.text()
    
class Ui_editTeamDialog(object):
    def setupUi(self, editTeamDialog):
    
        editTeamDialog.setObjectName("editTeamDialog")
        editTeamDialog.setMinimumSize(QSize(500, 550))
        editTeamDialog.setMaximumSize(QSize(500, 550))
        
        self.mainVerticalLayout = QVBoxLayout(editTeamDialog)
        self.topLayout = QHBoxLayout()
        self.teamUserInfoLayout = QGridLayout()

        managerLabel = QLabel()
        self.teamUserInfoLayout.addWidget(managerLabel, 0, 0)

        teamLabel = QLabel()
        self.teamUserInfoLayout.addWidget(teamLabel, 1, 0)
        self.teamNameEdit = QLineEdit()
        self.teamNameEdit.setMinimumWidth(200)
        self.teamUserInfoLayout.addWidget(self.teamNameEdit, 1, 1)

        emailLabel = QLabel()
        self.teamUserInfoLayout.addWidget(emailLabel, 2, 0)
        self.emailEdit = QLineEdit()
        self.teamUserInfoLayout.addWidget(self.emailEdit, 2, 1)

        self.topLayout.addLayout(self.teamUserInfoLayout)
        self.topLayout.addStretch()

        self.mainVerticalLayout.addLayout(self.topLayout)
        self.mainVerticalLayout.addItem(QSpacerItem(0, 15))
        
        #self.mainVerticalLayout.addStretch()

        self.formationLayout = QHBoxLayout()

        self.formationRadioButtons = RadioButtonGroup("Formation", Formation.formations)
        self.formationRadioButtons.setFlat(True)
        self.formationLayout.addWidget(self.formationRadioButtons)
        self.formationLayout.addStretch()

        self.mainVerticalLayout.addLayout(self.formationLayout)
        
        self.playersGroupBox = QGroupBox()

        self.gridLayout = QGridLayout(self.playersGroupBox)

        self.goalkeeperLabel = QLabel(self.playersGroupBox)
        self.gridLayout.addWidget(self.goalkeeperLabel, 0, 0)

        self.positionLabels = [QLabel(self.playersGroupBox) for i in range(11)]
        self.searchBoxes = [QLineEdit(self.playersGroupBox) for i in range(11)]
        self.selections = [QComboBox(self.playersGroupBox) for i in range(11)]
        self.clubLabels = [QLabel(self.playersGroupBox) for i in range(11)]
        self.valueLabels = [QLabel(self.playersGroupBox) for i in range(11)]
        
        for i, positionLabel in enumerate(self.positionLabels):
            self.gridLayout.addWidget(positionLabel, i, 0)
        
        for i, searchBox in enumerate(self.searchBoxes):
            searchBox.setToolTip("Search for a player by code or name")
            self.gridLayout.addWidget(searchBox, i, 1)
            searchBox.returnPressed.connect(partial(self.playerSearch, i))
        
        for i, selection in enumerate(self.selections):
            selection.setToolTip("Select a player")
            selection.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
            selection.setCurrentIndex(-1)
            self.gridLayout.addWidget(selection, i, 2)
        
        clubWidth = self.clubLabels[0].fontMetrics().width("Wolverhampton Wanderers")
        for i, clubLabel in enumerate(self.clubLabels):
            clubLabel.setFixedWidth(clubWidth)
            self.gridLayout.addWidget(clubLabel, i, 3)
            
        valueWidth = self.valueLabels[0].fontMetrics().width("0.0")
        for i, valueLabel in enumerate(self.valueLabels):
            valueLabel.setFixedWidth(valueWidth)
            self.gridLayout.addWidget(valueLabel, i, 4)

        
        self.mainVerticalLayout.addWidget(self.playersGroupBox)
        self.mainVerticalLayout.addItem(QSpacerItem(0, 15))
        
        self.totalCostLayout = QHBoxLayout()
        self.totalCostLabel = QLabel()
        self.totalCostLayout.addWidget(self.totalCostLabel)

        self.mainVerticalLayout.addLayout(self.totalCostLayout)
        self.mainVerticalLayout.addItem(QSpacerItem(0, 15))
        
        self.buttonLayout = QHBoxLayout()
        
        okButton = QPushButton("OK")
        okButton.setAutoDefault(False)
        cancelButton = QPushButton("Cancel")
        cancelButton.setAutoDefault(False)
        self.buttonLayout.addWidget(okButton)
        self.buttonLayout.addWidget(cancelButton)
        buttonSpacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.buttonLayout.addItem(buttonSpacer)
        self.mainVerticalLayout.addLayout(self.buttonLayout)

        okButton.clicked.connect(editTeamDialog.accept)
        cancelButton.clicked.connect(editTeamDialog.reject)

        managerLabel.setText("Manager")
        teamLabel.setText("Team Name")
        emailLabel.setText("Email")

        self.playersGroupBox.setTitle("Players")

        for formationRadioButton in self.formationRadioButtons:
            formationRadioButton.clicked.connect(partial(self.formationChanged, str(formationRadioButton.text())))
        
        self.totalCostLabel.setText("Total Cost")
