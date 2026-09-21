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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableView, QVBoxLayout,
    QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_CatalogDialog(object):
    def setupUi(self, CatalogDialog):
        if not CatalogDialog.objectName():
            CatalogDialog.setObjectName(u"CatalogDialog")
        CatalogDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        CatalogDialog.resize(820, 560)
        icon = QIcon()
        icon.addFile(u":/icons/catalog.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CatalogDialog.setWindowIcon(icon)
        CatalogDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(CatalogDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.catalogTable = QTableView(CatalogDialog)
        self.catalogTable.setObjectName(u"catalogTable")
        self.catalogTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.catalogTable.setAlternatingRowColors(True)
        self.catalogTable.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.catalogTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.catalogTable)

        self.editLayout = QHBoxLayout()
        self.editLayout.setObjectName(u"editLayout")
        self.addButton = QPushButton(CatalogDialog)
        self.addButton.setObjectName(u"addButton")
        self.addButton.setAutoDefault(False)

        self.editLayout.addWidget(self.addButton)

        self.addSpaceButton = QPushButton(CatalogDialog)
        self.addSpaceButton.setObjectName(u"addSpaceButton")
        self.addSpaceButton.setAutoDefault(False)

        self.editLayout.addWidget(self.addSpaceButton)

        self.editButton = QPushButton(CatalogDialog)
        self.editButton.setObjectName(u"editButton")
        self.editButton.setAutoDefault(False)

        self.editLayout.addWidget(self.editButton)

        self.removeButton = QPushButton(CatalogDialog)
        self.removeButton.setObjectName(u"removeButton")
        self.removeButton.setAutoDefault(False)

        self.editLayout.addWidget(self.removeButton)

        self.editSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.editLayout.addItem(self.editSpacer)

        self.lbl_search = QLabel(CatalogDialog)
        self.lbl_search.setObjectName(u"lbl_search")

        self.editLayout.addWidget(self.lbl_search)

        self.search = QLineEdit(CatalogDialog)
        self.search.setObjectName(u"search")
        self.search.setClearButtonEnabled(True)

        self.editLayout.addWidget(self.search)


        self.verticalLayout.addLayout(self.editLayout)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.saveButton = QPushButton(CatalogDialog)
        self.saveButton.setObjectName(u"saveButton")
        self.saveButton.setAutoDefault(False)

        self.buttonLayout.addWidget(self.saveButton)

        self.saveAsButton = QPushButton(CatalogDialog)
        self.saveAsButton.setObjectName(u"saveAsButton")
        self.saveAsButton.setAutoDefault(False)

        self.buttonLayout.addWidget(self.saveAsButton)

        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.buttonSpacer)

        self.addSelectedButton = QPushButton(CatalogDialog)
        self.addSelectedButton.setObjectName(u"addSelectedButton")
        self.addSelectedButton.setAutoDefault(False)

        self.buttonLayout.addWidget(self.addSelectedButton)

        self.closeButton = QPushButton(CatalogDialog)
        self.closeButton.setObjectName(u"closeButton")
        self.closeButton.setAutoDefault(False)

        self.buttonLayout.addWidget(self.closeButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(CatalogDialog)

        QMetaObject.connectSlotsByName(CatalogDialog)
    # setupUi

    def retranslateUi(self, CatalogDialog):
        CatalogDialog.setWindowTitle(QCoreApplication.translate("CatalogDialog", u"Catalog", None))
#if QT_CONFIG(tooltip)
        self.addButton.setToolTip(QCoreApplication.translate("CatalogDialog", u"Add a new entry to the catalogue", None))
#endif // QT_CONFIG(tooltip)
        self.addButton.setText(QCoreApplication.translate("CatalogDialog", u"Add...", None))
#if QT_CONFIG(tooltip)
        self.addSpaceButton.setToolTip(QCoreApplication.translate("CatalogDialog", u"Add a space telescope to the catalogue", None))
#endif // QT_CONFIG(tooltip)
        self.addSpaceButton.setText(QCoreApplication.translate("CatalogDialog", u"Add Space Telescope...", None))
#if QT_CONFIG(tooltip)
        self.editButton.setToolTip(QCoreApplication.translate("CatalogDialog", u"Edit the selected entry. Double-clicking a row does the same", None))
#endif // QT_CONFIG(tooltip)
        self.editButton.setText(QCoreApplication.translate("CatalogDialog", u"Edit...", None))
#if QT_CONFIG(tooltip)
        self.removeButton.setToolTip(QCoreApplication.translate("CatalogDialog", u"Remove the selected entries from the catalogue", None))
#endif // QT_CONFIG(tooltip)
        self.removeButton.setText(QCoreApplication.translate("CatalogDialog", u"Remove", None))
        self.lbl_search.setText(QCoreApplication.translate("CatalogDialog", u"Search:", None))
        self.saveButton.setProperty(u"role", QCoreApplication.translate("CatalogDialog", u"primary", None))
#if QT_CONFIG(tooltip)
        self.saveButton.setToolTip(QCoreApplication.translate("CatalogDialog", u"Write the catalogue to its file. One that came with the application, or was read from a .dat file, is saved as JSON under a name you choose", None))
#endif // QT_CONFIG(tooltip)
        self.saveButton.setText(QCoreApplication.translate("CatalogDialog", u"Save", None))
#if QT_CONFIG(tooltip)
        self.saveAsButton.setToolTip(QCoreApplication.translate("CatalogDialog", u"Write the catalogue to a new JSON file, and use that file from now on", None))
#endif // QT_CONFIG(tooltip)
        self.saveAsButton.setText(QCoreApplication.translate("CatalogDialog", u"Save As...", None))
        self.addSelectedButton.setText(QCoreApplication.translate("CatalogDialog", u"Add Selected", None))
        self.closeButton.setText(QCoreApplication.translate("CatalogDialog", u"Close", None))
    # retranslateUi

