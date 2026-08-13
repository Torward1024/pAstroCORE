# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_run_report.ui'
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
class Ui_RunReportDialog(object):
    def setupUi(self, RunReportDialog):
        if not RunReportDialog.objectName():
            RunReportDialog.setObjectName(u"RunReportDialog")
        RunReportDialog.resize(620, 420)
        RunReportDialog.setMinimumSize(QSize(480, 320))
        icon = QIcon()
        icon.addFile(u":/icons/preferences.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        RunReportDialog.setWindowIcon(icon)
        RunReportDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.verticalLayout = QVBoxLayout(RunReportDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelSummary = QLabel(RunReportDialog)
        self.labelSummary.setObjectName(u"labelSummary")
        self.labelSummary.setStyleSheet(u"font-size: 10pt; padding: 4px;")
        self.labelSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelSummary)

        self.tableSteps = QTableWidget(RunReportDialog)
        self.tableSteps.setObjectName(u"tableSteps")
        self.tableSteps.setStyleSheet(u"QTableWidget {\n"
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
        self.tableSteps.setAlternatingRowColors(True)
        self.tableSteps.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableSteps.setSortingEnabled(False)
        self.tableSteps.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableSteps)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButtonCopy = QPushButton(RunReportDialog)
        self.pushButtonCopy.setObjectName(u"pushButtonCopy")
        self.pushButtonCopy.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout.addWidget(self.pushButtonCopy)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButtonClose = QPushButton(RunReportDialog)
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


        self.retranslateUi(RunReportDialog)

        QMetaObject.connectSlotsByName(RunReportDialog)
    # setupUi

    def retranslateUi(self, RunReportDialog):
        RunReportDialog.setWindowTitle(QCoreApplication.translate("RunReportDialog", u"Run Report", None))
        self.labelSummary.setText(QCoreApplication.translate("RunReportDialog", u"lblSummary", None))
#if QT_CONFIG(tooltip)
        self.pushButtonCopy.setToolTip(QCoreApplication.translate("RunReportDialog", u"Copy the report as text, for a bug report", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonCopy.setText(QCoreApplication.translate("RunReportDialog", u"Copy", None))
        self.pushButtonClose.setText(QCoreApplication.translate("RunReportDialog", u"Close", None))
    # retranslateUi

