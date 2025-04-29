# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_space_telescopeJFZEgz.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDateTimeEdit, QDialog, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTableView, QVBoxLayout, QWidget)

class Ui_SpaceTelescopeEditorDialog(object):
    def setupUi(self, SpaceTelescopeEditorDialog):
        if not SpaceTelescopeEditorDialog.objectName():
            SpaceTelescopeEditorDialog.setObjectName(u"SpaceTelescopeEditorDialog")
        SpaceTelescopeEditorDialog.resize(595, 1218)
        self.verticalLayout = QVBoxLayout(SpaceTelescopeEditorDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelCode = QLabel(SpaceTelescopeEditorDialog)
        self.labelCode.setObjectName(u"labelCode")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelCode)

        self.codeEdit = QLineEdit(SpaceTelescopeEditorDialog)
        self.codeEdit.setObjectName(u"codeEdit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.codeEdit)

        self.labelName = QLabel(SpaceTelescopeEditorDialog)
        self.labelName.setObjectName(u"labelName")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelName)

        self.nameEdit = QLineEdit(SpaceTelescopeEditorDialog)
        self.nameEdit.setObjectName(u"nameEdit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameEdit)

        self.labelDiameter = QLabel(SpaceTelescopeEditorDialog)
        self.labelDiameter.setObjectName(u"labelDiameter")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelDiameter)

        self.diameterEdit = QDoubleSpinBox(SpaceTelescopeEditorDialog)
        self.diameterEdit.setObjectName(u"diameterEdit")
        self.diameterEdit.setDecimals(2)
        self.diameterEdit.setMinimum(0.010000000000000)
        self.diameterEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.diameterEdit)

        self.labelSurfaceAccuracy = QLabel(SpaceTelescopeEditorDialog)
        self.labelSurfaceAccuracy.setObjectName(u"labelSurfaceAccuracy")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelSurfaceAccuracy)

        self.surfaceAccuracyEdit = QDoubleSpinBox(SpaceTelescopeEditorDialog)
        self.surfaceAccuracyEdit.setObjectName(u"surfaceAccuracyEdit")
        self.surfaceAccuracyEdit.setDecimals(2)
        self.surfaceAccuracyEdit.setMinimum(0.000000000000000)
        self.surfaceAccuracyEdit.setMaximum(10000.000000000000000)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.surfaceAccuracyEdit)

        self.labelOrbitFile = QLabel(SpaceTelescopeEditorDialog)
        self.labelOrbitFile.setObjectName(u"labelOrbitFile")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.labelOrbitFile)

        self.orbitFileLayout = QHBoxLayout()
        self.orbitFileLayout.setObjectName(u"orbitFileLayout")
        self.orbitFileEdit = QLineEdit(SpaceTelescopeEditorDialog)
        self.orbitFileEdit.setObjectName(u"orbitFileEdit")

        self.orbitFileLayout.addWidget(self.orbitFileEdit)

        self.browseOrbitFileButton = QPushButton(SpaceTelescopeEditorDialog)
        self.browseOrbitFileButton.setObjectName(u"browseOrbitFileButton")

        self.orbitFileLayout.addWidget(self.browseOrbitFileButton)


        self.formLayout.setLayout(4, QFormLayout.FieldRole, self.orbitFileLayout)

        self.labelInterpolationMethod = QLabel(SpaceTelescopeEditorDialog)
        self.labelInterpolationMethod.setObjectName(u"labelInterpolationMethod")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.labelInterpolationMethod)

        self.interpolationMethodCombo = QComboBox(SpaceTelescopeEditorDialog)
        self.interpolationMethodCombo.addItem("")
        self.interpolationMethodCombo.addItem("")
        self.interpolationMethodCombo.addItem("")
        self.interpolationMethodCombo.setObjectName(u"interpolationMethodCombo")

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.interpolationMethodCombo)

        self.labelPitchRange = QLabel(SpaceTelescopeEditorDialog)
        self.labelPitchRange.setObjectName(u"labelPitchRange")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.labelPitchRange)

        self.pitchRangeLayout = QHBoxLayout()
        self.pitchRangeLayout.setObjectName(u"pitchRangeLayout")
        self.pitchMinEdit = QDoubleSpinBox(SpaceTelescopeEditorDialog)
        self.pitchMinEdit.setObjectName(u"pitchMinEdit")
        self.pitchMinEdit.setDecimals(2)
        self.pitchMinEdit.setMinimum(-90.000000000000000)
        self.pitchMinEdit.setMaximum(90.000000000000000)

        self.pitchRangeLayout.addWidget(self.pitchMinEdit)

        self.pitchMaxEdit = QDoubleSpinBox(SpaceTelescopeEditorDialog)
        self.pitchMaxEdit.setObjectName(u"pitchMaxEdit")
        self.pitchMaxEdit.setDecimals(2)
        self.pitchMaxEdit.setMinimum(-90.000000000000000)
        self.pitchMaxEdit.setMaximum(90.000000000000000)

        self.pitchRangeLayout.addWidget(self.pitchMaxEdit)


        self.formLayout.setLayout(6, QFormLayout.FieldRole, self.pitchRangeLayout)

        self.labelYawRange = QLabel(SpaceTelescopeEditorDialog)
        self.labelYawRange.setObjectName(u"labelYawRange")

        self.formLayout.setWidget(7, QFormLayout.LabelRole, self.labelYawRange)

        self.yawRangeLayout = QHBoxLayout()
        self.yawRangeLayout.setObjectName(u"yawRangeLayout")
        self.yawMinEdit = QDoubleSpinBox(SpaceTelescopeEditorDialog)
        self.yawMinEdit.setObjectName(u"yawMinEdit")
        self.yawMinEdit.setDecimals(2)
        self.yawMinEdit.setMinimum(-180.000000000000000)
        self.yawMinEdit.setMaximum(180.000000000000000)

        self.yawRangeLayout.addWidget(self.yawMinEdit)

        self.yawMaxEdit = QDoubleSpinBox(SpaceTelescopeEditorDialog)
        self.yawMaxEdit.setObjectName(u"yawMaxEdit")
        self.yawMaxEdit.setDecimals(2)
        self.yawMaxEdit.setMinimum(-180.000000000000000)
        self.yawMaxEdit.setMaximum(180.000000000000000)

        self.yawRangeLayout.addWidget(self.yawMaxEdit)


        self.formLayout.setLayout(7, QFormLayout.FieldRole, self.yawRangeLayout)

        self.labelUseKep = QLabel(SpaceTelescopeEditorDialog)
        self.labelUseKep.setObjectName(u"labelUseKep")

        self.formLayout.setWidget(8, QFormLayout.LabelRole, self.labelUseKep)

        self.useKepCheckBox = QCheckBox(SpaceTelescopeEditorDialog)
        self.useKepCheckBox.setObjectName(u"useKepCheckBox")
        self.useKepCheckBox.setChecked(True)

        self.formLayout.setWidget(8, QFormLayout.FieldRole, self.useKepCheckBox)

        self.labelIsActive = QLabel(SpaceTelescopeEditorDialog)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(9, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(SpaceTelescopeEditorDialog)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(9, QFormLayout.FieldRole, self.isActiveCheckBox)


        self.verticalLayout.addLayout(self.formLayout)

        self.keplerGroupBox = QGroupBox(SpaceTelescopeEditorDialog)
        self.keplerGroupBox.setObjectName(u"keplerGroupBox")
        self.keplerFormLayout = QFormLayout(self.keplerGroupBox)
        self.keplerFormLayout.setObjectName(u"keplerFormLayout")
        self.labelSemiMajorAxis = QLabel(self.keplerGroupBox)
        self.labelSemiMajorAxis.setObjectName(u"labelSemiMajorAxis")

        self.keplerFormLayout.setWidget(0, QFormLayout.LabelRole, self.labelSemiMajorAxis)

        self.semiMajorAxisEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.semiMajorAxisEdit.setObjectName(u"semiMajorAxisEdit")
        self.semiMajorAxisEdit.setDecimals(2)
        self.semiMajorAxisEdit.setMinimum(0.010000000000000)
        self.semiMajorAxisEdit.setMaximum(1000000000.000000000000000)

        self.keplerFormLayout.setWidget(0, QFormLayout.FieldRole, self.semiMajorAxisEdit)

        self.labelEccentricity = QLabel(self.keplerGroupBox)
        self.labelEccentricity.setObjectName(u"labelEccentricity")

        self.keplerFormLayout.setWidget(1, QFormLayout.LabelRole, self.labelEccentricity)

        self.eccentricityEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.eccentricityEdit.setObjectName(u"eccentricityEdit")
        self.eccentricityEdit.setDecimals(3)
        self.eccentricityEdit.setMinimum(0.000000000000000)
        self.eccentricityEdit.setMaximum(0.999000000000000)

        self.keplerFormLayout.setWidget(1, QFormLayout.FieldRole, self.eccentricityEdit)

        self.labelInclination = QLabel(self.keplerGroupBox)
        self.labelInclination.setObjectName(u"labelInclination")

        self.keplerFormLayout.setWidget(2, QFormLayout.LabelRole, self.labelInclination)

        self.inclinationEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.inclinationEdit.setObjectName(u"inclinationEdit")
        self.inclinationEdit.setDecimals(2)
        self.inclinationEdit.setMinimum(0.000000000000000)
        self.inclinationEdit.setMaximum(180.000000000000000)

        self.keplerFormLayout.setWidget(2, QFormLayout.FieldRole, self.inclinationEdit)

        self.labelRaan = QLabel(self.keplerGroupBox)
        self.labelRaan.setObjectName(u"labelRaan")

        self.keplerFormLayout.setWidget(3, QFormLayout.LabelRole, self.labelRaan)

        self.raanEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.raanEdit.setObjectName(u"raanEdit")
        self.raanEdit.setDecimals(2)
        self.raanEdit.setMinimum(0.000000000000000)
        self.raanEdit.setMaximum(360.000000000000000)

        self.keplerFormLayout.setWidget(3, QFormLayout.FieldRole, self.raanEdit)

        self.labelArgp = QLabel(self.keplerGroupBox)
        self.labelArgp.setObjectName(u"labelArgp")

        self.keplerFormLayout.setWidget(4, QFormLayout.LabelRole, self.labelArgp)

        self.argpEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.argpEdit.setObjectName(u"argpEdit")
        self.argpEdit.setDecimals(2)
        self.argpEdit.setMinimum(0.000000000000000)
        self.argpEdit.setMaximum(360.000000000000000)

        self.keplerFormLayout.setWidget(4, QFormLayout.FieldRole, self.argpEdit)

        self.labelNu = QLabel(self.keplerGroupBox)
        self.labelNu.setObjectName(u"labelNu")

        self.keplerFormLayout.setWidget(5, QFormLayout.LabelRole, self.labelNu)

        self.nuEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.nuEdit.setObjectName(u"nuEdit")
        self.nuEdit.setDecimals(2)
        self.nuEdit.setMinimum(0.000000000000000)
        self.nuEdit.setMaximum(360.000000000000000)

        self.keplerFormLayout.setWidget(5, QFormLayout.FieldRole, self.nuEdit)

        self.labelEpoch = QLabel(self.keplerGroupBox)
        self.labelEpoch.setObjectName(u"labelEpoch")

        self.keplerFormLayout.setWidget(6, QFormLayout.LabelRole, self.labelEpoch)

        self.epochEdit = QDateTimeEdit(self.keplerGroupBox)
        self.epochEdit.setObjectName(u"epochEdit")
        self.epochEdit.setCalendarPopup(True)

        self.keplerFormLayout.setWidget(6, QFormLayout.FieldRole, self.epochEdit)

        self.labelMu = QLabel(self.keplerGroupBox)
        self.labelMu.setObjectName(u"labelMu")

        self.keplerFormLayout.setWidget(7, QFormLayout.LabelRole, self.labelMu)

        self.muEdit = QDoubleSpinBox(self.keplerGroupBox)
        self.muEdit.setObjectName(u"muEdit")
        self.muEdit.setDecimals(2)
        self.muEdit.setMinimum(0.010000000000000)
        self.muEdit.setMaximum(1000000000000000.000000000000000)
        self.muEdit.setValue(398600441800000.000000000000000)

        self.keplerFormLayout.setWidget(7, QFormLayout.FieldRole, self.muEdit)


        self.verticalLayout.addWidget(self.keplerGroupBox)

        self.labelSefdTable = QLabel(SpaceTelescopeEditorDialog)
        self.labelSefdTable.setObjectName(u"labelSefdTable")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(10)
        font.setBold(True)
        self.labelSefdTable.setFont(font)

        self.verticalLayout.addWidget(self.labelSefdTable)

        self.sefdTable = QTableView(SpaceTelescopeEditorDialog)
        self.sefdTable.setObjectName(u"sefdTable")
        self.sefdTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.sefdTable.setAlternatingRowColors(True)
        self.sefdTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sefdTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.sefdTable)

        self.sefdButtonLayout = QHBoxLayout()
        self.sefdButtonLayout.setObjectName(u"sefdButtonLayout")
        self.addSefdButton = QPushButton(SpaceTelescopeEditorDialog)
        self.addSefdButton.setObjectName(u"addSefdButton")

        self.sefdButtonLayout.addWidget(self.addSefdButton)

        self.removeSefdButton = QPushButton(SpaceTelescopeEditorDialog)
        self.removeSefdButton.setObjectName(u"removeSefdButton")

        self.sefdButtonLayout.addWidget(self.removeSefdButton)

        self.clearSefdButton = QPushButton(SpaceTelescopeEditorDialog)
        self.clearSefdButton.setObjectName(u"clearSefdButton")

        self.sefdButtonLayout.addWidget(self.clearSefdButton)

        self.horizontalSpacerSefd = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sefdButtonLayout.addItem(self.horizontalSpacerSefd)


        self.verticalLayout.addLayout(self.sefdButtonLayout)

        self.labelSurfaceEfficiencyTable = QLabel(SpaceTelescopeEditorDialog)
        self.labelSurfaceEfficiencyTable.setObjectName(u"labelSurfaceEfficiencyTable")
        self.labelSurfaceEfficiencyTable.setFont(font)

        self.verticalLayout.addWidget(self.labelSurfaceEfficiencyTable)

        self.surfaceEfficiencyTable = QTableView(SpaceTelescopeEditorDialog)
        self.surfaceEfficiencyTable.setObjectName(u"surfaceEfficiencyTable")
        self.surfaceEfficiencyTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.surfaceEfficiencyTable.setAlternatingRowColors(True)
        self.surfaceEfficiencyTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.surfaceEfficiencyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.surfaceEfficiencyTable)

        self.surfaceEfficiencyButtonLayout = QHBoxLayout()
        self.surfaceEfficiencyButtonLayout.setObjectName(u"surfaceEfficiencyButtonLayout")
        self.addSurfaceEfficiencyButton = QPushButton(SpaceTelescopeEditorDialog)
        self.addSurfaceEfficiencyButton.setObjectName(u"addSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.addSurfaceEfficiencyButton)

        self.removeSurfaceEfficiencyButton = QPushButton(SpaceTelescopeEditorDialog)
        self.removeSurfaceEfficiencyButton.setObjectName(u"removeSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.removeSurfaceEfficiencyButton)

        self.clearSurfaceEfficiencyButton = QPushButton(SpaceTelescopeEditorDialog)
        self.clearSurfaceEfficiencyButton.setObjectName(u"clearSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.clearSurfaceEfficiencyButton)

        self.horizontalSpacerSurfaceEfficiency = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.surfaceEfficiencyButtonLayout.addItem(self.horizontalSpacerSurfaceEfficiency)


        self.verticalLayout.addLayout(self.surfaceEfficiencyButtonLayout)

        self.labelEffectiveAreaTable = QLabel(SpaceTelescopeEditorDialog)
        self.labelEffectiveAreaTable.setObjectName(u"labelEffectiveAreaTable")
        self.labelEffectiveAreaTable.setFont(font)

        self.verticalLayout.addWidget(self.labelEffectiveAreaTable)

        self.effectiveAreaTable = QTableView(SpaceTelescopeEditorDialog)
        self.effectiveAreaTable.setObjectName(u"effectiveAreaTable")
        self.effectiveAreaTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.effectiveAreaTable.setAlternatingRowColors(True)
        self.effectiveAreaTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.effectiveAreaTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.effectiveAreaTable)

        self.effectiveAreaButtonLayout = QHBoxLayout()
        self.effectiveAreaButtonLayout.setObjectName(u"effectiveAreaButtonLayout")
        self.addEffectiveAreaButton = QPushButton(SpaceTelescopeEditorDialog)
        self.addEffectiveAreaButton.setObjectName(u"addEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.addEffectiveAreaButton)

        self.removeEffectiveAreaButton = QPushButton(SpaceTelescopeEditorDialog)
        self.removeEffectiveAreaButton.setObjectName(u"removeEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.removeEffectiveAreaButton)

        self.clearEffectiveAreaButton = QPushButton(SpaceTelescopeEditorDialog)
        self.clearEffectiveAreaButton.setObjectName(u"clearEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.clearEffectiveAreaButton)

        self.horizontalSpacerEffectiveArea = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.effectiveAreaButtonLayout.addItem(self.horizontalSpacerEffectiveArea)


        self.verticalLayout.addLayout(self.effectiveAreaButtonLayout)

        self.labelSystemTemperatureTable = QLabel(SpaceTelescopeEditorDialog)
        self.labelSystemTemperatureTable.setObjectName(u"labelSystemTemperatureTable")
        self.labelSystemTemperatureTable.setFont(font)

        self.verticalLayout.addWidget(self.labelSystemTemperatureTable)

        self.systemTemperatureTable = QTableView(SpaceTelescopeEditorDialog)
        self.systemTemperatureTable.setObjectName(u"systemTemperatureTable")
        self.systemTemperatureTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.systemTemperatureTable.setAlternatingRowColors(True)
        self.systemTemperatureTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.systemTemperatureTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.systemTemperatureTable)

        self.systemTemperatureButtonLayout = QHBoxLayout()
        self.systemTemperatureButtonLayout.setObjectName(u"systemTemperatureButtonLayout")
        self.addSystemTemperatureButton = QPushButton(SpaceTelescopeEditorDialog)
        self.addSystemTemperatureButton.setObjectName(u"addSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.addSystemTemperatureButton)

        self.removeSystemTemperatureButton = QPushButton(SpaceTelescopeEditorDialog)
        self.removeSystemTemperatureButton.setObjectName(u"removeSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.removeSystemTemperatureButton)

        self.clearSystemTemperatureButton = QPushButton(SpaceTelescopeEditorDialog)
        self.clearSystemTemperatureButton.setObjectName(u"clearSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.clearSystemTemperatureButton)

        self.horizontalSpacerSystemTemperature = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.systemTemperatureButtonLayout.addItem(self.horizontalSpacerSystemTemperature)


        self.verticalLayout.addLayout(self.systemTemperatureButtonLayout)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacerButtons = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacerButtons)

        self.saveButton = QPushButton(SpaceTelescopeEditorDialog)
        self.saveButton.setObjectName(u"saveButton")

        self.buttonLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(SpaceTelescopeEditorDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.buttonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(SpaceTelescopeEditorDialog)
        self.saveButton.clicked.connect(SpaceTelescopeEditorDialog.accept)
        self.cancelButton.clicked.connect(SpaceTelescopeEditorDialog.reject)
        self.useKepCheckBox.toggled.connect(self.keplerGroupBox.setEnabled)
        self.useKepCheckBox.toggled.connect(self.orbitFileEdit.setDisabled)
        self.useKepCheckBox.toggled.connect(self.browseOrbitFileButton.setDisabled)

        QMetaObject.connectSlotsByName(SpaceTelescopeEditorDialog)
    # setupUi

    def retranslateUi(self, SpaceTelescopeEditorDialog):
        SpaceTelescopeEditorDialog.setWindowTitle(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Edit Space Telescope", None))
        SpaceTelescopeEditorDialog.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelCode.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Code:", None))
        self.codeEdit.setPlaceholderText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Enter telescope code", None))
        self.labelName.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Name:", None))
        self.nameEdit.setPlaceholderText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Enter telescope name", None))
        self.labelDiameter.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Diameter (m):", None))
        self.labelSurfaceAccuracy.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Surface Accuracy (\u00b5m):", None))
        self.surfaceAccuracyEdit.setSpecialValueText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"None", None))
        self.labelOrbitFile.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Orbit File:", None))
        self.orbitFileEdit.setPlaceholderText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Enter orbit file path", None))
        self.browseOrbitFileButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.browseOrbitFileButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Browse", None))
        self.labelInterpolationMethod.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Interpolation Method:", None))
        self.interpolationMethodCombo.setItemText(0, QCoreApplication.translate("SpaceTelescopeEditorDialog", u"linear", None))
        self.interpolationMethodCombo.setItemText(1, QCoreApplication.translate("SpaceTelescopeEditorDialog", u"chebyshev", None))
        self.interpolationMethodCombo.setItemText(2, QCoreApplication.translate("SpaceTelescopeEditorDialog", u"cubic_spline", None))

        self.labelPitchRange.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Pitch Range (deg):", None))
        self.pitchMinEdit.setSuffix(QCoreApplication.translate("SpaceTelescopeEditorDialog", u" deg", None))
        self.pitchMaxEdit.setSuffix(QCoreApplication.translate("SpaceTelescopeEditorDialog", u" deg", None))
        self.labelYawRange.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Yaw Range (deg):", None))
        self.yawMinEdit.setSuffix(QCoreApplication.translate("SpaceTelescopeEditorDialog", u" deg", None))
        self.yawMaxEdit.setSuffix(QCoreApplication.translate("SpaceTelescopeEditorDialog", u" deg", None))
        self.labelUseKep.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Use Keplerian Elements:", None))
        self.labelIsActive.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Active:", None))
        self.keplerGroupBox.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"border: 1px solid #d3d3d3; padding: 10px;", None))
        self.keplerGroupBox.setTitle(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Keplerian Elements", None))
        self.labelSemiMajorAxis.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Semi-Major Axis (m):", None))
        self.labelEccentricity.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Eccentricity:", None))
        self.labelInclination.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Inclination (deg):", None))
        self.labelRaan.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"RAAN (deg):", None))
        self.labelArgp.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Arg. of Perigee (deg):", None))
        self.labelNu.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"True Anomaly (deg):", None))
        self.labelEpoch.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Epoch (UTC):", None))
        self.labelMu.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Gravitational Parameter (m\u00b3/s\u00b2):", None))
        self.labelSefdTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"SEFD Table (MHz, Jy):", None))
        self.sefdTable.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addSefdButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addSefdButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add SEFD", None))
        self.removeSefdButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeSefdButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove SEFD", None))
        self.clearSefdButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearSefdButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear SEFD Table", None))
        self.labelSurfaceEfficiencyTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Surface Efficiency Table (MHz, Efficiency):", None))
        self.surfaceEfficiencyTable.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addSurfaceEfficiencyButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addSurfaceEfficiencyButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add Efficiency", None))
        self.removeSurfaceEfficiencyButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeSurfaceEfficiencyButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove Efficiency", None))
        self.clearSurfaceEfficiencyButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearSurfaceEfficiencyButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear Efficiency Table", None))
        self.labelEffectiveAreaTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Effective Area Table (MHz, m\u00b2):", None))
        self.effectiveAreaTable.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addEffectiveAreaButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addEffectiveAreaButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add Area", None))
        self.removeEffectiveAreaButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeEffectiveAreaButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove Area", None))
        self.clearEffectiveAreaButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearEffectiveAreaButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear Area Table", None))
        self.labelSystemTemperatureTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"System Temperature Table (MHz, K):", None))
        self.systemTemperatureTable.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addSystemTemperatureButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addSystemTemperatureButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add Temperature", None))
        self.removeSystemTemperatureButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeSystemTemperatureButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove Temperature", None))
        self.clearSystemTemperatureButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearSystemTemperatureButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear Temperature Table", None))
        self.saveButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.saveButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Save", None))
        self.cancelButton.setStyleSheet(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"background-color: #6c757d; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.cancelButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Cancel", None))
    # retranslateUi