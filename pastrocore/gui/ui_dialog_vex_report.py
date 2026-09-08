# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_vex_report.ui'
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
class Ui_VEXReportDialog(object):
    def setupUi(self, VEXReportDialog):
        if not VEXReportDialog.objectName():
            VEXReportDialog.setObjectName(u"VEXReportDialog")
        VEXReportDialog.resize(680, 460)
        VEXReportDialog.setMinimumSize(QSize(520, 360))
        icon = QIcon()
        icon.addFile(u":/icons/export_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        VEXReportDialog.setWindowIcon(icon)
        self.verticalLayout = QVBoxLayout(VEXReportDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelSummary = QLabel(VEXReportDialog)
        self.labelSummary.setObjectName(u"labelSummary")
        self.labelSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelSummary)

        self.labelPath = QLabel(VEXReportDialog)
        self.labelPath.setObjectName(u"labelPath")
        self.labelPath.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.labelPath.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelPath)

        self.labelOutstanding = QLabel(VEXReportDialog)
        self.labelOutstanding.setObjectName(u"labelOutstanding")
        self.labelOutstanding.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelOutstanding)

        self.tableOutstanding = QTableWidget(VEXReportDialog)
        self.tableOutstanding.setObjectName(u"tableOutstanding")
        self.tableOutstanding.setAlternatingRowColors(True)
        self.tableOutstanding.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableOutstanding.setSortingEnabled(False)
        self.tableOutstanding.setWordWrap(True)
        self.tableOutstanding.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableOutstanding)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButtonCopy = QPushButton(VEXReportDialog)
        self.pushButtonCopy.setObjectName(u"pushButtonCopy")

        self.horizontalLayout.addWidget(self.pushButtonCopy)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButtonClose = QPushButton(VEXReportDialog)
        self.pushButtonClose.setObjectName(u"pushButtonClose")

        self.horizontalLayout.addWidget(self.pushButtonClose)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(VEXReportDialog)

        QMetaObject.connectSlotsByName(VEXReportDialog)
    # setupUi

    def retranslateUi(self, VEXReportDialog):
        VEXReportDialog.setWindowTitle(QCoreApplication.translate("VEXReportDialog", u"VEX Written", None))
        self.labelSummary.setText(QCoreApplication.translate("VEXReportDialog", u"lblSummary", None))
        self.labelPath.setText(QCoreApplication.translate("VEXReportDialog", u"lblPath", None))
        self.labelOutstanding.setText(QCoreApplication.translate("VEXReportDialog", u"What the file leaves for the station to complete", None))
#if QT_CONFIG(tooltip)
        self.pushButtonCopy.setToolTip(QCoreApplication.translate("VEXReportDialog", u"Copy the report as text, to send with the file", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonCopy.setText(QCoreApplication.translate("VEXReportDialog", u"Copy", None))
        self.pushButtonClose.setText(QCoreApplication.translate("VEXReportDialog", u"Close", None))
    # retranslateUi

