# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_projectSEeocB.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableView, QWidget)

class Ui_ProjectInfoTab(object):
    def setupUi(self, ProjectInfoTab):
        if not ProjectInfoTab.objectName():
            ProjectInfoTab.setObjectName(u"ProjectInfoTab")
        ProjectInfoTab.resize(560, 429)
        self.gridLayout = QGridLayout(ProjectInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.titleLabel = QLabel(ProjectInfoTab)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        font.setBold(True)
        self.titleLabel.setFont(font)

        self.gridLayout.addWidget(self.titleLabel, 0, 0, 1, 2)

        self.label = QLabel(ProjectInfoTab)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(12)
        font1.setBold(False)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)

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

        self.gridLayout.addWidget(self.lineEdit, 1, 1, 1, 1)

        self.projectInfoTable = QTableView(ProjectInfoTab)
        self.projectInfoTable.setObjectName(u"projectInfoTable")
        self.projectInfoTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projectInfoTable.setAlternatingRowColors(True)
        self.projectInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projectInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.projectInfoTable, 2, 0, 1, 2)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.refreshButton = QPushButton(ProjectInfoTab)
        self.refreshButton.setObjectName(u"refreshButton")
        self.refreshButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff; /* \u0421\u0432\u0435\u0442\u043b\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5; /* \u0422\u0435\u043c\u043d\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0436\u0430\u0442\u0438\u0438 */\n"
"    padding-top: 7px; /* \u041b\u0435\u0433\u043a\u043e\u0435 \u0441\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u0432\u043d\u0438\u0437 \u0434\u043b\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0430 \"\u043f\u0440\u043e\u0434\u0430\u0432\u043b\u0438\u0432\u0430\u043d\u0438\u044f\" */\n"
"    padding-bottom: 5px;\n"
"}")
        self.refreshButton.setFlat(False)

        self.buttonLayout.addWidget(self.refreshButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.buttonLayout, 3, 0, 1, 2)


        self.retranslateUi(ProjectInfoTab)
        self.refreshButton.clicked.connect(self.projectInfoTable.update)

        QMetaObject.connectSlotsByName(ProjectInfoTab)
    # setupUi

    def retranslateUi(self, ProjectInfoTab):
        ProjectInfoTab.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"background-color: #ffffff; font-family: Arial;", None))
        self.titleLabel.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"color: #333333; padding-bottom: 10px;", None))
        self.titleLabel.setText(QCoreApplication.translate("ProjectInfoTab", u"Project Information", None))
        self.label.setText(QCoreApplication.translate("ProjectInfoTab", u"Name:", None))
        self.projectInfoTable.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.refreshButton.setText(QCoreApplication.translate("ProjectInfoTab", u"Refresh", None))
    # retranslateUi

