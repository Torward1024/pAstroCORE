# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_if.ui'
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
    QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_IFEditorDialog(object):
    def setupUi(self, IFEditorDialog):
        if not IFEditorDialog.objectName():
            IFEditorDialog.setObjectName(u"IFEditorDialog")
        IFEditorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        IFEditorDialog.resize(430, 296)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(IFEditorDialog.sizePolicy().hasHeightForWidth())
        IFEditorDialog.setSizePolicy(sizePolicy)
        IFEditorDialog.setMinimumSize(QSize(430, 296))
        IFEditorDialog.setMaximumSize(QSize(430, 296))
        icon = QIcon()
        icon.addFile(u":/icons/edit_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        IFEditorDialog.setWindowIcon(icon)
        IFEditorDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(IFEditorDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelFrequency = QLabel(IFEditorDialog)
        self.labelFrequency.setObjectName(u"labelFrequency")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelFrequency)

        self.frequencyEdit = QDoubleSpinBox(IFEditorDialog)
        self.frequencyEdit.setObjectName(u"frequencyEdit")
        self.frequencyEdit.setDecimals(3)
        self.frequencyEdit.setMinimum(1.000000000000000)
        self.frequencyEdit.setMaximum(1000000.000000000000000)
        self.frequencyEdit.setValue(1000.000000000000000)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.frequencyEdit)

        self.labelWavelength = QLabel(IFEditorDialog)
        self.labelWavelength.setObjectName(u"labelWavelength")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelWavelength)

        self.wavelengthDisplay = QLabel(IFEditorDialog)
        self.wavelengthDisplay.setObjectName(u"wavelengthDisplay")
        self.wavelengthDisplay.setFrameShape(QFrame.Shape.Panel)
        self.wavelengthDisplay.setFrameShadow(QFrame.Shadow.Sunken)
        self.wavelengthDisplay.setIndent(1)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.wavelengthDisplay)

        self.labelBandwidth = QLabel(IFEditorDialog)
        self.labelBandwidth.setObjectName(u"labelBandwidth")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelBandwidth)

        self.bandwidthEdit = QDoubleSpinBox(IFEditorDialog)
        self.bandwidthEdit.setObjectName(u"bandwidthEdit")
        self.bandwidthEdit.setDecimals(3)
        self.bandwidthEdit.setMinimum(1.000000000000000)
        self.bandwidthEdit.setMaximum(128000.000000000000000)
        self.bandwidthEdit.setValue(16.000000000000000)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.bandwidthEdit)

        self.labelCoverage = QLabel(IFEditorDialog)
        self.labelCoverage.setObjectName(u"labelCoverage")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelCoverage)

        self.coverageDisplay = QLabel(IFEditorDialog)
        self.coverageDisplay.setObjectName(u"coverageDisplay")
        self.coverageDisplay.setFrameShape(QFrame.Shape.Panel)
        self.coverageDisplay.setFrameShadow(QFrame.Shadow.Sunken)
        self.coverageDisplay.setIndent(1)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.coverageDisplay)

        self.labelIsActive = QLabel(IFEditorDialog)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(IFEditorDialog)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(4, QFormLayout.FieldRole, self.isActiveCheckBox)


        self.verticalLayout.addLayout(self.formLayout)

        self.line = QFrame(IFEditorDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.polarizationsColumn = QVBoxLayout()
        self.polarizationsColumn.setObjectName(u"polarizationsColumn")
        self.labelPolarizations = QLabel(IFEditorDialog)
        self.labelPolarizations.setObjectName(u"labelPolarizations")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(10)
        font.setBold(False)
        self.labelPolarizations.setFont(font)

        self.polarizationsColumn.addWidget(self.labelPolarizations)

        self.polarizationsList = QListWidget(IFEditorDialog)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        self.polarizationsList.setObjectName(u"polarizationsList")
        self.polarizationsList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.polarizationsColumn.addWidget(self.polarizationsList)


        self.horizontalLayout.addLayout(self.polarizationsColumn)

        self.sidebandsColumn = QVBoxLayout()
        self.sidebandsColumn.setObjectName(u"sidebandsColumn")
        self.labelSidebands = QLabel(IFEditorDialog)
        self.labelSidebands.setObjectName(u"labelSidebands")
        self.labelSidebands.setFont(font)

        self.sidebandsColumn.addWidget(self.labelSidebands)

        self.sidebandsList = QListWidget(IFEditorDialog)
        QListWidgetItem(self.sidebandsList)
        QListWidgetItem(self.sidebandsList)
        self.sidebandsList.setObjectName(u"sidebandsList")
        self.sidebandsList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.sidebandsColumn.addWidget(self.sidebandsList)


        self.horizontalLayout.addLayout(self.sidebandsColumn)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.line_2 = QFrame(IFEditorDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)

        self.polarizationsButtonLayout = QHBoxLayout()
        self.polarizationsButtonLayout.setObjectName(u"polarizationsButtonLayout")
        self.clearPolarizationsButton = QPushButton(IFEditorDialog)
        self.clearPolarizationsButton.setObjectName(u"clearPolarizationsButton")

        self.polarizationsButtonLayout.addWidget(self.clearPolarizationsButton)

        self.horizontalSpacerPolarizations = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.polarizationsButtonLayout.addItem(self.horizontalSpacerPolarizations)

        self.saveButton = QPushButton(IFEditorDialog)
        self.saveButton.setObjectName(u"saveButton")

        self.polarizationsButtonLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(IFEditorDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.polarizationsButtonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.polarizationsButtonLayout)


        self.retranslateUi(IFEditorDialog)
        self.saveButton.clicked.connect(IFEditorDialog.accept)
        self.cancelButton.clicked.connect(IFEditorDialog.reject)

        QMetaObject.connectSlotsByName(IFEditorDialog)
    # setupUi

    def retranslateUi(self, IFEditorDialog):
        IFEditorDialog.setWindowTitle(QCoreApplication.translate("IFEditorDialog", u"Frequency Editor", None))
        self.labelFrequency.setText(QCoreApplication.translate("IFEditorDialog", u"Frequency (MHz):", None))
        self.labelWavelength.setText(QCoreApplication.translate("IFEditorDialog", u"Wavelength (cm):", None))
        self.wavelengthDisplay.setText(QCoreApplication.translate("IFEditorDialog", u"29.979", None))
        self.labelBandwidth.setText(QCoreApplication.translate("IFEditorDialog", u"Bandwidth (MHz):", None))
        self.labelCoverage.setText(QCoreApplication.translate("IFEditorDialog", u"Covers (MHz):", None))
#if QT_CONFIG(tooltip)
        self.coverageDisplay.setToolTip(QCoreApplication.translate("IFEditorDialog", u"The spectrum this setting actually records. Two bands that cover the same span are the same spectrum written two ways, and the project will refuse the second", None))
#endif // QT_CONFIG(tooltip)
        self.coverageDisplay.setText(QCoreApplication.translate("IFEditorDialog", u"1000.000 - 1016.000", None))
        self.labelIsActive.setText(QCoreApplication.translate("IFEditorDialog", u"Active:", None))
        self.labelPolarizations.setText(QCoreApplication.translate("IFEditorDialog", u"<html><head/><body><p>Polarizations:</p></body></html>", None))

        __sortingEnabled = self.polarizationsList.isSortingEnabled()
        self.polarizationsList.setSortingEnabled(False)
        ___qlistwidgetitem = self.polarizationsList.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("IFEditorDialog", u"RCP", None));
        ___qlistwidgetitem1 = self.polarizationsList.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("IFEditorDialog", u"LCP", None));
        ___qlistwidgetitem2 = self.polarizationsList.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("IFEditorDialog", u"H", None));
        ___qlistwidgetitem3 = self.polarizationsList.item(3)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("IFEditorDialog", u"V", None));
        self.polarizationsList.setSortingEnabled(__sortingEnabled)

