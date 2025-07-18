# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_projectSAjDWk.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QSizePolicy,
    QSpacerItem, QTableView, QWidget)

class Ui_ProjectInfoTab(object):
    def setupUi(self, ProjectInfoTab):
        if not ProjectInfoTab.objectName():
            ProjectInfoTab.setObjectName(u"ProjectInfoTab")
        ProjectInfoTab.resize(598, 468)
        self.gridLayout = QGridLayout(ProjectInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(ProjectInfoTab)
        self.label_2.setObjectName(u"label_2")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.label_2.setFont(font)

        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)

        self.line = QFrame(ProjectInfoTab)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 3, 0, 1, 3)

        self.label = QLabel(ProjectInfoTab)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(9)
        font1.setBold(False)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 2, 1, 1)

        self.projectInfoTable = QTableView(ProjectInfoTab)
        self.projectInfoTable.setObjectName(u"projectInfoTable")
        self.projectInfoTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"    padding: 0; /* Ensure no default padding */\n"
"}\n"
"\n"
"QTableView::item, QTableWidget::item {\n"
"    padding: 4px; /* Consistent padding for normal state */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Consistent padding for selected state */\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Explicitly set same padding to avoid shift */\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external bord"
                        "er to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"    border-right: none; /* Avoid doubling with adjacent sections */\n"
"    border-left: none; /* Clean look */\n"
"    border-top: none; /* Clean look */\n"
"    padding: 4px;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"}\n"
"\n"
"QHeaderView::section:horizontal {\n"
"    border-right: 1px solid #d3d3d3; /* Separator between columns */\n"
"}\n"
"\n"
"QHeaderView::section:vertical {\n"
"    border-bottom: 1px solid #d3d3d3; /* Separator between rows */\n"
"}\n"
"\n"
"QHeaderView::section:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Explicitly set same padding to avoid shift */\n"
"}")
        self.projectInfoTable.setFrameShadow(QFrame.Shadow.Sunken)
        self.projectInfoTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projectInfoTable.setAlternatingRowColors(True)
        self.projectInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projectInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.projectInfoTable.setSortingEnabled(False)
        self.projectInfoTable.verticalHeader().setVisible(False)

        self.gridLayout.addWidget(self.projectInfoTable, 2, 0, 1, 3)

        self.lineEdit = QLineEdit(ProjectInfoTab)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setFont(font)
        self.lineEdit.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
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

        self.gridLayout.addWidget(self.lineEdit, 0, 1, 1, 1)

        self.search = QLineEdit(ProjectInfoTab)
        self.search.setObjectName(u"search")
        self.search.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
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

        self.gridLayout.addWidget(self.search, 4, 1, 1, 1)

        self.line_2 = QFrame(ProjectInfoTab)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 1, 0, 1, 3)


        self.retranslateUi(ProjectInfoTab)

        QMetaObject.connectSlotsByName(ProjectInfoTab)
    # setupUi

    def retranslateUi(self, ProjectInfoTab):
        ProjectInfoTab.setStyleSheet(QCoreApplication.translate("ProjectInfoTab", u"background-color: #ffffff; font-family: Arial;", None))
        self.label_2.setText(QCoreApplication.translate("ProjectInfoTab", u"Search:", None))
        self.label.setText(QCoreApplication.translate("ProjectInfoTab", u"Name:", None))
    # retranslateUi