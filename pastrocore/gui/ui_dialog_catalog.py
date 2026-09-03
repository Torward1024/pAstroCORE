# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_catalog.ui'
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
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_CatalogDialog(object):
    def setupUi(self, CatalogDialog):
        if not CatalogDialog.objectName():
            CatalogDialog.setObjectName(u"CatalogDialog")
        CatalogDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        CatalogDialog.resize(740, 550)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(CatalogDialog.sizePolicy().hasHeightForWidth())
        CatalogDialog.setSizePolicy(sizePolicy)
        CatalogDialog.setMinimumSize(QSize(740, 550))
        CatalogDialog.setMaximumSize(QSize(740, 550))
        icon = QIcon()
        icon.addFile(u":/icons/catalog.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CatalogDialog.setWindowIcon(icon)
        CatalogDialog.setModal(True)
        self.gridLayout = QGridLayout(CatalogDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.closeButton = QPushButton(CatalogDialog)
        self.closeButton.setObjectName(u"closeButton")
        self.closeButton.setFlat(True)

        self.gridLayout.addWidget(self.closeButton, 2, 3, 1, 1)

        self.catalogTable = QTableView(CatalogDialog)
        self.catalogTable.setObjectName(u"catalogTable")
        self.catalogTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.catalogTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.catalogTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.catalogTable, 0, 0, 1, 4)

        self.search = QLineEdit(CatalogDialog)
        self.search.setObjectName(u"search")

        self.gridLayout.addWidget(self.search, 2, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 2, 2, 1, 1)

        self.lbl_search = QLabel(CatalogDialog)
        self.lbl_search.setObjectName(u"lbl_search")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.lbl_search.setFont(font)

        self.gridLayout.addWidget(self.lbl_search, 2, 0, 1, 1)


        self.retranslateUi(CatalogDialog)

        QMetaObject.connectSlotsByName(CatalogDialog)
    # setupUi

    def retranslateUi(self, CatalogDialog):
        CatalogDialog.setWindowTitle(QCoreApplication.translate("CatalogDialog", u"Dialog", None))
        self.closeButton.setText(QCoreApplication.translate("CatalogDialog", u"Close", None))
        self.lbl_search.setText(QCoreApplication.translate("CatalogDialog", u"Search:", None))
    # retranslateUi

