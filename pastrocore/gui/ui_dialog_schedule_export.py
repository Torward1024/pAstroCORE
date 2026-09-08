# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_schedule_export.ui'
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
class Ui_ScheduleExportDialog(object):
    def setupUi(self, ScheduleExportDialog):
        if not ScheduleExportDialog.objectName():
            ScheduleExportDialog.setObjectName(u"ScheduleExportDialog")
        ScheduleExportDialog.resize(680, 460)
        ScheduleExportDialog.setMinimumSize(QSize(520, 360))
        icon = QIcon()
        icon.addFile(u":/icons/export_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        ScheduleExportDialog.setWindowIcon(icon)
        self.verticalLayout = QVBoxLayout(ScheduleExportDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelSummary = QLabel(ScheduleExportDialog)
        self.labelSummary.setObjectName(u"labelSummary")
        self.labelSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelSummary)

        self.labelPath = QLabel(ScheduleExportDialog)
        self.labelPath.setObjectName(u"labelPath")
        self.labelPath.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.labelPath.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelPath)

        self.labelOutstanding = QLabel(ScheduleExportDialog)
        self.labelOutstanding.setObjectName(u"labelOutstanding")
        self.labelOutstanding.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelOutstanding)

        self.tableOutstanding = QTableWidget(ScheduleExportDialog)
        self.tableOutstanding.setObjectName(u"tableOutstanding")
        self.tableOutstanding.setAlternatingRowColors(True)
        self.tableOutstanding.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableOutstanding.setSortingEnabled(False)
        self.tableOutstanding.setWordWrap(True)
        self.tableOutstanding.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableOutstanding)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButtonCopy = QPushButton(ScheduleExportDialog)
        self.pushButtonCopy.setObjectName(u"pushButtonCopy")

        self.horizontalLayout.addWidget(self.pushButtonCopy)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButtonClose = QPushButton(ScheduleExportDialog)
        self.pushButtonClose.setObjectName(u"pushButtonClose")

        self.horizontalLayout.addWidget(self.pushButtonClose)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(ScheduleExportDialog)

        QMetaObject.connectSlotsByName(ScheduleExportDialog)
    # setupUi

    def retranslateUi(self, ScheduleExportDialog):
        ScheduleExportDialog.setWindowTitle(QCoreApplication.translate("ScheduleExportDialog", u"Schedule Written", None))
        self.labelSummary.setText(QCoreApplication.translate("ScheduleExportDialog", u"lblSummary", None))
        self.labelPath.setText(QCoreApplication.translate("ScheduleExportDialog", u"lblPath", None))
        self.labelOutstanding.setText(QCoreApplication.translate("ScheduleExportDialog", u"What the file leaves for the station to complete", None))
#if QT_CONFIG(tooltip)
        self.pushButtonCopy.setToolTip(QCoreApplication.translate("ScheduleExportDialog", u"Copy the report as text, to send with the file", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonCopy.setText(QCoreApplication.translate("ScheduleExportDialog", u"Copy", None))
        self.pushButtonClose.setText(QCoreApplication.translate("ScheduleExportDialog", u"Close", None))
    # retranslateUi

