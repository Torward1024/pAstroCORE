# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_edtior_source.ui'
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
    QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTableView,
    QVBoxLayout, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_SourceEditorDialog(object):
    def setupUi(self, SourceEditorDialog):
        if not SourceEditorDialog.objectName():
            SourceEditorDialog.setObjectName(u"SourceEditorDialog")
        SourceEditorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        SourceEditorDialog.resize(460, 380)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SourceEditorDialog.sizePolicy().hasHeightForWidth())
        SourceEditorDialog.setSizePolicy(sizePolicy)
        SourceEditorDialog.setMinimumSize(QSize(460, 380))
        SourceEditorDialog.setMaximumSize(QSize(460, 380))
        icon = QIcon()
        icon.addFile(u":/icons/edit_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SourceEditorDialog.setWindowIcon(icon)
        SourceEditorDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(SourceEditorDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelName = QLabel(SourceEditorDialog)
        self.labelName.setObjectName(u"labelName")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelName)

        self.nameEdit = QLineEdit(SourceEditorDialog)
        self.nameEdit.setObjectName(u"nameEdit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.nameEdit)

        self.labelNameJ2000 = QLabel(SourceEditorDialog)
        self.labelNameJ2000.setObjectName(u"labelNameJ2000")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelNameJ2000)

        self.nameJ2000Edit = QLineEdit(SourceEditorDialog)
        self.nameJ2000Edit.setObjectName(u"nameJ2000Edit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameJ2000Edit)

        self.labelAltName = QLabel(SourceEditorDialog)
        self.labelAltName.setObjectName(u"labelAltName")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelAltName)

        self.altNameEdit = QLineEdit(SourceEditorDialog)
        self.altNameEdit.setObjectName(u"altNameEdit")

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

        self.line_2 = QFrame(SourceEditorDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.addFluxButton = QPushButton(SourceEditorDialog)
        self.addFluxButton.setObjectName(u"addFluxButton")

        self.horizontalLayout.addWidget(self.addFluxButton)

        self.removeFluxButton = QPushButton(SourceEditorDialog)
        self.removeFluxButton.setObjectName(u"removeFluxButton")

        self.horizontalLayout.addWidget(self.removeFluxButton)

        self.clearFluxButton = QPushButton(SourceEditorDialog)
        self.clearFluxButton.setObjectName(u"clearFluxButton")

        self.horizontalLayout.addWidget(self.clearFluxButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.fluxTable = QTableView(SourceEditorDialog)
        self.fluxTable.setObjectName(u"fluxTable")
        self.fluxTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.fluxTable.setAlternatingRowColors(True)
        self.fluxTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.fluxTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.fluxTable, 1, 0, 1, 1)

        self.labelFluxTable = QLabel(SourceEditorDialog)
        self.labelFluxTable.setObjectName(u"labelFluxTable")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        font.setBold(False)
        self.labelFluxTable.setFont(font)

        self.gridLayout.addWidget(self.labelFluxTable, 0, 0, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout)

        self.line = QFrame(SourceEditorDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.saveButton = QPushButton(SourceEditorDialog)
        self.saveButton.setObjectName(u"saveButton")

        self.buttonLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(SourceEditorDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.buttonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(SourceEditorDialog)
        self.saveButton.clicked.connect(SourceEditorDialog.accept)
        self.cancelButton.clicked.connect(SourceEditorDialog.reject)

        QMetaObject.connectSlotsByName(SourceEditorDialog)
    # setupUi

    def retranslateUi(self, SourceEditorDialog):
        SourceEditorDialog.setWindowTitle(QCoreApplication.translate("SourceEditorDialog", u"Edit Source", None))
        self.labelName.setText(QCoreApplication.translate("SourceEditorDialog", u"Name (B1950):", None))
        self.nameEdit.setPlaceholderText(QCoreApplication.translate("SourceEditorDialog", u"Enter source name", None))
        self.labelNameJ2000.setText(QCoreApplication.translate("SourceEditorDialog", u"Name (J2000):", None))
        self.nameJ2000Edit.setPlaceholderText(QCoreApplication.translate("SourceEditorDialog", u"Enter J2000 name (optional)", None))
        self.labelAltName.setText(QCoreApplication.translate("SourceEditorDialog", u"Alternative Name:", None))
        self.altNameEdit.setPlaceholderText(QCoreApplication.translate("SourceEditorDialog", u"Enter alternative name (optional)", None))
        self.labelRa.setText(QCoreApplication.translate("SourceEditorDialog", u"RA (hh:mm:ss):", None))
        self.raHEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"h", None))
        self.raMEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"m", None))
        self.raSEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"s", None))
        self.labelDec.setText(QCoreApplication.translate("SourceEditorDialog", u"DEC (dd:mm:ss):", None))
        self.deDEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"d", None))
        self.deMEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"m", None))
        self.deSEdit.setSuffix(QCoreApplication.translate("SourceEditorDialog", u"s", None))
        self.labelSpectralIndex.setText(QCoreApplication.translate("SourceEditorDialog", u"Spectral Index:", None))
        self.spectralIndexEdit.setProperty(u"placeholderText", QCoreApplication.translate("SourceEditorDialog", u"Enter spectral index (optional)", None))
        self.labelIsActive.setText(QCoreApplication.translate("SourceEditorDialog", u"Active:", None))
        self.addFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Add", None))
        self.removeFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Remove", None))
        self.clearFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Clear", None))
        self.labelFluxTable.setText(QCoreApplication.translate("SourceEditorDialog", u"Flux Table (MHz, Jy):", None))
        self.saveButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Cancel", None))
    # retranslateUi

