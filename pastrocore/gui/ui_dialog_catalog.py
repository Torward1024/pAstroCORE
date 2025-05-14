# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_catalogbmfLbP.ui'
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
        CatalogDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.gridLayout = QGridLayout(CatalogDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.catalogTable = QTableView(CatalogDialog)
        self.catalogTable.setObjectName(u"catalogTable")
        self.catalogTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.catalogTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.catalogTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.catalogTable, 0, 0, 1, 4)

        self.search = QLineEdit(CatalogDialog)
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
        self.catalogTable.setStyleSheet(QCoreApplication.translate("CatalogDialog", u"border: 1px solid #d3d3d3;", None))
        self.lbl_search.setText(QCoreApplication.translate("CatalogDialog", u"Search:", None))
        self.closeButton.setText(QCoreApplication.translate("CatalogDialog", u"Close", None))
    # retranslateUi