# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_session.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_SessionDialog(object):
    def setupUi(self, SessionDialog):
        if not SessionDialog.objectName():
            SessionDialog.setObjectName(u"SessionDialog")
        SessionDialog.resize(720, 460)
        SessionDialog.setMinimumSize(QSize(560, 340))
        icon = QIcon()
        icon.addFile(u":/icons/preferences.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SessionDialog.setWindowIcon(icon)
        SessionDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.verticalLayout = QVBoxLayout(SessionDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelSummary = QLabel(SessionDialog)
        self.labelSummary.setObjectName(u"labelSummary")
        self.labelSummary.setStyleSheet(u"font-size: 10pt; padding: 4px;")
        self.labelSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelSummary)

        self.tableRequests = QTableWidget(SessionDialog)
        self.tableRequests.setObjectName(u"tableRequests")
        self.tableRequests.setStyleSheet(u"QTableWidget {\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    background-color: #f9f9f9;\n"
"    border: 1px solid #d3d3d3;\n"
"    border-radius: 3px;\n"
"    gridline-color: #e6e6e6;\n"
"}\n"
"QHeaderView::section {\n"
"    background-color: #f0f0f0;\n"
"    border: none;\n"
"    border-bottom: 1px solid #d3d3d3;\n"
"    padding: 4px;\n"
"}")
        self.tableRequests.setAlternatingRowColors(True)
        self.tableRequests.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableRequests.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableRequests)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButtonSave = QPushButton(SessionDialog)
        self.pushButtonSave.setObjectName(u"pushButtonSave")
        self.pushButtonSave.setStyleSheet(u"QPushButton {\n"
"    background-color: #f0f0f0;\n"
"    color: #333333;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #e6e6e6;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #d9d9d9;\n"
"}")

        self.horizontalLayout.addWidget(self.pushButtonSave)

        self.pushButtonReplay = QPushButton(SessionDialog)
        self.pushButtonReplay.setObjectName(u"pushButtonReplay")
        self.pushButtonReplay.setStyleSheet(u"QPushButton {\n"
"    background-color: #f0f0f0;\n"
"    color: #333333;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #e6e6e6;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #d9d9d9;\n"
"}")

        self.horizontalLayout.addWidget(self.pushButtonReplay)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButtonClose = QPushButton(SessionDialog)
        self.pushButtonClose.setObjectName(u"pushButtonClose")
        self.pushButtonClose.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.horizontalLayout.addWidget(self.pushButtonClose)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(SessionDialog)

        QMetaObject.connectSlotsByName(SessionDialog)
    # setupUi

    def retranslateUi(self, SessionDialog):
        SessionDialog.setWindowTitle(QCoreApplication.translate("SessionDialog", u"Session", None))
        self.labelSummary.setText(QCoreApplication.translate("SessionDialog", u"lblSummary", None))
#if QT_CONFIG(tooltip)
        self.pushButtonSave.setToolTip(QCoreApplication.translate("SessionDialog", u"Write this session to a file, so it can be replayed later or attached to a bug report", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonSave.setText(QCoreApplication.translate("SessionDialog", u"Save session...", None))
#if QT_CONFIG(tooltip)
        self.pushButtonReplay.setToolTip(QCoreApplication.translate("SessionDialog", u"Read a saved session and run it against the project that is open now. Each step names the object it ran on, and one this project does not have is reported rather than skipped.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonReplay.setText(QCoreApplication.translate("SessionDialog", u"Replay a session...", None))
        self.pushButtonClose.setText(QCoreApplication.translate("SessionDialog", u"Close", None))
    # retranslateUi

