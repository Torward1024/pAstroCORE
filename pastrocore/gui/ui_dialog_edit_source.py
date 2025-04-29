# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_edtior_sourcecUZLny.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableView, QVBoxLayout, QWidget)

class Ui_SourceEditorDialog(object):
    def setupUi(self, SourceEditorDialog):
        if not SourceEditorDialog.objectName():
            SourceEditorDialog.setObjectName(u"SourceEditorDialog")
        SourceEditorDialog.resize(600, 500)
        self.verticalLayout = QVBoxLayout(SourceEditorDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelName = QLabel(SourceEditorDialog)
        self.labelName.setObjectName(u"labelName")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelName)

        self.nameEdit = QLineEdit(SourceEditorDialog)
        self.nameEdit.setObjectName(u"nameEdit")
        self.nameEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.nameEdit)

        self.labelNameJ2000 = QLabel(SourceEditorDialog)
        self.labelNameJ2000.setObjectName(u"labelNameJ2000")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelNameJ2000)

        self.nameJ2000Edit = QLineEdit(SourceEditorDialog)
        self.nameJ2000Edit.setObjectName(u"nameJ2000Edit")
        self.nameJ2000Edit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameJ2000Edit)

        self.labelAltName = QLabel(SourceEditorDialog)
        self.labelAltName.setObjectName(u"labelAltName")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelAltName)

        self.altNameEdit = QLineEdit(SourceEditorDialog)
        self.altNameEdit.setObjectName(u"altNameEdit")
        self.altNameEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.altNameEdit)

        self.labelRa = QLabel(SourceEditorDialog)
        self.labelRa.setObjectName(u"labelRa")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelRa)

        self.raLayout = QHBoxLayout()
        self.raLayout.setObjectName(u"raLayout")
        self.raHEdit = QDoubleSpinBox(SourceEditorDialog)
        self.raHEdit.setObjectName(u"raHEdit")
        self.raHEdit.setDecimals(0)
        self.raHEdit.setMaximum(23.000000000000000)

        self.raLayout.addWidget(self.raHEdit)

        self.raMEdit = QDoubleSpinBox(SourceEditorDialog)
        self.raMEdit.setObjectName(u"raMEdit")
        self.raMEdit.setDecimals(0)
        self.raMEdit.setMaximum(59.000000000000000)

        self.raLayout.addWidget(self.raMEdit)

        self.raSEdit = QDoubleSpinBox(SourceEditorDialog)
        self.raSEdit.setObjectName(u"raSEdit")
        self.raSEdit.setDecimals(3)
        self.raSEdit.setMaximum(59.999000000000002)

        self.raLayout.addWidget(self.raSEdit)


        self.formLayout.setLayout(3, QFormLayout.FieldRole, self.raLayout)

        self.labelDec = QLabel(SourceEditorDialog)
        self.labelDec.setObjectName(u"labelDec")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.labelDec)

        self.decLayout = QHBoxLayout()
        self.decLayout.setObjectName(u"decLayout")
        self.deDEdit = QDoubleSpinBox(SourceEditorDialog)
        self.deDEdit.setObjectName(u"deDEdit")
        self.deDEdit.setDecimals(0)
        self.deDEdit.setMinimum(-90.000000000000000)
        self.deDEdit.setMaximum(90.000000000000000)

        self.decLayout.addWidget(self.deDEdit)

        self.deMEdit = QDoubleSpinBox(SourceEditorDialog)
        self.deMEdit.setObjectName(u"deMEdit")
        self.deMEdit.setDecimals(0)
        self.deMEdit.setMaximum(59.000000000000000)

        self.decLayout.addWidget(self.deMEdit)

        self.deSEdit = QDoubleSpinBox(SourceEditorDialog)
        self.deSEdit.setObjectName(u"deSEdit")
        self.deSEdit.setDecimals(3)
        self.deSEdit.setMaximum(59.999000000000002)

        self.decLayout.addWidget(self.deSEdit)


        self.formLayout.setLayout(4, QFormLayout.FieldRole, self.decLayout)

        self.labelSpectralIndex = QLabel(SourceEditorDialog)
        self.labelSpectralIndex.setObjectName(u"labelSpectralIndex")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.labelSpectralIndex)

        self.spectralIndexEdit = QDoubleSpinBox(SourceEditorDialog)
        self.spectralIndexEdit.setObjectName(u"spectralIndexEdit")
        self.spectralIndexEdit.setDecimals(3)
        self.spectralIndexEdit.setMinimum(-999.000000000000000)
        self.spectralIndexEdit.setMaximum(999.000000000000000)

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.spectralIndexEdit)

        self.labelIsActive = QLabel(SourceEditorDialog)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(SourceEditorDialog)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(6, QFormLayout.FieldRole, self.isActiveCheckBox)


        self.verticalLayout.addLayout(self.formLayout)

        self.labelFluxTable = QLabel(SourceEditorDialog)
        self.labelFluxTable.setObjectName(u"labelFluxTable")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(10)
        font.setBold(True)
        self.labelFluxTable.setFont(font)

        self.verticalLayout.addWidget(self.labelFluxTable)

        self.fluxTable = QTableView(SourceEditorDialog)
        self.fluxTable.setObjectName(u"fluxTable")
        self.fluxTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.fluxTable.setAlternatingRowColors(True)
        self.fluxTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.fluxTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.fluxTable)

        self.fluxButtonLayout = QHBoxLayout()
        self.fluxButtonLayout.setObjectName(u"fluxButtonLayout")
        self.addFluxButton = QPushButton(SourceEditorDialog)
        self.addFluxButton.setObjectName(u"addFluxButton")

        self.fluxButtonLayout.addWidget(self.addFluxButton)

        self.removeFluxButton = QPushButton(SourceEditorDialog)
        self.removeFluxButton.setObjectName(u"removeFluxButton")

        self.fluxButtonLayout.addWidget(self.removeFluxButton)

        self.clearFluxButton = QPushButton(SourceEditorDialog)
        self.clearFluxButton.setObjectName(u"clearFluxButton")

        self.fluxButtonLayout.addWidget(self.clearFluxButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.fluxButtonLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.fluxButtonLayout)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer1 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer1)

        self.saveButton = QPushButton(SourceEditorDialog)
        self.saveButton.setObjectName(u"saveButton")
        self.saveButton.setStyleSheet(u"QPushButton {\n"
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

        self.buttonLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(SourceEditorDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setStyleSheet(u"QPushButton {\n"
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

        self.buttonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(SourceEditorDialog)
        self.saveButton.clicked.connect(SourceEditorDialog.accept)
        self.cancelButton.clicked.connect(SourceEditorDialog.reject)

        QMetaObject.connectSlotsByName(SourceEditorDialog)
    # setupUi

    def retranslateUi(self, SourceEditorDialog):
        SourceEditorDialog.setWindowTitle(QCoreApplication.translate("SourceEditorDialog", u"Edit Source", None))
        SourceEditorDialog.setStyleSheet(QCoreApplication.translate("SourceEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelName.setText(QCoreApplication.translate("SourceEditorDialog", u"Name (B1950):", None))
        self.nameEdit.setPlaceholderText(QCoreApplication.translate("SourceEditorDialog", u"Enter source name", None))
        self.labelNameJ2000.setText(QCoreApplication.translate("SourceEditorDialog", u"Name (J2000):", None))
        self.nameJ2000Edit.setPlaceholderText(QCoreApplication.translate("SourceEditorDialog", u"Enter J2000 name (optional)", None))
        self.labelAltName.setText(QCoreApplication.translate("SourceEditorDialog", u"Alternative Name:", None))
        self.altNameEdit.setPlaceholderText(QCoreApplication.translate("SourceEditorDialog", u"Enter alternative name (optional)", None))
        self.labelRa.setText(QCoreApplication.translate("SourceEditorDialog", u"Right Ascension (hms):", None))
        self.raHEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"h", None))
        self.raMEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"m", None))
        self.raSEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"s", None))
        self.labelDec.setText(QCoreApplication.translate("SourceEditorDialog", u"Declination (dms):", None))
        self.deDEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"d", None))
        self.deMEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"m", None))
        self.deSEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"s", None))
        self.labelSpectralIndex.setText(QCoreApplication.translate("SourceEditorDialog", u"Spectral Index:", None))
        self.spectralIndexEdit.setProperty(u"placeholderText", QCoreApplication.translate("SourceEditorDialog", u"Enter spectral index (optional)", None))
        self.labelIsActive.setText(QCoreApplication.translate("SourceEditorDialog", u"Active:", None))
        self.labelFluxTable.setText(QCoreApplication.translate("SourceEditorDialog", u"Flux Table (MHz, Jy):", None))
        self.fluxTable.setStyleSheet(QCoreApplication.translate("SourceEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addFluxButton.setStyleSheet(QCoreApplication.translate("SourceEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Add Flux", None))
        self.removeFluxButton.setStyleSheet(QCoreApplication.translate("SourceEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Remove Flux", None))
        self.clearFluxButton.setStyleSheet(QCoreApplication.translate("SourceEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Clear Flux Table", None))
        self.saveButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Cancel", None))
    # retranslateUi