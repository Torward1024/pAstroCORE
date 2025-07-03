# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_catalogTKYoBm.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableView, QWidget)

class Ui_CatalogDialog(object):
    def setupUi(self, CatalogDialog):
        if not CatalogDialog.objectName():
            CatalogDialog.setObjectName(u"CatalogDialog")
        CatalogDialog.resize(609, 510)
        icon = QIcon()
        icon.addFile(u":/icons/catalog.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CatalogDialog.setWindowIcon(icon)
        CatalogDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.gridLayout = QGridLayout(CatalogDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.catalogTable = QTableView(CatalogDialog)
        self.catalogTable.setObjectName(u"catalogTable")
        self.catalogTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external border to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"   "
                        " border-right: none; /* Avoid doubling with adjacent sections */\n"
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
"}")
        self.catalogTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.catalogTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.catalogTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.catalogTable, 0, 0, 1, 4)

        self.search = QLineEdit(CatalogDialog)
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

        self.gridLayout.addWidget(self.search, 1, 1, 1, 1)

        self.lbl_search = QLabel(CatalogDialog)
        self.lbl_search.setObjectName(u"lbl_search")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.lbl_search.setFont(font)

        self.gridLayout.addWidget(self.lbl_search, 1, 0, 1, 1)

        self.closeButton = QPushButton(CatalogDialog)
        self.closeButton.setObjectName(u"closeButton")
        self.closeButton.setStyleSheet(u"QPushButton {\n"
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
        self.closeButton.setFlat(True)

        self.gridLayout.addWidget(self.closeButton, 1, 3, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 2, 1, 1)


        self.retranslateUi(CatalogDialog)

        QMetaObject.connectSlotsByName(CatalogDialog)
    # setupUi

    def retranslateUi(self, CatalogDialog):
        CatalogDialog.setWindowTitle(QCoreApplication.translate("CatalogDialog", u"Dialog", None))
        self.lbl_search.setText(QCoreApplication.translate("CatalogDialog", u"Search:", None))
        self.closeButton.setText(QCoreApplication.translate("CatalogDialog", u"Close", None))
    # retranslateUi