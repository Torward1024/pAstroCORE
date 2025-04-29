# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_telescopeORduXM.ui'
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
    QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableView, QVBoxLayout,
    QWidget)

class Ui_TelescopeEditorDialog(object):
    def setupUi(self, TelescopeEditorDialog):
        if not TelescopeEditorDialog.objectName():
            TelescopeEditorDialog.setObjectName(u"TelescopeEditorDialog")
        TelescopeEditorDialog.resize(583, 916)
        self.verticalLayout = QVBoxLayout(TelescopeEditorDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelCode = QLabel(TelescopeEditorDialog)
        self.labelCode.setObjectName(u"labelCode")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelCode)

        self.codeEdit = QLineEdit(TelescopeEditorDialog)
        self.codeEdit.setObjectName(u"codeEdit")
        self.codeEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.codeEdit)

        self.labelName = QLabel(TelescopeEditorDialog)
        self.labelName.setObjectName(u"labelName")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelName)

        self.nameEdit = QLineEdit(TelescopeEditorDialog)
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

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameEdit)

        self.labelX = QLabel(TelescopeEditorDialog)
        self.labelX.setObjectName(u"labelX")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelX)

        self.xEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.xEdit.setObjectName(u"xEdit")
        self.xEdit.setDecimals(2)
        self.xEdit.setMinimum(-10000000.000000000000000)
        self.xEdit.setMaximum(10000000.000000000000000)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.xEdit)

        self.labelY = QLabel(TelescopeEditorDialog)
        self.labelY.setObjectName(u"labelY")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelY)

        self.yEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.yEdit.setObjectName(u"yEdit")
        self.yEdit.setDecimals(2)
        self.yEdit.setMinimum(-10000000.000000000000000)
        self.yEdit.setMaximum(10000000.000000000000000)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.yEdit)

        self.labelZ = QLabel(TelescopeEditorDialog)
        self.labelZ.setObjectName(u"labelZ")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.labelZ)

        self.zEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.zEdit.setObjectName(u"zEdit")
        self.zEdit.setDecimals(2)
        self.zEdit.setMinimum(-10000000.000000000000000)
        self.zEdit.setMaximum(10000000.000000000000000)

        self.formLayout.setWidget(4, QFormLayout.FieldRole, self.zEdit)

        self.labelVx = QLabel(TelescopeEditorDialog)
        self.labelVx.setObjectName(u"labelVx")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.labelVx)

        self.vxEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.vxEdit.setObjectName(u"vxEdit")
        self.vxEdit.setDecimals(2)
        self.vxEdit.setMinimum(-1000.000000000000000)
        self.vxEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.vxEdit)

        self.labelVy = QLabel(TelescopeEditorDialog)
        self.labelVy.setObjectName(u"labelVy")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.labelVy)

        self.vyEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.vyEdit.setObjectName(u"vyEdit")
        self.vyEdit.setDecimals(2)
        self.vyEdit.setMinimum(-1000.000000000000000)
        self.vyEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(6, QFormLayout.FieldRole, self.vyEdit)

        self.labelVz = QLabel(TelescopeEditorDialog)
        self.labelVz.setObjectName(u"labelVz")

        self.formLayout.setWidget(7, QFormLayout.LabelRole, self.labelVz)

        self.vzEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.vzEdit.setObjectName(u"vzEdit")
        self.vzEdit.setDecimals(2)
        self.vzEdit.setMinimum(-1000.000000000000000)
        self.vzEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(7, QFormLayout.FieldRole, self.vzEdit)

        self.labelDiameter = QLabel(TelescopeEditorDialog)
        self.labelDiameter.setObjectName(u"labelDiameter")

        self.formLayout.setWidget(8, QFormLayout.LabelRole, self.labelDiameter)

        self.diameterEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.diameterEdit.setObjectName(u"diameterEdit")
        self.diameterEdit.setDecimals(2)
        self.diameterEdit.setMinimum(0.010000000000000)
        self.diameterEdit.setMaximum(1000.000000000000000)
        self.diameterEdit.setValue(1.000000000000000)

        self.formLayout.setWidget(8, QFormLayout.FieldRole, self.diameterEdit)

        self.labelSurfaceAccuracy = QLabel(TelescopeEditorDialog)
        self.labelSurfaceAccuracy.setObjectName(u"labelSurfaceAccuracy")

        self.formLayout.setWidget(9, QFormLayout.LabelRole, self.labelSurfaceAccuracy)

        self.surfaceAccuracyEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.surfaceAccuracyEdit.setObjectName(u"surfaceAccuracyEdit")
        self.surfaceAccuracyEdit.setDecimals(2)
        self.surfaceAccuracyEdit.setMinimum(0.000000000000000)
        self.surfaceAccuracyEdit.setMaximum(10000.000000000000000)

        self.formLayout.setWidget(9, QFormLayout.FieldRole, self.surfaceAccuracyEdit)

        self.labelElevationRange = QLabel(TelescopeEditorDialog)
        self.labelElevationRange.setObjectName(u"labelElevationRange")

        self.formLayout.setWidget(10, QFormLayout.LabelRole, self.labelElevationRange)

        self.elevationRangeLayout = QHBoxLayout()
        self.elevationRangeLayout.setObjectName(u"elevationRangeLayout")
        self.elevationMinEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.elevationMinEdit.setObjectName(u"elevationMinEdit")
        self.elevationMinEdit.setDecimals(2)
        self.elevationMinEdit.setMinimum(0.000000000000000)
        self.elevationMinEdit.setMaximum(90.000000000000000)

        self.elevationRangeLayout.addWidget(self.elevationMinEdit)

        self.elevationMaxEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.elevationMaxEdit.setObjectName(u"elevationMaxEdit")
        self.elevationMaxEdit.setDecimals(2)
        self.elevationMaxEdit.setMinimum(0.000000000000000)
        self.elevationMaxEdit.setMaximum(90.000000000000000)
        self.elevationMaxEdit.setValue(90.000000000000000)

        self.elevationRangeLayout.addWidget(self.elevationMaxEdit)


        self.formLayout.setLayout(10, QFormLayout.FieldRole, self.elevationRangeLayout)

        self.labelAzimuthRange = QLabel(TelescopeEditorDialog)
        self.labelAzimuthRange.setObjectName(u"labelAzimuthRange")

        self.formLayout.setWidget(11, QFormLayout.LabelRole, self.labelAzimuthRange)

        self.azimuthRangeLayout = QHBoxLayout()
        self.azimuthRangeLayout.setObjectName(u"azimuthRangeLayout")
        self.azimuthMinEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.azimuthMinEdit.setObjectName(u"azimuthMinEdit")
        self.azimuthMinEdit.setDecimals(2)
        self.azimuthMinEdit.setMinimum(0.000000000000000)
        self.azimuthMinEdit.setMaximum(360.000000000000000)

        self.azimuthRangeLayout.addWidget(self.azimuthMinEdit)

        self.azimuthMaxEdit = QDoubleSpinBox(TelescopeEditorDialog)
        self.azimuthMaxEdit.setObjectName(u"azimuthMaxEdit")
        self.azimuthMaxEdit.setDecimals(2)
        self.azimuthMaxEdit.setMinimum(0.000000000000000)
        self.azimuthMaxEdit.setMaximum(360.000000000000000)
        self.azimuthMaxEdit.setValue(360.000000000000000)

        self.azimuthRangeLayout.addWidget(self.azimuthMaxEdit)


        self.formLayout.setLayout(11, QFormLayout.FieldRole, self.azimuthRangeLayout)

        self.labelMountType = QLabel(TelescopeEditorDialog)
        self.labelMountType.setObjectName(u"labelMountType")

        self.formLayout.setWidget(12, QFormLayout.LabelRole, self.labelMountType)

        self.mountTypeCombo = QComboBox(TelescopeEditorDialog)
        self.mountTypeCombo.addItem("")
        self.mountTypeCombo.addItem("")
        self.mountTypeCombo.setObjectName(u"mountTypeCombo")
        self.mountTypeCombo.setStyleSheet(u"QComboBox {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* \u0411\u0430\u0437\u043e\u0432\u044b\u0439 \u0444\u043e\u043d, \u043a\u0430\u043a \u0443 readOnly QLineEdit */\n"
"    border: 1px solid #d3d3d3; /* \u0411\u0430\u0437\u043e\u0432\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430, \u043a\u0430\u043a \u0443 readOnly QLineEdit */\n"
"}\n"
"\n"
"QComboBox:editable {\n"
"    background-color: #f0f6ff; /* \u0424\u043e\u043d \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f, \u043a\u0430\u043a \u0443 readOnly=\"false\" */\n"
"    border: 1px solid #0078d7; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"}\n"
"\n"
"QComb"
                        "oBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438, \u043a\u0430\u043a \u0443 readOnly=\"false\":hover */\n"
