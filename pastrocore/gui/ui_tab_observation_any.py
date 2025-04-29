# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_observation_anyEwuiSF.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QHeaderView,
    QLabel, QLineEdit, QSizePolicy, QSpacerItem,
    QTableView, QWidget)

class Ui_observation_tab(object):
    def setupUi(self, observation_tab):
        if not observation_tab.objectName():
            observation_tab.setObjectName(u"observation_tab")
        observation_tab.resize(479, 355)
        observation_tab.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.gridLayout = QGridLayout(observation_tab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lbl_search = QLabel(observation_tab)
        self.lbl_search.setObjectName(u"lbl_search")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(12)
        self.lbl_search.setFont(font)

        self.gridLayout.addWidget(self.lbl_search, 1, 0, 1, 1)

        self.search = QLineEdit(observation_tab)
        self.search.setObjectName(u"search")
        self.search.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout.addWidget(self.search, 1, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(194, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 2, 1, 1)

        self.table = QTableView(observation_tab)
        self.table.setObjectName(u"table")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.table, 0, 0, 1, 3)


        self.retranslateUi(observation_tab)

        QMetaObject.connectSlotsByName(observation_tab)
    # setupUi

    def retranslateUi(self, observation_tab):
        observation_tab.setWindowTitle(QCoreApplication.translate("observation_tab", u"Form", None))
        self.lbl_search.setText(QCoreApplication.translate("observation_tab", u"Search:", None))
        self.table.setStyleSheet(QCoreApplication.translate("observation_tab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
    # retranslateUi