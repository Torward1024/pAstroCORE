# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_telescope.ui'
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
    QDialog, QDoubleSpinBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QTableView, QVBoxLayout, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_TelescopeEditorDialog(object):
    def setupUi(self, TelescopeEditorDialog):
        if not TelescopeEditorDialog.objectName():
            TelescopeEditorDialog.setObjectName(u"TelescopeEditorDialog")
        TelescopeEditorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        TelescopeEditorDialog.resize(460, 590)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(TelescopeEditorDialog.sizePolicy().hasHeightForWidth())
        TelescopeEditorDialog.setSizePolicy(sizePolicy)
        icon = QIcon()
        icon.addFile(u":/icons/edit_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        TelescopeEditorDialog.setWindowIcon(icon)
        TelescopeEditorDialog.setModal(True)
        self.gridLayout_2 = QGridLayout(TelescopeEditorDialog)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.tabWidget = QTabWidget(TelescopeEditorDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.mainParametersLayout = QVBoxLayout(self.tab)
        self.mainParametersLayout.setObjectName(u"mainParametersLayout")
        self.groupIdentity = QGroupBox(self.tab)
        self.groupIdentity.setObjectName(u"groupIdentity")
        self.gridIdentity = QGridLayout(self.groupIdentity)
        self.gridIdentity.setObjectName(u"gridIdentity")
        self.labelCode = QLabel(self.groupIdentity)
        self.labelCode.setObjectName(u"labelCode")

        self.gridIdentity.addWidget(self.labelCode, 0, 0, 1, 1)

        self.codeEdit = QLineEdit(self.groupIdentity)
        self.codeEdit.setObjectName(u"codeEdit")

        self.gridIdentity.addWidget(self.codeEdit, 0, 1, 1, 1)

        self.labelMountType = QLabel(self.groupIdentity)
        self.labelMountType.setObjectName(u"labelMountType")

        self.gridIdentity.addWidget(self.labelMountType, 0, 2, 1, 1)

        self.mountTypeCombo = QComboBox(self.groupIdentity)
        self.mountTypeCombo.addItem("")
        self.mountTypeCombo.addItem("")
        self.mountTypeCombo.setObjectName(u"mountTypeCombo")

        self.gridIdentity.addWidget(self.mountTypeCombo, 0, 3, 1, 1)

        self.labelName = QLabel(self.groupIdentity)
        self.labelName.setObjectName(u"labelName")

        self.gridIdentity.addWidget(self.labelName, 1, 0, 1, 1)

        self.nameEdit = QLineEdit(self.groupIdentity)
        self.nameEdit.setObjectName(u"nameEdit")

        self.gridIdentity.addWidget(self.nameEdit, 1, 1, 1, 3)


        self.mainParametersLayout.addWidget(self.groupIdentity)

        self.groupPosition = QGroupBox(self.tab)
        self.groupPosition.setObjectName(u"groupPosition")
        self.gridPosition = QGridLayout(self.groupPosition)
        self.gridPosition.setObjectName(u"gridPosition")
        self.labelX = QLabel(self.groupPosition)
        self.labelX.setObjectName(u"labelX")

        self.gridPosition.addWidget(self.labelX, 0, 0, 1, 1)

        self.xEdit = QDoubleSpinBox(self.groupPosition)
        self.xEdit.setObjectName(u"xEdit")
        self.xEdit.setDecimals(5)
        self.xEdit.setMinimum(-100000000.000000000000000)
        self.xEdit.setMaximum(100000000.000000000000000)

        self.gridPosition.addWidget(self.xEdit, 0, 1, 1, 1)

        self.labelVx = QLabel(self.groupPosition)
        self.labelVx.setObjectName(u"labelVx")

        self.gridPosition.addWidget(self.labelVx, 0, 2, 1, 1)

        self.vxEdit = QDoubleSpinBox(self.groupPosition)
        self.vxEdit.setObjectName(u"vxEdit")
        self.vxEdit.setDecimals(6)
        self.vxEdit.setMinimum(-1000.000000000000000)
        self.vxEdit.setMaximum(1000.000000000000000)

        self.gridPosition.addWidget(self.vxEdit, 0, 3, 1, 1)

        self.labelY = QLabel(self.groupPosition)
        self.labelY.setObjectName(u"labelY")

        self.gridPosition.addWidget(self.labelY, 1, 0, 1, 1)

        self.yEdit = QDoubleSpinBox(self.groupPosition)
        self.yEdit.setObjectName(u"yEdit")
        self.yEdit.setDecimals(5)
        self.yEdit.setMinimum(-100000000.000000000000000)
        self.yEdit.setMaximum(100000000.000000000000000)

        self.gridPosition.addWidget(self.yEdit, 1, 1, 1, 1)

        self.labelVy = QLabel(self.groupPosition)
        self.labelVy.setObjectName(u"labelVy")

        self.gridPosition.addWidget(self.labelVy, 1, 2, 1, 1)

        self.vyEdit = QDoubleSpinBox(self.groupPosition)
        self.vyEdit.setObjectName(u"vyEdit")
        self.vyEdit.setDecimals(6)
        self.vyEdit.setMinimum(-1000.000000000000000)
        self.vyEdit.setMaximum(1000.000000000000000)

        self.gridPosition.addWidget(self.vyEdit, 1, 3, 1, 1)

        self.labelZ = QLabel(self.groupPosition)
        self.labelZ.setObjectName(u"labelZ")

        self.gridPosition.addWidget(self.labelZ, 2, 0, 1, 1)

        self.zEdit = QDoubleSpinBox(self.groupPosition)
        self.zEdit.setObjectName(u"zEdit")
        self.zEdit.setDecimals(5)
        self.zEdit.setMinimum(-100000000.000000000000000)
        self.zEdit.setMaximum(100000000.000000000000000)

        self.gridPosition.addWidget(self.zEdit, 2, 1, 1, 1)

        self.labelVz = QLabel(self.groupPosition)
        self.labelVz.setObjectName(u"labelVz")

        self.gridPosition.addWidget(self.labelVz, 2, 2, 1, 1)

        self.vzEdit = QDoubleSpinBox(self.groupPosition)
        self.vzEdit.setObjectName(u"vzEdit")
        self.vzEdit.setDecimals(6)
        self.vzEdit.setMinimum(-1000.000000000000000)
        self.vzEdit.setMaximum(1000.000000000000000)

        self.gridPosition.addWidget(self.vzEdit, 2, 3, 1, 1)


        self.mainParametersLayout.addWidget(self.groupPosition)

        self.groupDish = QGroupBox(self.tab)
        self.groupDish.setObjectName(u"groupDish")
        self.gridDish = QGridLayout(self.groupDish)
        self.gridDish.setObjectName(u"gridDish")
        self.labelDiameter = QLabel(self.groupDish)
        self.labelDiameter.setObjectName(u"labelDiameter")

        self.gridDish.addWidget(self.labelDiameter, 0, 0, 1, 1)

        self.diameterEdit = QDoubleSpinBox(self.groupDish)
        self.diameterEdit.setObjectName(u"diameterEdit")
        self.diameterEdit.setDecimals(2)
        self.diameterEdit.setMinimum(0.010000000000000)
        self.diameterEdit.setMaximum(1000.000000000000000)
        self.diameterEdit.setValue(20.000000000000000)

        self.gridDish.addWidget(self.diameterEdit, 0, 1, 1, 1)

        self.labelSurfaceAccuracy = QLabel(self.groupDish)
        self.labelSurfaceAccuracy.setObjectName(u"labelSurfaceAccuracy")

        self.gridDish.addWidget(self.labelSurfaceAccuracy, 0, 2, 1, 1)

        self.surfaceAccuracyEdit = QDoubleSpinBox(self.groupDish)
        self.surfaceAccuracyEdit.setObjectName(u"surfaceAccuracyEdit")
        self.surfaceAccuracyEdit.setDecimals(2)
        self.surfaceAccuracyEdit.setMinimum(0.000000000000000)
        self.surfaceAccuracyEdit.setMaximum(10000.000000000000000)

        self.gridDish.addWidget(self.surfaceAccuracyEdit, 0, 3, 1, 1)


        self.mainParametersLayout.addWidget(self.groupDish)

        self.groupPointing = QGroupBox(self.tab)
        self.groupPointing.setObjectName(u"groupPointing")
        self.gridPointing = QGridLayout(self.groupPointing)
        self.gridPointing.setObjectName(u"gridPointing")
        self.labelElevationRange = QLabel(self.groupPointing)
        self.labelElevationRange.setObjectName(u"labelElevationRange")

        self.gridPointing.addWidget(self.labelElevationRange, 0, 0, 1, 1)

        self.elevationRangeLayout = QHBoxLayout()
        self.elevationRangeLayout.setObjectName(u"elevationRangeLayout")
        self.elevationMinEdit = QDoubleSpinBox(self.groupPointing)
        self.elevationMinEdit.setObjectName(u"elevationMinEdit")
        self.elevationMinEdit.setDecimals(2)
        self.elevationMinEdit.setMinimum(0.000000000000000)
        self.elevationMinEdit.setMaximum(90.000000000000000)

        self.elevationRangeLayout.addWidget(self.elevationMinEdit)

        self.elevationMaxEdit = QDoubleSpinBox(self.groupPointing)
        self.elevationMaxEdit.setObjectName(u"elevationMaxEdit")
        self.elevationMaxEdit.setDecimals(2)
        self.elevationMaxEdit.setMinimum(0.000000000000000)
        self.elevationMaxEdit.setMaximum(90.000000000000000)
        self.elevationMaxEdit.setValue(90.000000000000000)

        self.elevationRangeLayout.addWidget(self.elevationMaxEdit)


        self.gridPointing.addLayout(self.elevationRangeLayout, 0, 1, 1, 1)

        self.labelAzimuthRange = QLabel(self.groupPointing)
        self.labelAzimuthRange.setObjectName(u"labelAzimuthRange")

        self.gridPointing.addWidget(self.labelAzimuthRange, 1, 0, 1, 1)

        self.azimuthRangeLayout = QHBoxLayout()
        self.azimuthRangeLayout.setObjectName(u"azimuthRangeLayout")
        self.azimuthMinEdit = QDoubleSpinBox(self.groupPointing)
        self.azimuthMinEdit.setObjectName(u"azimuthMinEdit")
        self.azimuthMinEdit.setDecimals(2)
        self.azimuthMinEdit.setMinimum(0.000000000000000)
        self.azimuthMinEdit.setMaximum(360.000000000000000)

        self.azimuthRangeLayout.addWidget(self.azimuthMinEdit)

        self.azimuthMaxEdit = QDoubleSpinBox(self.groupPointing)
        self.azimuthMaxEdit.setObjectName(u"azimuthMaxEdit")
        self.azimuthMaxEdit.setDecimals(2)
        self.azimuthMaxEdit.setMinimum(0.000000000000000)
        self.azimuthMaxEdit.setMaximum(360.000000000000000)
        self.azimuthMaxEdit.setValue(360.000000000000000)

        self.azimuthRangeLayout.addWidget(self.azimuthMaxEdit)


        self.gridPointing.addLayout(self.azimuthRangeLayout, 1, 1, 1, 1)


        self.mainParametersLayout.addWidget(self.groupPointing)

        self.isActiveCheckBox = QCheckBox(self.tab)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.mainParametersLayout.addWidget(self.isActiveCheckBox)

        self.mainParametersSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.mainParametersLayout.addItem(self.mainParametersSpacer)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.tab_2.setEnabled(True)
        self.gridLayout_3 = QGridLayout(self.tab_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.line_2 = QFrame(self.tab_2)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line_2, 7, 0, 1, 2)

        self.labelSurfaceEfficiencyTable = QLabel(self.tab_2)
        self.labelSurfaceEfficiencyTable.setObjectName(u"labelSurfaceEfficiencyTable")

        self.gridLayout_3.addWidget(self.labelSurfaceEfficiencyTable, 4, 0, 1, 1)

        self.sefdTable = QTableView(self.tab_2)
        self.sefdTable.setObjectName(u"sefdTable")
        self.sefdTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.sefdTable.setAlternatingRowColors(True)
        self.sefdTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sefdTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.sefdTable, 2, 0, 1, 2)

        self.labelSefdTable = QLabel(self.tab_2)
        self.labelSefdTable.setObjectName(u"labelSefdTable")

        self.gridLayout_3.addWidget(self.labelSefdTable, 0, 0, 1, 1)

        self.surfaceEfficiencyTable = QTableView(self.tab_2)
        self.surfaceEfficiencyTable.setObjectName(u"surfaceEfficiencyTable")
        self.surfaceEfficiencyTable.setAutoFillBackground(False)
        self.surfaceEfficiencyTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.surfaceEfficiencyTable.setAlternatingRowColors(True)
        self.surfaceEfficiencyTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.surfaceEfficiencyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.surfaceEfficiencyTable, 5, 0, 1, 2)

        self.effectiveAreaTable = QTableView(self.tab_2)
        self.effectiveAreaTable.setObjectName(u"effectiveAreaTable")
        self.effectiveAreaTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.effectiveAreaTable.setAlternatingRowColors(True)
        self.effectiveAreaTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.effectiveAreaTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.effectiveAreaTable, 9, 0, 1, 2)

        self.line = QFrame(self.tab_2)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line, 11, 0, 1, 2)

        self.systemTemperatureTable = QTableView(self.tab_2)
        self.systemTemperatureTable.setObjectName(u"systemTemperatureTable")
        self.systemTemperatureTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.systemTemperatureTable.setAlternatingRowColors(True)
        self.systemTemperatureTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.systemTemperatureTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.systemTemperatureTable, 13, 0, 1, 2)

        self.effectiveAreaButtonLayout = QHBoxLayout()
        self.effectiveAreaButtonLayout.setObjectName(u"effectiveAreaButtonLayout")
        self.addEffectiveAreaButton = QPushButton(self.tab_2)
        self.addEffectiveAreaButton.setObjectName(u"addEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.addEffectiveAreaButton)

        self.removeEffectiveAreaButton = QPushButton(self.tab_2)
        self.removeEffectiveAreaButton.setObjectName(u"removeEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.removeEffectiveAreaButton)

        self.clearEffectiveAreaButton = QPushButton(self.tab_2)
        self.clearEffectiveAreaButton.setObjectName(u"clearEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.clearEffectiveAreaButton)

        self.horizontalSpacerEffectiveArea = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.effectiveAreaButtonLayout.addItem(self.horizontalSpacerEffectiveArea)


        self.gridLayout_3.addLayout(self.effectiveAreaButtonLayout, 10, 0, 1, 2)

        self.surfaceEfficiencyButtonLayout = QHBoxLayout()
        self.surfaceEfficiencyButtonLayout.setObjectName(u"surfaceEfficiencyButtonLayout")
        self.addSurfaceEfficiencyButton = QPushButton(self.tab_2)
        self.addSurfaceEfficiencyButton.setObjectName(u"addSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.addSurfaceEfficiencyButton)

        self.removeSurfaceEfficiencyButton = QPushButton(self.tab_2)
        self.removeSurfaceEfficiencyButton.setObjectName(u"removeSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.removeSurfaceEfficiencyButton)

        self.clearSurfaceEfficiencyButton = QPushButton(self.tab_2)
        self.clearSurfaceEfficiencyButton.setObjectName(u"clearSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.clearSurfaceEfficiencyButton)

        self.horizontalSpacerSurfaceEfficiency = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.surfaceEfficiencyButtonLayout.addItem(self.horizontalSpacerSurfaceEfficiency)


        self.gridLayout_3.addLayout(self.surfaceEfficiencyButtonLayout, 6, 0, 1, 2)

        self.labelSystemTemperatureTable = QLabel(self.tab_2)
        self.labelSystemTemperatureTable.setObjectName(u"labelSystemTemperatureTable")

        self.gridLayout_3.addWidget(self.labelSystemTemperatureTable, 12, 0, 1, 2)

        self.systemTemperatureButtonLayout = QHBoxLayout()
        self.systemTemperatureButtonLayout.setObjectName(u"systemTemperatureButtonLayout")
        self.addSystemTemperatureButton = QPushButton(self.tab_2)
        self.addSystemTemperatureButton.setObjectName(u"addSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.addSystemTemperatureButton)

        self.removeSystemTemperatureButton = QPushButton(self.tab_2)
        self.removeSystemTemperatureButton.setObjectName(u"removeSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.removeSystemTemperatureButton)

        self.clearSystemTemperatureButton = QPushButton(self.tab_2)
        self.clearSystemTemperatureButton.setObjectName(u"clearSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.clearSystemTemperatureButton)

        self.horizontalSpacerSystemTemperature = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.systemTemperatureButtonLayout.addItem(self.horizontalSpacerSystemTemperature)


        self.gridLayout_3.addLayout(self.systemTemperatureButtonLayout, 14, 0, 1, 2)

        self.labelEffectiveAreaTable = QLabel(self.tab_2)
        self.labelEffectiveAreaTable.setObjectName(u"labelEffectiveAreaTable")

        self.gridLayout_3.addWidget(self.labelEffectiveAreaTable, 8, 0, 1, 2)

        self.sefdButtonLayout = QHBoxLayout()
        self.sefdButtonLayout.setObjectName(u"sefdButtonLayout")
        self.addSefdButton = QPushButton(self.tab_2)
        self.addSefdButton.setObjectName(u"addSefdButton")

        self.sefdButtonLayout.addWidget(self.addSefdButton)

        self.removeSefdButton = QPushButton(self.tab_2)
        self.removeSefdButton.setObjectName(u"removeSefdButton")

        self.sefdButtonLayout.addWidget(self.removeSefdButton)

        self.clearSefdButton = QPushButton(self.tab_2)
        self.clearSefdButton.setObjectName(u"clearSefdButton")

        self.sefdButtonLayout.addWidget(self.clearSefdButton)

        self.horizontalSpacerSefd = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sefdButtonLayout.addItem(self.horizontalSpacerSefd)


        self.gridLayout_3.addLayout(self.sefdButtonLayout, 3, 0, 1, 1)

        self.tabWidget.addTab(self.tab_2, "")

        self.gridLayout_2.addWidget(self.tabWidget, 0, 0, 1, 1)

        self.line_3 = QFrame(TelescopeEditorDialog)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_3, 1, 0, 1, 1)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacerButtons = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacerButtons)

        self.saveButton = QPushButton(TelescopeEditorDialog)
        self.saveButton.setObjectName(u"saveButton")

        self.buttonLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(TelescopeEditorDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.buttonLayout.addWidget(self.cancelButton)


        self.gridLayout_2.addLayout(self.buttonLayout, 2, 0, 1, 1)


        self.retranslateUi(TelescopeEditorDialog)
        self.saveButton.clicked.connect(TelescopeEditorDialog.accept)
        self.cancelButton.clicked.connect(TelescopeEditorDialog.reject)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(TelescopeEditorDialog)
    # setupUi

    def retranslateUi(self, TelescopeEditorDialog):
        TelescopeEditorDialog.setWindowTitle(QCoreApplication.translate("TelescopeEditorDialog", u"Edit Telescope", None))
        self.groupIdentity.setTitle(QCoreApplication.translate("TelescopeEditorDialog", u"What it is", None))
        self.labelCode.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Code:", None))
        self.codeEdit.setPlaceholderText(QCoreApplication.translate("TelescopeEditorDialog", u"Enter telescope code", None))
        self.labelMountType.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Mount:", None))
        self.mountTypeCombo.setItemText(0, QCoreApplication.translate("TelescopeEditorDialog", u"EQUA", None))
        self.mountTypeCombo.setItemText(1, QCoreApplication.translate("TelescopeEditorDialog", u"AZIM", None))

        self.labelName.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Name:", None))
        self.nameEdit.setPlaceholderText(QCoreApplication.translate("TelescopeEditorDialog", u"Enter telescope name", None))
        self.groupPosition.setTitle(QCoreApplication.translate("TelescopeEditorDialog", u"Where it stands, and how it moves", None))
        self.labelX.setText(QCoreApplication.translate("TelescopeEditorDialog", u"X (m):", None))
        self.labelVx.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Vx (m/yr):", None))
        self.labelY.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Y (m):", None))
        self.labelVy.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Vy (m/yr):", None))
        self.labelZ.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Z (m):", None))
        self.labelVz.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Vz (m/yr):", None))
        self.groupDish.setTitle(QCoreApplication.translate("TelescopeEditorDialog", u"The dish", None))
        self.labelDiameter.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Diameter (m):", None))
        self.labelSurfaceAccuracy.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Surface accuracy (um):", None))
#if QT_CONFIG(tooltip)
        self.surfaceAccuracyEdit.setToolTip(QCoreApplication.translate("TelescopeEditorDialog", u"The RMS error of the surface, which is what Ruze's formula takes. Leave it at None when it is not known.", None))
#endif // QT_CONFIG(tooltip)
        self.surfaceAccuracyEdit.setSpecialValueText(QCoreApplication.translate("TelescopeEditorDialog", u"None", None))
        self.groupPointing.setTitle(QCoreApplication.translate("TelescopeEditorDialog", u"Where it can point", None))
        self.labelElevationRange.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Elevation (deg):", None))
        self.elevationMinEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.elevationMaxEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.labelAzimuthRange.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Azimuth (deg):", None))
        self.azimuthMinEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.azimuthMaxEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.isActiveCheckBox.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Active in this observation", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("TelescopeEditorDialog", u"Main Parameters", None))
        self.labelSurfaceEfficiencyTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Surface Efficiency Table (from-to MHz, efficiency):", None))
        self.labelSefdTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"SEFD Table (from-to MHz, Jy):", None))
        self.addEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.addSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.labelSystemTemperatureTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"System Temperature Table (from-to MHz, K):", None))
        self.addSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.labelEffectiveAreaTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Effective Area Table (from-to MHz, m\u00b2):", None))
        self.addSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("TelescopeEditorDialog", u"Sensitivity", None))
        self.saveButton.setProperty(u"role", QCoreApplication.translate("TelescopeEditorDialog", u"primary", None))
        self.saveButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Cancel", None))
    # retranslateUi

