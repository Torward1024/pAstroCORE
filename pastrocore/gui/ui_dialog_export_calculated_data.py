# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_export_calculated_datasEinBh.ui'
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
    QDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_ExportCalculatedDataDialog(object):
    def setupUi(self, ExportCalculatedDataDialog):
        if not ExportCalculatedDataDialog.objectName():
            ExportCalculatedDataDialog.setObjectName(u"ExportCalculatedDataDialog")
        ExportCalculatedDataDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        ExportCalculatedDataDialog.resize(600, 450)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ExportCalculatedDataDialog.sizePolicy().hasHeightForWidth())
        ExportCalculatedDataDialog.setSizePolicy(sizePolicy)
        ExportCalculatedDataDialog.setMinimumSize(QSize(600, 450))
        ExportCalculatedDataDialog.setMaximumSize(QSize(600, 450))
        icon = QIcon()
        icon.addFile(u":/icons/export_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        ExportCalculatedDataDialog.setWindowIcon(icon)
        ExportCalculatedDataDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        ExportCalculatedDataDialog.setModal(True)
        self.gridLayout_3 = QGridLayout(ExportCalculatedDataDialog)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.line_2 = QFrame(ExportCalculatedDataDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line_2, 5, 0, 1, 2)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.exportButton = QPushButton(ExportCalculatedDataDialog)
        self.exportButton.setObjectName(u"exportButton")
        self.exportButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")
        self.exportButton.setAutoDefault(False)
        self.exportButton.setFlat(True)

        self.buttonLayout.addWidget(self.exportButton)

        self.cancelButton = QPushButton(ExportCalculatedDataDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")
        self.cancelButton.setAutoDefault(True)
        self.cancelButton.setFlat(True)

        self.buttonLayout.addWidget(self.cancelButton)


        self.gridLayout_3.addLayout(self.buttonLayout, 6, 0, 1, 2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.lblPath = QLabel(ExportCalculatedDataDialog)
        self.lblPath.setObjectName(u"lblPath")

        self.horizontalLayout_3.addWidget(self.lblPath)

        self.lineEdit = QLineEdit(ExportCalculatedDataDialog)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
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

        self.horizontalLayout_3.addWidget(self.lineEdit)

        self.pushButton = QPushButton(ExportCalculatedDataDialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.horizontalLayout_3.addWidget(self.pushButton)


        self.gridLayout_3.addLayout(self.horizontalLayout_3, 4, 0, 1, 2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.selectAllCalcButton = QPushButton(ExportCalculatedDataDialog)
        self.selectAllCalcButton.setObjectName(u"selectAllCalcButton")
        self.selectAllCalcButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.horizontalLayout_2.addWidget(self.selectAllCalcButton)

        self.clearAllCalcButton = QPushButton(ExportCalculatedDataDialog)
        self.clearAllCalcButton.setObjectName(u"clearAllCalcButton")
        self.clearAllCalcButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.horizontalLayout_2.addWidget(self.clearAllCalcButton)


        self.gridLayout.addLayout(self.horizontalLayout_2, 6, 2, 1, 1)

        self.targetList = QListWidget(ExportCalculatedDataDialog)
        self.targetList.setObjectName(u"targetList")
        self.targetList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.targetList, 3, 3, 1, 1)

        self.labelTargets = QLabel(ExportCalculatedDataDialog)
        self.labelTargets.setObjectName(u"labelTargets")

        self.gridLayout.addWidget(self.labelTargets, 2, 3, 1, 1)

        self.labelCalc = QLabel(ExportCalculatedDataDialog)
        self.labelCalc.setObjectName(u"labelCalc")

        self.gridLayout.addWidget(self.labelCalc, 2, 2, 1, 1)

        self.calcList = QListWidget(ExportCalculatedDataDialog)
        self.calcList.setObjectName(u"calcList")

        self.gridLayout.addWidget(self.calcList, 3, 2, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.selectAllObsButton = QPushButton(ExportCalculatedDataDialog)
        self.selectAllObsButton.setObjectName(u"selectAllObsButton")
        self.selectAllObsButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")
        self.selectAllObsButton.setFlat(True)

        self.horizontalLayout.addWidget(self.selectAllObsButton)

        self.clearAllObsButton = QPushButton(ExportCalculatedDataDialog)
        self.clearAllObsButton.setObjectName(u"clearAllObsButton")
        self.clearAllObsButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.horizontalLayout.addWidget(self.clearAllObsButton)


        self.gridLayout.addLayout(self.horizontalLayout, 6, 3, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout, 0, 0, 1, 2)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.chkExportVisualizations = QCheckBox(ExportCalculatedDataDialog)
        self.chkExportVisualizations.setObjectName(u"chkExportVisualizations")
        self.chkExportVisualizations.setStyleSheet(u"/* \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0441\u0442\u0438\u043b\u044c QCheckBox */\n"
"QCheckBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    spacing: 6px;\n"
"    padding: 2px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QCheckBox::item {\n"
"    padding: 2px;\n"
"}\n"
"\n"
"/* \u0418\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440 \u0447\u0435\u043a\u0431\u043e\u043a\u0441\u0430 */\n"
"QCheckBox::indicator {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"\n"
"/* Unchecked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 */\n"
"QCheckBox::indicator:unchecked {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:hover {\n"
"    border: 1px solid #1a8cff;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:focus {\n"
"    b"
                        "order: 1px solid #005bb5;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"/* Checked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 - \u0411\u0415\u041b\u042b\u0419 \u0424\u041e\u041d, \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430 */\n"
"QCheckBox::indicator:checked {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:hover {\n"
"    border: 1px solid #1a8cff; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_hover.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:focus {\n"
"    border: 1px solid #005bb5; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430"
                        "\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"/* Disabled \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"QCheckBox::indicator:unchecked:disabled {\n"
"    border: 1px solid #e0e0e0;\n"
"    background-color: #f5f5f5;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0; /* \u0421\u0432\u0435\u0442\u043b\u043e-\u0441\u0435\u0440\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_disabled.svg);\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #999999;\n"
"}")
        self.chkExportVisualizations.setChecked(True)

        self.gridLayout_2.addWidget(self.chkExportVisualizations, 2, 0, 1, 1)

        self.chkExportData = QCheckBox(ExportCalculatedDataDialog)
        self.chkExportData.setObjectName(u"chkExportData")
        self.chkExportData.setEnabled(True)
        self.chkExportData.setStyleSheet(u"/* \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0441\u0442\u0438\u043b\u044c QCheckBox */\n"
"QCheckBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    spacing: 6px;\n"
"    padding: 2px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QCheckBox::item {\n"
"    padding: 2px;\n"
"}\n"
"\n"
"/* \u0418\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440 \u0447\u0435\u043a\u0431\u043e\u043a\u0441\u0430 */\n"
"QCheckBox::indicator {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"\n"
"/* Unchecked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 */\n"
"QCheckBox::indicator:unchecked {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:hover {\n"
"    border: 1px solid #1a8cff;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:focus {\n"
"    b"
                        "order: 1px solid #005bb5;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"/* Checked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 - \u0411\u0415\u041b\u042b\u0419 \u0424\u041e\u041d, \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430 */\n"
"QCheckBox::indicator:checked {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:hover {\n"
"    border: 1px solid #1a8cff; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_hover.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:focus {\n"
"    border: 1px solid #005bb5; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430"
                        "\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"/* Disabled \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"QCheckBox::indicator:unchecked:disabled {\n"
"    border: 1px solid #e0e0e0;\n"
"    background-color: #f5f5f5;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0; /* \u0421\u0432\u0435\u0442\u043b\u043e-\u0441\u0435\u0440\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_disabled.svg);\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #999999;\n"
"}")
        self.chkExportData.setChecked(True)

        self.gridLayout_2.addWidget(self.chkExportData, 3, 0, 1, 1)

        self.line = QFrame(ExportCalculatedDataDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 0, 0, 1, 3)

        self.lblFigureScale = QLabel(ExportCalculatedDataDialog)
        self.lblFigureScale.setObjectName(u"lblFigureScale")

        self.gridLayout_2.addWidget(self.lblFigureScale, 2, 1, 1, 1)

        self.cmbUnits = QComboBox(ExportCalculatedDataDialog)
        self.cmbUnits.setObjectName(u"cmbUnits")
        self.cmbUnits.setStyleSheet(u"QComboBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
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
"QCombo"
                        "Box:editable:hover {\n"
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
"    image: url("
                        ":/icons/down_arrow_icon.svg);\n"
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
"QComboBox QAbstractItemView::item:hover {\n"
"    background-color: #0078d7;\n"
"}")

        self.gridLayout_2.addWidget(self.cmbUnits, 2, 2, 1, 1)

        self.labelParameters = QLabel(ExportCalculatedDataDialog)
        self.labelParameters.setObjectName(u"labelParameters")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(False)
        self.labelParameters.setFont(font)

        self.gridLayout_2.addWidget(self.labelParameters, 1, 0, 1, 3)


        self.gridLayout_3.addLayout(self.gridLayout_2, 2, 0, 1, 2)


        self.retranslateUi(ExportCalculatedDataDialog)

        QMetaObject.connectSlotsByName(ExportCalculatedDataDialog)
    # setupUi

    def retranslateUi(self, ExportCalculatedDataDialog):
        ExportCalculatedDataDialog.setWindowTitle(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export Calculated Data", None))
        self.exportButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export", None))
        self.cancelButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Cancel", None))
        self.lblPath.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Path:", None))
        self.pushButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Browse", None))
        self.selectAllCalcButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Select All", None))
        self.clearAllCalcButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Clear", None))
        self.labelTargets.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Observations:", None))
        self.labelCalc.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Calculations:", None))
        self.selectAllObsButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Select All", None))
        self.clearAllObsButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Clear", None))
        self.chkExportVisualizations.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export Visualizations", None))
        self.chkExportData.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export Data to Text Tables", None))
        self.lblFigureScale.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"UV Units in Figures:", None))
        self.cmbUnits.setCurrentText("")
        self.labelParameters.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Parameters:", None))
    # retranslateUi