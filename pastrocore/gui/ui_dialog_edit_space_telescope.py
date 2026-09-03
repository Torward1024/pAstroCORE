# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_space_telescope.ui'
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
    QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTabWidget, QTableView, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_SpaceTelescopeEditorDialog(object):
    def setupUi(self, SpaceTelescopeEditorDialog):
        if not SpaceTelescopeEditorDialog.objectName():
            SpaceTelescopeEditorDialog.setObjectName(u"SpaceTelescopeEditorDialog")
        SpaceTelescopeEditorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        SpaceTelescopeEditorDialog.resize(440, 512)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SpaceTelescopeEditorDialog.sizePolicy().hasHeightForWidth())
        SpaceTelescopeEditorDialog.setSizePolicy(sizePolicy)
        SpaceTelescopeEditorDialog.setMinimumSize(QSize(440, 500))
        SpaceTelescopeEditorDialog.setMaximumSize(QSize(440, 512))
        icon = QIcon()
        icon.addFile(u":/icons/edit_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SpaceTelescopeEditorDialog.setWindowIcon(icon)
        SpaceTelescopeEditorDialog.setModal(True)
        self.gridLayout = QGridLayout(SpaceTelescopeEditorDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacerButtons = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacerButtons)

        self.saveButton = QPushButton(SpaceTelescopeEditorDialog)
        self.saveButton.setObjectName(u"saveButton")

        self.horizontalLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(SpaceTelescopeEditorDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout.addWidget(self.cancelButton)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 2, 1)

        self.tabWidget = QTabWidget(SpaceTelescopeEditorDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_3 = QGridLayout(self.tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelCode = QLabel(self.tab)
        self.labelCode.setObjectName(u"labelCode")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelCode)

        self.codeEdit = QLineEdit(self.tab)
        self.codeEdit.setObjectName(u"codeEdit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.codeEdit)

        self.labelName = QLabel(self.tab)
        self.labelName.setObjectName(u"labelName")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelName)

        self.nameEdit = QLineEdit(self.tab)
        self.nameEdit.setObjectName(u"nameEdit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameEdit)

        self.labelDiameter = QLabel(self.tab)
        self.labelDiameter.setObjectName(u"labelDiameter")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelDiameter)

        self.diameterEdit = QDoubleSpinBox(self.tab)
        self.diameterEdit.setObjectName(u"diameterEdit")
        self.diameterEdit.setDecimals(2)
        self.diameterEdit.setMinimum(1.000000000000000)
        self.diameterEdit.setMaximum(1000.000000000000000)
        self.diameterEdit.setValue(10.000000000000000)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.diameterEdit)

        self.labelSurfaceAccuracy = QLabel(self.tab)
        self.labelSurfaceAccuracy.setObjectName(u"labelSurfaceAccuracy")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelSurfaceAccuracy)

        self.surfaceAccuracyEdit = QDoubleSpinBox(self.tab)
        self.surfaceAccuracyEdit.setObjectName(u"surfaceAccuracyEdit")
        self.surfaceAccuracyEdit.setDecimals(2)
        self.surfaceAccuracyEdit.setMinimum(0.000000000000000)
        self.surfaceAccuracyEdit.setMaximum(10000.000000000000000)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.surfaceAccuracyEdit)

        self.labelOrbitFile = QLabel(self.tab)
        self.labelOrbitFile.setObjectName(u"labelOrbitFile")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.labelOrbitFile)

        self.orbitFileLayout = QHBoxLayout()
        self.orbitFileLayout.setObjectName(u"orbitFileLayout")
        self.orbitFileEdit = QLineEdit(self.tab)
        self.orbitFileEdit.setObjectName(u"orbitFileEdit")

        self.orbitFileLayout.addWidget(self.orbitFileEdit)

        self.browseOrbitFileButton = QPushButton(self.tab)
        self.browseOrbitFileButton.setObjectName(u"browseOrbitFileButton")

        self.orbitFileLayout.addWidget(self.browseOrbitFileButton)


        self.formLayout.setLayout(4, QFormLayout.FieldRole, self.orbitFileLayout)

        self.labelInterpolationMethod = QLabel(self.tab)
        self.labelInterpolationMethod.setObjectName(u"labelInterpolationMethod")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.labelInterpolationMethod)

        self.interpolationMethodCombo = QComboBox(self.tab)
        self.interpolationMethodCombo.addItem("")
        self.interpolationMethodCombo.addItem("")
        self.interpolationMethodCombo.addItem("")
        self.interpolationMethodCombo.setObjectName(u"interpolationMethodCombo")

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.interpolationMethodCombo)

        self.labelPitchRange = QLabel(self.tab)
        self.labelPitchRange.setObjectName(u"labelPitchRange")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.labelPitchRange)

        self.pitchRangeLayout = QHBoxLayout()
        self.pitchRangeLayout.setObjectName(u"pitchRangeLayout")
        self.pitchMinEdit = QDoubleSpinBox(self.tab)
        self.pitchMinEdit.setObjectName(u"pitchMinEdit")
        self.pitchMinEdit.setDecimals(2)
        self.pitchMinEdit.setMinimum(-90.000000000000000)
        self.pitchMinEdit.setMaximum(89.000000000000000)

        self.pitchRangeLayout.addWidget(self.pitchMinEdit)

        self.pitchMaxEdit = QDoubleSpinBox(self.tab)
        self.pitchMaxEdit.setObjectName(u"pitchMaxEdit")
        self.pitchMaxEdit.setDecimals(2)
        self.pitchMaxEdit.setMinimum(0.000000000000000)
        self.pitchMaxEdit.setMaximum(90.000000000000000)
        self.pitchMaxEdit.setValue(90.000000000000000)

        self.pitchRangeLayout.addWidget(self.pitchMaxEdit)


        self.formLayout.setLayout(6, QFormLayout.FieldRole, self.pitchRangeLayout)

        self.labelYawRange = QLabel(self.tab)
        self.labelYawRange.setObjectName(u"labelYawRange")

        self.formLayout.setWidget(7, QFormLayout.LabelRole, self.labelYawRange)

        self.yawRangeLayout = QHBoxLayout()
        self.yawRangeLayout.setObjectName(u"yawRangeLayout")
        self.yawMinEdit = QDoubleSpinBox(self.tab)
        self.yawMinEdit.setObjectName(u"yawMinEdit")
        self.yawMinEdit.setDecimals(2)
        self.yawMinEdit.setMinimum(-180.000000000000000)
        self.yawMinEdit.setMaximum(179.000000000000000)

        self.yawRangeLayout.addWidget(self.yawMinEdit)

        self.yawMaxEdit = QDoubleSpinBox(self.tab)
        self.yawMaxEdit.setObjectName(u"yawMaxEdit")
        self.yawMaxEdit.setDecimals(2)
        self.yawMaxEdit.setMinimum(0.000000000000000)
        self.yawMaxEdit.setMaximum(180.000000000000000)
        self.yawMaxEdit.setValue(90.000000000000000)

        self.yawRangeLayout.addWidget(self.yawMaxEdit)


        self.formLayout.setLayout(7, QFormLayout.FieldRole, self.yawRangeLayout)

        self.labelUseKep = QLabel(self.tab)
        self.labelUseKep.setObjectName(u"labelUseKep")

        self.formLayout.setWidget(8, QFormLayout.LabelRole, self.labelUseKep)

        self.useKepCheckBox = QCheckBox(self.tab)
        self.useKepCheckBox.setObjectName(u"useKepCheckBox")
        self.useKepCheckBox.setChecked(True)

        self.formLayout.setWidget(8, QFormLayout.FieldRole, self.useKepCheckBox)

        self.labelIsActive = QLabel(self.tab)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(9, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(self.tab)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(9, QFormLayout.FieldRole, self.isActiveCheckBox)


        self.gridLayout_3.addLayout(self.formLayout, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_5 = QGridLayout(self.tab_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_4 = QGridLayout()
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.labelArgp = QLabel(self.tab_2)
        self.labelArgp.setObjectName(u"labelArgp")

        self.gridLayout_4.addWidget(self.labelArgp, 4, 0, 1, 1)

        self.nuEdit = QDoubleSpinBox(self.tab_2)
        self.nuEdit.setObjectName(u"nuEdit")
        self.nuEdit.setDecimals(2)
        self.nuEdit.setMinimum(-360.000000000000000)
        self.nuEdit.setMaximum(360.000000000000000)

        self.gridLayout_4.addWidget(self.nuEdit, 5, 1, 1, 1)

        self.muEdit = QDoubleSpinBox(self.tab_2)
        self.muEdit.setObjectName(u"muEdit")
        self.muEdit.setDecimals(2)
        self.muEdit.setMinimum(0.010000000000000)
        self.muEdit.setMaximum(1000000000000000.000000000000000)
        self.muEdit.setValue(398600441800000.000000000000000)

        self.gridLayout_4.addWidget(self.muEdit, 7, 1, 1, 1)

        self.labelRaan = QLabel(self.tab_2)
        self.labelRaan.setObjectName(u"labelRaan")

        self.gridLayout_4.addWidget(self.labelRaan, 3, 0, 1, 1)

        self.epochEdit = QDateTimeEdit(self.tab_2)
        self.epochEdit.setObjectName(u"epochEdit")
        self.epochEdit.setCalendarPopup(True)

        self.gridLayout_4.addWidget(self.epochEdit, 6, 1, 1, 1)

        self.labelMu = QLabel(self.tab_2)
        self.labelMu.setObjectName(u"labelMu")

        self.gridLayout_4.addWidget(self.labelMu, 7, 0, 1, 1)

        self.labelEccentricity = QLabel(self.tab_2)
        self.labelEccentricity.setObjectName(u"labelEccentricity")

        self.gridLayout_4.addWidget(self.labelEccentricity, 1, 0, 1, 1)

        self.eccentricityEdit = QDoubleSpinBox(self.tab_2)
        self.eccentricityEdit.setObjectName(u"eccentricityEdit")
        self.eccentricityEdit.setDecimals(3)
        self.eccentricityEdit.setMinimum(0.000000000000000)
        self.eccentricityEdit.setMaximum(0.999000000000000)

        self.gridLayout_4.addWidget(self.eccentricityEdit, 1, 1, 1, 1)

        self.argpEdit = QDoubleSpinBox(self.tab_2)
        self.argpEdit.setObjectName(u"argpEdit")
        self.argpEdit.setDecimals(2)
        self.argpEdit.setMinimum(-360.000000000000000)
        self.argpEdit.setMaximum(360.000000000000000)

        self.gridLayout_4.addWidget(self.argpEdit, 4, 1, 1, 1)

        self.labelEpoch = QLabel(self.tab_2)
        self.labelEpoch.setObjectName(u"labelEpoch")

        self.gridLayout_4.addWidget(self.labelEpoch, 6, 0, 1, 1)

        self.inclinationEdit = QDoubleSpinBox(self.tab_2)
        self.inclinationEdit.setObjectName(u"inclinationEdit")
        self.inclinationEdit.setDecimals(2)
        self.inclinationEdit.setMinimum(-360.000000000000000)
        self.inclinationEdit.setMaximum(360.000000000000000)

        self.gridLayout_4.addWidget(self.inclinationEdit, 2, 1, 1, 1)

        self.labelNu = QLabel(self.tab_2)
        self.labelNu.setObjectName(u"labelNu")

        self.gridLayout_4.addWidget(self.labelNu, 5, 0, 1, 1)

        self.semiMajorAxisEdit = QDoubleSpinBox(self.tab_2)
        self.semiMajorAxisEdit.setObjectName(u"semiMajorAxisEdit")
        self.semiMajorAxisEdit.setDecimals(2)
        self.semiMajorAxisEdit.setMinimum(1.000000000000000)
        self.semiMajorAxisEdit.setMaximum(1000000000000.000000000000000)

        self.gridLayout_4.addWidget(self.semiMajorAxisEdit, 0, 1, 1, 1)

        self.labelInclination = QLabel(self.tab_2)
        self.labelInclination.setObjectName(u"labelInclination")

        self.gridLayout_4.addWidget(self.labelInclination, 2, 0, 1, 1)

        self.raanEdit = QDoubleSpinBox(self.tab_2)
        self.raanEdit.setObjectName(u"raanEdit")
        self.raanEdit.setDecimals(2)
        self.raanEdit.setMinimum(-10000000.000000000000000)
        self.raanEdit.setMaximum(10000000.000000000000000)

        self.gridLayout_4.addWidget(self.raanEdit, 3, 1, 1, 1)

        self.labelSemiMajorAxis = QLabel(self.tab_2)
        self.labelSemiMajorAxis.setObjectName(u"labelSemiMajorAxis")

        self.gridLayout_4.addWidget(self.labelSemiMajorAxis, 0, 0, 1, 1)


        self.gridLayout_5.addLayout(self.gridLayout_4, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.gridLayout_6 = QGridLayout(self.tab_4)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.line_4 = QFrame(self.tab_4)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_6.addWidget(self.line_4, 11, 0, 1, 2)

        self.systemTemperatureButtonLayout = QHBoxLayout()
        self.systemTemperatureButtonLayout.setObjectName(u"systemTemperatureButtonLayout")
        self.addSystemTemperatureButton = QPushButton(self.tab_4)
        self.addSystemTemperatureButton.setObjectName(u"addSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.addSystemTemperatureButton)

        self.removeSystemTemperatureButton = QPushButton(self.tab_4)
        self.removeSystemTemperatureButton.setObjectName(u"removeSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.removeSystemTemperatureButton)

        self.clearSystemTemperatureButton = QPushButton(self.tab_4)
        self.clearSystemTemperatureButton.setObjectName(u"clearSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.clearSystemTemperatureButton)

        self.horizontalSpacerSystemTemperature = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.systemTemperatureButtonLayout.addItem(self.horizontalSpacerSystemTemperature)


        self.gridLayout_6.addLayout(self.systemTemperatureButtonLayout, 14, 0, 1, 2)

        self.labelSefdTable = QLabel(self.tab_4)
        self.labelSefdTable.setObjectName(u"labelSefdTable")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        font.setBold(False)
        self.labelSefdTable.setFont(font)

        self.gridLayout_6.addWidget(self.labelSefdTable, 0, 0, 1, 2)

        self.effectiveAreaTable = QTableView(self.tab_4)
        self.effectiveAreaTable.setObjectName(u"effectiveAreaTable")
        self.effectiveAreaTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.effectiveAreaTable.setAlternatingRowColors(True)
        self.effectiveAreaTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.effectiveAreaTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_6.addWidget(self.effectiveAreaTable, 9, 0, 1, 2)

        self.surfaceEfficiencyButtonLayout = QHBoxLayout()
        self.surfaceEfficiencyButtonLayout.setObjectName(u"surfaceEfficiencyButtonLayout")
        self.addSurfaceEfficiencyButton = QPushButton(self.tab_4)
        self.addSurfaceEfficiencyButton.setObjectName(u"addSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.addSurfaceEfficiencyButton)

        self.removeSurfaceEfficiencyButton = QPushButton(self.tab_4)
        self.removeSurfaceEfficiencyButton.setObjectName(u"removeSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.removeSurfaceEfficiencyButton)

        self.clearSurfaceEfficiencyButton = QPushButton(self.tab_4)
        self.clearSurfaceEfficiencyButton.setObjectName(u"clearSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.clearSurfaceEfficiencyButton)

        self.horizontalSpacerSurfaceEfficiency = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.surfaceEfficiencyButtonLayout.addItem(self.horizontalSpacerSurfaceEfficiency)


        self.gridLayout_6.addLayout(self.surfaceEfficiencyButtonLayout, 6, 0, 1, 2)

        self.sefdTable = QTableView(self.tab_4)
        self.sefdTable.setObjectName(u"sefdTable")
        self.sefdTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.sefdTable.setAlternatingRowColors(True)
        self.sefdTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sefdTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_6.addWidget(self.sefdTable, 1, 0, 2, 2)

        self.surfaceEfficiencyTable = QTableView(self.tab_4)
        self.surfaceEfficiencyTable.setObjectName(u"surfaceEfficiencyTable")
        self.surfaceEfficiencyTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.surfaceEfficiencyTable.setAlternatingRowColors(True)
        self.surfaceEfficiencyTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.surfaceEfficiencyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_6.addWidget(self.surfaceEfficiencyTable, 5, 0, 1, 2)

        self.line_3 = QFrame(self.tab_4)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_6.addWidget(self.line_3, 7, 0, 1, 2)

        self.labelSurfaceEfficiencyTable = QLabel(self.tab_4)
        self.labelSurfaceEfficiencyTable.setObjectName(u"labelSurfaceEfficiencyTable")
        self.labelSurfaceEfficiencyTable.setFont(font)

        self.gridLayout_6.addWidget(self.labelSurfaceEfficiencyTable, 4, 0, 1, 2)

        self.systemTemperatureTable = QTableView(self.tab_4)
        self.systemTemperatureTable.setObjectName(u"systemTemperatureTable")
        self.systemTemperatureTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.systemTemperatureTable.setAlternatingRowColors(True)
        self.systemTemperatureTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.systemTemperatureTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_6.addWidget(self.systemTemperatureTable, 13, 0, 1, 2)

        self.effectiveAreaButtonLayout = QHBoxLayout()
        self.effectiveAreaButtonLayout.setObjectName(u"effectiveAreaButtonLayout")
        self.addEffectiveAreaButton = QPushButton(self.tab_4)
        self.addEffectiveAreaButton.setObjectName(u"addEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.addEffectiveAreaButton)

        self.removeEffectiveAreaButton = QPushButton(self.tab_4)
        self.removeEffectiveAreaButton.setObjectName(u"removeEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.removeEffectiveAreaButton)

        self.clearEffectiveAreaButton = QPushButton(self.tab_4)
        self.clearEffectiveAreaButton.setObjectName(u"clearEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.clearEffectiveAreaButton)

        self.horizontalSpacerEffectiveArea = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.effectiveAreaButtonLayout.addItem(self.horizontalSpacerEffectiveArea)


        self.gridLayout_6.addLayout(self.effectiveAreaButtonLayout, 10, 0, 1, 2)

        self.labelEffectiveAreaTable = QLabel(self.tab_4)
        self.labelEffectiveAreaTable.setObjectName(u"labelEffectiveAreaTable")
        self.labelEffectiveAreaTable.setFont(font)

        self.gridLayout_6.addWidget(self.labelEffectiveAreaTable, 8, 0, 1, 2)

        self.labelSystemTemperatureTable = QLabel(self.tab_4)
        self.labelSystemTemperatureTable.setObjectName(u"labelSystemTemperatureTable")
        self.labelSystemTemperatureTable.setFont(font)

        self.gridLayout_6.addWidget(self.labelSystemTemperatureTable, 12, 0, 1, 2)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.addSefdButton = QPushButton(self.tab_4)
        self.addSefdButton.setObjectName(u"addSefdButton")

        self.gridLayout_2.addWidget(self.addSefdButton, 0, 0, 1, 1)

        self.removeSefdButton = QPushButton(self.tab_4)
        self.removeSefdButton.setObjectName(u"removeSefdButton")

        self.gridLayout_2.addWidget(self.removeSefdButton, 0, 1, 1, 1)

        self.clearSefdButton = QPushButton(self.tab_4)
        self.clearSefdButton.setObjectName(u"clearSefdButton")

        self.gridLayout_2.addWidget(self.clearSefdButton, 0, 2, 1, 1)

        self.horizontalSpacerSefd = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacerSefd, 0, 3, 1, 1)


        self.gridLayout_6.addLayout(self.gridLayout_2, 3, 0, 1, 1)

        self.tabWidget.addTab(self.tab_4, "")

        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)

        self.line = QFrame(SpaceTelescopeEditorDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)


        self.retranslateUi(SpaceTelescopeEditorDialog)
        self.saveButton.clicked.connect(SpaceTelescopeEditorDialog.accept)
        self.cancelButton.clicked.connect(SpaceTelescopeEditorDialog.reject)
        self.useKepCheckBox.toggled.connect(self.orbitFileEdit.setDisabled)
        self.useKepCheckBox.toggled.connect(self.browseOrbitFileButton.setDisabled)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(SpaceTelescopeEditorDialog)
    # setupUi

    def retranslateUi(self, SpaceTelescopeEditorDialog):
        SpaceTelescopeEditorDialog.setWindowTitle(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Space Telescope Editor", None))
        self.saveButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Cancel", None))
        self.labelCode.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Code:", None))
        self.codeEdit.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"ST", None))
        self.codeEdit.setPlaceholderText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Enter telescope code", None))
        self.labelName.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Name:", None))
        self.nameEdit.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"SPACETELESCOPE", None))
        self.nameEdit.setPlaceholderText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Enter telescope name", None))
        self.labelDiameter.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Diameter (m):", None))
        self.labelSurfaceAccuracy.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Surface Accuracy (\u00b5m):", None))
        self.surfaceAccuracyEdit.setSpecialValueText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"None", None))
        self.labelOrbitFile.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Orbit File:", None))
        self.orbitFileEdit.setPlaceholderText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Enter orbit file path", None))
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
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Main Parameters", None))
        self.labelArgp.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Arg. of Perigee (deg):", None))
        self.labelRaan.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"RAAN (deg):", None))
        self.labelMu.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Gravitational Parameter (m\u00b3/s\u00b2):", None))
        self.labelEccentricity.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Eccentricity:", None))
        self.labelEpoch.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Epoch (UTC):", None))
        self.labelNu.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"True Anomaly (deg):", None))
        self.labelInclination.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Inclination (deg):", None))
        self.labelSemiMajorAxis.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Semi-Major Axis (m):", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Keplerian Elements", None))
        self.addSystemTemperatureButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add", None))
        self.removeSystemTemperatureButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove", None))
        self.clearSystemTemperatureButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear", None))
        self.labelSefdTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"SEFD Table (MHz, Jy):", None))
        self.addSurfaceEfficiencyButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add", None))
        self.removeSurfaceEfficiencyButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove", None))
        self.clearSurfaceEfficiencyButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear", None))
        self.labelSurfaceEfficiencyTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Surface Efficiency Table (MHz, Efficiency):", None))
        self.addEffectiveAreaButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add", None))
        self.removeEffectiveAreaButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove", None))
        self.clearEffectiveAreaButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear", None))
        self.labelEffectiveAreaTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Effective Area Table (MHz, m\u00b2):", None))
        self.labelSystemTemperatureTable.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"<html><head/><body><p>System Temperature Table (MHz, K):</p></body></html>", None))
        self.addSefdButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Add", None))
        self.removeSefdButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Remove", None))
        self.clearSefdButton.setText(QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Clear", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("SpaceTelescopeEditorDialog", u"Sensitivity", None))
    # retranslateUi