"}\n"
"\n"
"QComboBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"    background-color: #ffffff; /* \u0424\u043e\u043d \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"}\n"
"\n"
"QComboBox:!editable {\n"
"    background-color: #f0f6ff; /* \u0424\u043e\u043d \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f, \u043a\u0430\u043a \u0443 readOnly=\"false\" */\n"
"    border: 1px solid #0078d7; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u043b"
                        "\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"}\n"
"\n"
"QComboBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438, \u043a\u0430\u043a \u0443 readOnly=\"false\":hover */\n"
"}\n"
"\n"
"QComboBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"    background-color: #ffffff; /* \u0424\u043e\u043d \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"}\n"
"\n"
"/* \u0421\u0442\u0438\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043a\u043d\u043e\u043f\u043a\u0438 \u0441\u043e \u0441\u0442\u0440\u0435\u043b\u043a\u043e\u0439 */\n"
"QComboBox::drop-down {\n"
"    sub"
                        "control-origin: padding;\n"
"    subcontrol-position: right;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* \u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0430 \u0433\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u043b\u044f \u0432\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0440\u0430\u0437\u0434\u0435\u043b\u0435\u043d\u0438\u044f */\n"
"    border-top-right-radius: 3px;\n"
"    border-bottom-right-radius: 3px;\n"
"    background-color: #f9f9f9; /* \u0424\u043e\u043d \u043a\u043d\u043e\u043f\u043a\u0438, \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0449\u0438\u0439 \u0441 \u043e\u0441\u043d\u043e\u0432\u043d\u044b\u043c */\n"
"}\n"
"\n"
"QComboBox::drop-down:hover {\n"
"    background-color: #0078d7; /* \u041b\u0451\u0433\u043a\u043e\u0435 \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    /* \u0421\u0442"
                        "\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0441\u0442\u0440\u0435\u043b\u043a\u0430 Qt, \u0435\u0441\u043b\u0438 \u043d\u0435\u0442 \u0438\u043a\u043e\u043d\u043a\u0438 */\n"