#if QT_CONFIG(tooltip)
        self.polarizationsList.setToolTip(QCoreApplication.translate("IFEditorDialog", u"Circular or linear, not both. Each one recorded in each sideband is a channel", None))
#endif // QT_CONFIG(tooltip)
        self.labelSidebands.setText(QCoreApplication.translate("IFEditorDialog", u"<html><head/><body><p>Sidebands:</p></body></html>", None))

        __sortingEnabled1 = self.sidebandsList.isSortingEnabled()
        self.sidebandsList.setSortingEnabled(False)
        ___qlistwidgetitem4 = self.sidebandsList.item(0)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("IFEditorDialog", u"U", None));
        ___qlistwidgetitem5 = self.sidebandsList.item(1)
        ___qlistwidgetitem5.setText(QCoreApplication.translate("IFEditorDialog", u"L", None));
        self.sidebandsList.setSortingEnabled(__sortingEnabled1)

#if QT_CONFIG(tooltip)
        self.sidebandsList.setToolTip(QCoreApplication.translate("IFEditorDialog", u"Which way the band runs from its sky frequency: U upwards, L downwards, both for a receiver that records either side", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.clearPolarizationsButton.setToolTip(QCoreApplication.translate("IFEditorDialog", u"Unselect every polarization and sideband", None))
#endif // QT_CONFIG(tooltip)
        self.clearPolarizationsButton.setText(QCoreApplication.translate("IFEditorDialog", u"Clear", None))
        self.saveButton.setText(QCoreApplication.translate("IFEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("IFEditorDialog", u"Cancel", None))
    # retranslateUi

