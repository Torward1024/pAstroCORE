# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_projectksjveQ.ui'
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

class Ui_ProjectInfoTab(object):
    def setupUi(self, ProjectInfoTab):
        if not ProjectInfoTab.objectName():
            ProjectInfoTab.setObjectName(u"ProjectInfoTab")
        ProjectInfoTab.resize(624, 468)
        self.gridLayout = QGridLayout(ProjectInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.titleLabel = QLabel(ProjectInfoTab)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        font.setBold(True)
        self.titleLabel.setFont(font)

        self.gridLayout.addWidget(self.titleLabel, 0, 0, 1, 3)

        self.label = QLabel(ProjectInfoTab)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(12)
        font1.setBold(False)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)

        self.projectInfoTable = QTableView(ProjectInfoTab)
        self.projectInfoTable.setObjectName(u"projectInfoTable")
        self.projectInfoTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projectInfoTable.setAlternatingRowColors(True)
        self.projectInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projectInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.projectInfoTable, 2, 0, 1, 3)

        self.label_2 = QLabel(ProjectInfoTab)
        self.label_2.setObjectName(u"label_2")
        font2 = QFont()
        font2.setFamilies([u"Arial"])
        font2.setPointSize(12)
        self.label_2.setFont(font2)

        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 1)

        self.lineEdit = QLineEdit(ProjectInfoTab)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setStyleSheet(u"QLineEdit {\n"
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
        self.lineEdit.setReadOnly(True)

        self.gridLayout.addWidget(self.lineEdit, 1, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 2, 1, 1)

        self.search = QLineEdit(ProjectInfoTab)
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

        self.gridLayout.addWidget(self.search, 3, 1, 1, 1)


        self.retranslateUi(ProjectInfoTab)

        QMetaObject.connectSlotsByName(ProjectInfoTab)
    # setupUi

    def retranslateUi(self, ProjectInfoTab):
        ProjectInfoTab.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"background-color: #ffffff; font-family: Arial;", None))
        self.titleLabel.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"color: #333333; padding-bottom: 10px;", None))
        self.titleLabel.setText(QCoreApplication.translate("ProjectInfoTab", u"Project Information", None))
        self.label.setText(QCoreApplication.translate("ProjectInfoTab", u"Name:", None))
        self.projectInfoTable.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.label_2.setText(QCoreApplication.translate("ProjectInfoTab", u"Search:", None))
    # retranslateUi