import os

from PySide.QtCore import (QSettings)
from PySide.QtGui import (QDialog, QVBoxLayout, QGridLayout, QDialogButtonBox,
                         QLabel, QLineEdit, QFontMetrics, QFont, QGroupBox, QPushButton, QFileDialog)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.setWindowTitle("Settings")
        
        main_layout = QVBoxLayout()
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        
        settings = QSettings()
        
        db_group = QGroupBox("Database")
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("File"),0,0)
        text = settings.value('DB/File')
        self.file = QLineEdit(text)
        self.file.setText(text)
        grid_layout.addWidget(self.file,0,1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        grid_layout.addWidget(browse,0,2)
        db_group.setLayout(grid_layout)
        main_layout.addWidget(db_group)
        
        ip_width = QFontMetrics(QFont(self.font())).width("000.000.000.000  ")
    
        smtp_group = QGroupBox("SMTP")
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Server"),0,0)
        text = settings.value('SMTP/Server')
        self.smtp_server = QLineEdit(text)
        self.smtp_server.setText(text)
        grid_layout.addWidget(self.smtp_server,0,1)
        smtp_group.setLayout(grid_layout)
        main_layout.addWidget(smtp_group)

        self.http_proxy = QGroupBox("HTTP Proxy")
        self.http_proxy.setCheckable(True)
        self.http_proxy.setChecked(bool(settings.value('HTTP Proxy/Enabled')))
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Server"),0,0)
        self.http_proxy_ip = QLineEdit()
        self.http_proxy_ip.setText(settings.value('HTTP Proxy/IP'))
        self.http_proxy_ip.setMinimumWidth(ip_width)
        grid_layout.addWidget(self.http_proxy_ip,0,1)
        grid_layout.setColumnStretch(0,1)
        self.http_proxy.setLayout(grid_layout)
        main_layout.addWidget(self.http_proxy)
        
        main_layout.addWidget(buttonBox)
        self.setLayout(main_layout)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
    def browse(self):
        file, ext = QFileDialog.getOpenFileName(self, "Choose database", os.getcwd(),
                                                "Database (*.db)")
        self.file.setText(file)

    def accept(self):
        settings = QSettings()
        settings.setValue("DB/File", self.file.text())
        settings.setValue("SMTP/Server", self.smtp_server.text())
        settings.setValue("HTTP Proxy/IP", self.http_proxy_ip.text())
        settings.setValue("HTTP Proxy/Enabled", bool(self.http_proxy.isChecked()) and bool(self.http_proxy_ip.text()))
        QDialog.accept(self)