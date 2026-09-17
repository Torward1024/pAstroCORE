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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_SessionDialog(object):
    def setupUi(self, SessionDialog):
        if not SessionDialog.objectName():
            SessionDialog.setObjectName(u"SessionDialog")
        SessionDialog.resize(760, 480)
        SessionDialog.setMinimumSize(QSize(560, 340))
        icon = QIcon()
        icon.addFile(u":/icons/session.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SessionDialog.setWindowIcon(icon)
        self.verticalLayout = QVBoxLayout(SessionDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelSummary = QLabel(SessionDialog)
        self.labelSummary.setObjectName(u"labelSummary")
        self.labelSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelSummary)

        self.checkBoxChangesOnly = QCheckBox(SessionDialog)
        self.checkBoxChangesOnly.setObjectName(u"checkBoxChangesOnly")

        self.verticalLayout.addWidget(self.checkBoxChangesOnly)

        self.tableRequests = QTableWidget(SessionDialog)
        self.tableRequests.setObjectName(u"tableRequests")
        self.tableRequests.setAlternatingRowColors(True)
        self.tableRequests.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tableRequests.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableRequests.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableRequests)

        self.editLayout = QHBoxLayout()
        self.editLayout.setObjectName(u"editLayout")
        self.pushButtonRemove = QPushButton(SessionDialog)
        self.pushButtonRemove.setObjectName(u"pushButtonRemove")
        self.pushButtonRemove.setAutoDefault(False)

        self.editLayout.addWidget(self.pushButtonRemove)

        self.pushButtonRestore = QPushButton(SessionDialog)
        self.pushButtonRestore.setObjectName(u"pushButtonRestore")
        self.pushButtonRestore.setAutoDefault(False)

        self.editLayout.addWidget(self.pushButtonRestore)

        self.editSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.editLayout.addItem(self.editSpacer)


        self.verticalLayout.addLayout(self.editLayout)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButtonSave = QPushButton(SessionDialog)
        self.pushButtonSave.setObjectName(u"pushButtonSave")
        self.pushButtonSave.setAutoDefault(False)

        self.horizontalLayout.addWidget(self.pushButtonSave)

        self.pushButtonReplay = QPushButton(SessionDialog)
        self.pushButtonReplay.setObjectName(u"pushButtonReplay")
        self.pushButtonReplay.setAutoDefault(False)

        self.horizontalLayout.addWidget(self.pushButtonReplay)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButtonClose = QPushButton(SessionDialog)
        self.pushButtonClose.setObjectName(u"pushButtonClose")
        self.pushButtonClose.setAutoDefault(False)

        self.horizontalLayout.addWidget(self.pushButtonClose)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(SessionDialog)

        QMetaObject.connectSlotsByName(SessionDialog)
    # setupUi

    def retranslateUi(self, SessionDialog):
        SessionDialog.setWindowTitle(QCoreApplication.translate("SessionDialog", u"Session", None))
        self.labelSummary.setText(QCoreApplication.translate("SessionDialog", u"lblSummary", None))
#if QT_CONFIG(tooltip)
        self.checkBoxChangesOnly.setToolTip(QCoreApplication.translate("SessionDialog", u"Hide the requests that only read -- inspecting, drawing, summarising. Everything is still recorded; this only changes what is shown and saved", None))
#endif // QT_CONFIG(tooltip)
        self.checkBoxChangesOnly.setText(QCoreApplication.translate("SessionDialog", u"Only requests that change something", None))
#if QT_CONFIG(tooltip)
        self.pushButtonRemove.setToolTip(QCoreApplication.translate("SessionDialog", u"Leave the selected requests out of the session you save. The journal keeps them", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonRemove.setText(QCoreApplication.translate("SessionDialog", u"Remove Selected", None))
#if QT_CONFIG(tooltip)
        self.pushButtonRestore.setToolTip(QCoreApplication.translate("SessionDialog", u"Bring back every request removed from this list", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonRestore.setText(QCoreApplication.translate("SessionDialog", u"Restore Removed", None))
#if QT_CONFIG(tooltip)
        self.pushButtonSave.setToolTip(QCoreApplication.translate("SessionDialog", u"Write the requests shown to a file, so they can be replayed later or attached to a bug report", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonSave.setText(QCoreApplication.translate("SessionDialog", u"Save session...", None))
#if QT_CONFIG(tooltip)
        self.pushButtonReplay.setToolTip(QCoreApplication.translate("SessionDialog", u"Read a saved session and run it against the project that is open now. Each step names the object it ran on, and one this project does not have is reported rather than skipped. Requests that only read are not run again", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonReplay.setText(QCoreApplication.translate("SessionDialog", u"Replay a session...", None))
        self.pushButtonClose.setText(QCoreApplication.translate("SessionDialog", u"Close", None))
    # retranslateUi