"    /* \u0415\u0441\u043b\u0438 \u0435\u0441\u0442\u044c \u0438\u043a\u043e\u043d\u043a\u0430, \u0440\u0430\u0441\u043a\u043e\u043c\u043c\u0435\u043d\u0442\u0438\u0440\u0443\u0439\u0442\u0435: */\n"
"    /* image: url(:/icons/down_arrow.png); */\n"
"}\n"
"\n"
"/* \u0421\u0442\u0438\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0432\u044b\u043f\u0430\u0434\u0430\u044e\u0449\u0435\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430 */\n"
"QComboBox QAbstractItemView {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    background-color: #ffffff;\n"
"    border: 1px solid #d3d3d3;\n"
"    selection-background-color: #0078d7;\n"
"    selection-color: #ffffff;\n"
"    padding: 1px;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView::item {\n"
"    padding: 4px;\n"
"    min-height: 20px;\n"
"}\n"
"\n"
"QComboB"
                        "ox QAbstractItemView::item:hover {\n"
"    background-color: #0078d7;\n"
"}")

        self.formLayout.setWidget(12, QFormLayout.FieldRole, self.mountTypeCombo)

        self.labelIsActive = QLabel(TelescopeEditorDialog)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(13, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(TelescopeEditorDialog)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(13, QFormLayout.FieldRole, self.isActiveCheckBox)


        self.verticalLayout.addLayout(self.formLayout)

        self.labelSefdTable = QLabel(TelescopeEditorDialog)
        self.labelSefdTable.setObjectName(u"labelSefdTable")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(10)
        font.setBold(True)
        self.labelSefdTable.setFont(font)

        self.verticalLayout.addWidget(self.labelSefdTable)

        self.sefdTable = QTableView(TelescopeEditorDialog)
        self.sefdTable.setObjectName(u"sefdTable")
        self.sefdTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.sefdTable.setAlternatingRowColors(True)
        self.sefdTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sefdTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.sefdTable)

        self.sefdButtonLayout = QHBoxLayout()
        self.sefdButtonLayout.setObjectName(u"sefdButtonLayout")
        self.addSefdButton = QPushButton(TelescopeEditorDialog)
        self.addSefdButton.setObjectName(u"addSefdButton")

        self.sefdButtonLayout.addWidget(self.addSefdButton)

        self.removeSefdButton = QPushButton(TelescopeEditorDialog)
        self.removeSefdButton.setObjectName(u"removeSefdButton")

        self.sefdButtonLayout.addWidget(self.removeSefdButton)

        self.clearSefdButton = QPushButton(TelescopeEditorDialog)
        self.clearSefdButton.setObjectName(u"clearSefdButton")

        self.sefdButtonLayout.addWidget(self.clearSefdButton)

        self.horizontalSpacerSefd = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sefdButtonLayout.addItem(self.horizontalSpacerSefd)


        self.verticalLayout.addLayout(self.sefdButtonLayout)

        self.labelSurfaceEfficiencyTable = QLabel(TelescopeEditorDialog)
        self.labelSurfaceEfficiencyTable.setObjectName(u"labelSurfaceEfficiencyTable")
        self.labelSurfaceEfficiencyTable.setFont(font)

        self.verticalLayout.addWidget(self.labelSurfaceEfficiencyTable)

        self.surfaceEfficiencyTable = QTableView(TelescopeEditorDialog)
        self.surfaceEfficiencyTable.setObjectName(u"surfaceEfficiencyTable")
        self.surfaceEfficiencyTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.surfaceEfficiencyTable.setAlternatingRowColors(True)
        self.surfaceEfficiencyTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.surfaceEfficiencyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.surfaceEfficiencyTable)

        self.surfaceEfficiencyButtonLayout = QHBoxLayout()
        self.surfaceEfficiencyButtonLayout.setObjectName(u"surfaceEfficiencyButtonLayout")
        self.addSurfaceEfficiencyButton = QPushButton(TelescopeEditorDialog)
        self.addSurfaceEfficiencyButton.setObjectName(u"addSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.addSurfaceEfficiencyButton)

        self.removeSurfaceEfficiencyButton = QPushButton(TelescopeEditorDialog)
        self.removeSurfaceEfficiencyButton.setObjectName(u"removeSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.removeSurfaceEfficiencyButton)

        self.clearSurfaceEfficiencyButton = QPushButton(TelescopeEditorDialog)
        self.clearSurfaceEfficiencyButton.setObjectName(u"clearSurfaceEfficiencyButton")

        self.surfaceEfficiencyButtonLayout.addWidget(self.clearSurfaceEfficiencyButton)

        self.horizontalSpacerSurfaceEfficiency = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.surfaceEfficiencyButtonLayout.addItem(self.horizontalSpacerSurfaceEfficiency)


        self.verticalLayout.addLayout(self.surfaceEfficiencyButtonLayout)

        self.labelEffectiveAreaTable = QLabel(TelescopeEditorDialog)
        self.labelEffectiveAreaTable.setObjectName(u"labelEffectiveAreaTable")
        self.labelEffectiveAreaTable.setFont(font)

        self.verticalLayout.addWidget(self.labelEffectiveAreaTable)

        self.effectiveAreaTable = QTableView(TelescopeEditorDialog)
        self.effectiveAreaTable.setObjectName(u"effectiveAreaTable")
        self.effectiveAreaTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.effectiveAreaTable.setAlternatingRowColors(True)
        self.effectiveAreaTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.effectiveAreaTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.effectiveAreaTable)

        self.effectiveAreaButtonLayout = QHBoxLayout()
        self.effectiveAreaButtonLayout.setObjectName(u"effectiveAreaButtonLayout")
        self.addEffectiveAreaButton = QPushButton(TelescopeEditorDialog)
        self.addEffectiveAreaButton.setObjectName(u"addEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.addEffectiveAreaButton)

        self.removeEffectiveAreaButton = QPushButton(TelescopeEditorDialog)
        self.removeEffectiveAreaButton.setObjectName(u"removeEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.removeEffectiveAreaButton)

        self.clearEffectiveAreaButton = QPushButton(TelescopeEditorDialog)
        self.clearEffectiveAreaButton.setObjectName(u"clearEffectiveAreaButton")

        self.effectiveAreaButtonLayout.addWidget(self.clearEffectiveAreaButton)

        self.horizontalSpacerEffectiveArea = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.effectiveAreaButtonLayout.addItem(self.horizontalSpacerEffectiveArea)


        self.verticalLayout.addLayout(self.effectiveAreaButtonLayout)

        self.labelSystemTemperatureTable = QLabel(TelescopeEditorDialog)
        self.labelSystemTemperatureTable.setObjectName(u"labelSystemTemperatureTable")
        self.labelSystemTemperatureTable.setFont(font)

        self.verticalLayout.addWidget(self.labelSystemTemperatureTable)

        self.systemTemperatureTable = QTableView(TelescopeEditorDialog)
        self.systemTemperatureTable.setObjectName(u"systemTemperatureTable")
        self.systemTemperatureTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.systemTemperatureTable.setAlternatingRowColors(True)
        self.systemTemperatureTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.systemTemperatureTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout.addWidget(self.systemTemperatureTable)

        self.systemTemperatureButtonLayout = QHBoxLayout()
        self.systemTemperatureButtonLayout.setObjectName(u"systemTemperatureButtonLayout")
        self.addSystemTemperatureButton = QPushButton(TelescopeEditorDialog)
        self.addSystemTemperatureButton.setObjectName(u"addSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.addSystemTemperatureButton)

        self.removeSystemTemperatureButton = QPushButton(TelescopeEditorDialog)
        self.removeSystemTemperatureButton.setObjectName(u"removeSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.removeSystemTemperatureButton)

        self.clearSystemTemperatureButton = QPushButton(TelescopeEditorDialog)
        self.clearSystemTemperatureButton.setObjectName(u"clearSystemTemperatureButton")

        self.systemTemperatureButtonLayout.addWidget(self.clearSystemTemperatureButton)

        self.horizontalSpacerSystemTemperature = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.systemTemperatureButtonLayout.addItem(self.horizontalSpacerSystemTemperature)


        self.verticalLayout.addLayout(self.systemTemperatureButtonLayout)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacerButtons = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacerButtons)

        self.saveButton = QPushButton(TelescopeEditorDialog)
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

        self.cancelButton = QPushButton(TelescopeEditorDialog)
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


        self.retranslateUi(TelescopeEditorDialog)
        self.saveButton.clicked.connect(TelescopeEditorDialog.accept)
        self.cancelButton.clicked.connect(TelescopeEditorDialog.reject)

        QMetaObject.connectSlotsByName(TelescopeEditorDialog)
    # setupUi

    def retranslateUi(self, TelescopeEditorDialog):
        TelescopeEditorDialog.setWindowTitle(QCoreApplication.translate("TelescopeEditorDialog", u"Edit Telescope", None))
        TelescopeEditorDialog.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelCode.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Code:", None))
        self.codeEdit.setPlaceholderText(QCoreApplication.translate("TelescopeEditorDialog", u"Enter telescope code", None))
        self.labelName.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Name:", None))
        self.nameEdit.setPlaceholderText(QCoreApplication.translate("TelescopeEditorDialog", u"Enter telescope name", None))
        self.labelX.setText(QCoreApplication.translate("TelescopeEditorDialog", u"X (m):", None))
        self.labelY.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Y (m):", None))
        self.labelZ.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Z (m):", None))
        self.labelVx.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Vx (m/s):", None))
        self.labelVy.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Vy (m/s):", None))
        self.labelVz.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Vz (m/s):", None))
        self.labelDiameter.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Diameter (m):", None))
        self.labelSurfaceAccuracy.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Surface Accuracy (\u00b5m):", None))
        self.surfaceAccuracyEdit.setSpecialValueText(QCoreApplication.translate("TelescopeEditorDialog", u"None", None))
        self.labelElevationRange.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Elevation Range (deg):", None))
        self.elevationMinEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.elevationMaxEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.labelAzimuthRange.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Azimuth Range (deg):", None))
        self.azimuthMinEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.azimuthMaxEdit.setSuffix(QCoreApplication.translate("TelescopeEditorDialog", u" deg", None))
        self.labelMountType.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Mount Type:", None))
        self.mountTypeCombo.setItemText(0, QCoreApplication.translate("TelescopeEditorDialog", u"EQUA", None))
        self.mountTypeCombo.setItemText(1, QCoreApplication.translate("TelescopeEditorDialog", u"AZIM", None))

        self.labelIsActive.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Active:", None))
        self.labelSefdTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"SEFD Table (MHz, Jy):", None))
        self.sefdTable.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addSefdButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add SEFD", None))
        self.removeSefdButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove SEFD", None))
        self.clearSefdButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear SEFD Table", None))
        self.labelSurfaceEfficiencyTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Surface Efficiency Table (MHz, Efficiency):", None))
        self.surfaceEfficiencyTable.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addSurfaceEfficiencyButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add Efficiency", None))
        self.removeSurfaceEfficiencyButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove Efficiency", None))
        self.clearSurfaceEfficiencyButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear Efficiency Table", None))
        self.labelEffectiveAreaTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Effective Area Table (MHz, m\u00b2):", None))
        self.effectiveAreaTable.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addEffectiveAreaButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add Area", None))
        self.removeEffectiveAreaButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove Area", None))
        self.clearEffectiveAreaButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear Area Table", None))
        self.labelSystemTemperatureTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"System Temperature Table (MHz, K):", None))
        self.systemTemperatureTable.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.addSystemTemperatureButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add Temperature", None))
        self.removeSystemTemperatureButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.removeSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove Temperature", None))
        self.clearSystemTemperatureButton.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #d9534f; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.clearSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear Temperature Table", None))
        self.saveButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Cancel", None))
    # retranslateUi