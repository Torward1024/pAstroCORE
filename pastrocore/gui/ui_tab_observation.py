# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_observationjtUiOt.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTableView, QVBoxLayout, QWidget)

class Ui_ObservationInfoTab(object):
    def setupUi(self, ObservationInfoTab):
        if not ObservationInfoTab.objectName():
            ObservationInfoTab.setObjectName(u"ObservationInfoTab")
        ObservationInfoTab.resize(560, 429)
        self.verticalLayout = QVBoxLayout(ObservationInfoTab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.titleLabel = QLabel(ObservationInfoTab)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        font.setBold(True)
        self.titleLabel.setFont(font)

        self.verticalLayout.addWidget(self.titleLabel)

        self.projectInfoTable = QTableView(ObservationInfoTab)
        self.projectInfoTable.setObjectName(u"projectInfoTable")
        self.projectInfoTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.projectInfoTable.setAlternatingRowColors(True)
        self.projectInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projectInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.projectInfoTable)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.refreshButton = QPushButton(ObservationInfoTab)
        self.refreshButton.setObjectName(u"refreshButton")
        self.refreshButton.setStyleSheet(u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;")

        self.buttonLayout.addWidget(self.refreshButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(ObservationInfoTab)
        self.refreshButton.clicked.connect(self.projectInfoTable.update)

        QMetaObject.connectSlotsByName(ObservationInfoTab)
    # setupUi

    def retranslateUi(self, ObservationInfoTab):
        ObservationInfoTab.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"background-color: #ffffff; font-family: Arial;", None))
        self.titleLabel.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"color: #333333; padding-bottom: 10px;", None))
        self.titleLabel.setText(QCoreApplication.translate("ObservationInfoTab", u"Observation Information", None))
        self.projectInfoTable.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.refreshButton.setText(QCoreApplication.translate("ObservationInfoTab", u"Refresh", None))
    # retranslateUi