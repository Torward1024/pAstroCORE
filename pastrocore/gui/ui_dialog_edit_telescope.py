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
    QDialog, QDoubleSpinBox, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QTableView, QWidget)
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
        TelescopeEditorDialog.setMinimumSize(QSize(460, 590))
        TelescopeEditorDialog.setMaximumSize(QSize(460, 590))
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
        self.gridLayout = QGridLayout(self.tab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line_4 = QFrame(self.tab)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_4, 1, 0, 1, 1)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelCode = QLabel(self.tab)
        self.labelCode.setObjectName(u"labelCode")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelCode)

        self.codeEdit = QLineEdit(self.tab)
        self.codeEdit.setObjectName(u"codeEdit")
        self.codeEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.codeEdit)

        self.nameEdit = QLineEdit(self.tab)
        self.nameEdit.setObjectName(u"nameEdit")
        self.nameEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameEdit)

        self.labelX = QLabel(self.tab)
        self.labelX.setObjectName(u"labelX")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelX)

        self.xEdit = QDoubleSpinBox(self.tab)
        self.xEdit.setObjectName(u"xEdit")
        self.xEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.xEdit.setDecimals(2)
        self.xEdit.setMinimum(-10000000.000000000000000)
        self.xEdit.setMaximum(10000000.000000000000000)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.xEdit)

        self.labelY = QLabel(self.tab)
        self.labelY.setObjectName(u"labelY")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelY)

        self.yEdit = QDoubleSpinBox(self.tab)
        self.yEdit.setObjectName(u"yEdit")
        self.yEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.yEdit.setDecimals(2)
        self.yEdit.setMinimum(-10000000.000000000000000)
        self.yEdit.setMaximum(10000000.000000000000000)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.yEdit)

        self.labelZ = QLabel(self.tab)
        self.labelZ.setObjectName(u"labelZ")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.labelZ)

        self.zEdit = QDoubleSpinBox(self.tab)
        self.zEdit.setObjectName(u"zEdit")
        self.zEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.zEdit.setDecimals(2)
        self.zEdit.setMinimum(-10000000.000000000000000)
        self.zEdit.setMaximum(10000000.000000000000000)

        self.formLayout.setWidget(4, QFormLayout.FieldRole, self.zEdit)

        self.labelVx = QLabel(self.tab)
        self.labelVx.setObjectName(u"labelVx")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.labelVx)

        self.vxEdit = QDoubleSpinBox(self.tab)
        self.vxEdit.setObjectName(u"vxEdit")
        self.vxEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.vxEdit.setDecimals(2)
        self.vxEdit.setMinimum(-1000.000000000000000)
        self.vxEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.vxEdit)

        self.labelVy = QLabel(self.tab)
        self.labelVy.setObjectName(u"labelVy")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.labelVy)

        self.vyEdit = QDoubleSpinBox(self.tab)
        self.vyEdit.setObjectName(u"vyEdit")
        self.vyEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.vyEdit.setDecimals(2)
        self.vyEdit.setMinimum(-1000.000000000000000)
        self.vyEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(6, QFormLayout.FieldRole, self.vyEdit)

        self.labelVz = QLabel(self.tab)
        self.labelVz.setObjectName(u"labelVz")

        self.formLayout.setWidget(7, QFormLayout.LabelRole, self.labelVz)

        self.vzEdit = QDoubleSpinBox(self.tab)
        self.vzEdit.setObjectName(u"vzEdit")
        self.vzEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.vzEdit.setDecimals(2)
        self.vzEdit.setMinimum(-1000.000000000000000)
        self.vzEdit.setMaximum(1000.000000000000000)

        self.formLayout.setWidget(7, QFormLayout.FieldRole, self.vzEdit)

        self.labelDiameter = QLabel(self.tab)
        self.labelDiameter.setObjectName(u"labelDiameter")

        self.formLayout.setWidget(8, QFormLayout.LabelRole, self.labelDiameter)

        self.diameterEdit = QDoubleSpinBox(self.tab)
        self.diameterEdit.setObjectName(u"diameterEdit")
        self.diameterEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.diameterEdit.setDecimals(2)
        self.diameterEdit.setMinimum(1.000000000000000)
        self.diameterEdit.setMaximum(1000.000000000000000)
        self.diameterEdit.setValue(20.000000000000000)

        self.formLayout.setWidget(8, QFormLayout.FieldRole, self.diameterEdit)

        self.labelSurfaceAccuracy = QLabel(self.tab)
        self.labelSurfaceAccuracy.setObjectName(u"labelSurfaceAccuracy")

        self.formLayout.setWidget(9, QFormLayout.LabelRole, self.labelSurfaceAccuracy)

        self.surfaceAccuracyEdit = QDoubleSpinBox(self.tab)
        self.surfaceAccuracyEdit.setObjectName(u"surfaceAccuracyEdit")
        self.surfaceAccuracyEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.surfaceAccuracyEdit.setDecimals(2)
        self.surfaceAccuracyEdit.setMinimum(0.000000000000000)
        self.surfaceAccuracyEdit.setMaximum(10000.000000000000000)

        self.formLayout.setWidget(9, QFormLayout.FieldRole, self.surfaceAccuracyEdit)

        self.labelElevationRange = QLabel(self.tab)
        self.labelElevationRange.setObjectName(u"labelElevationRange")

        self.formLayout.setWidget(10, QFormLayout.LabelRole, self.labelElevationRange)

        self.elevationRangeLayout = QHBoxLayout()
        self.elevationRangeLayout.setObjectName(u"elevationRangeLayout")
        self.elevationMinEdit = QDoubleSpinBox(self.tab)
        self.elevationMinEdit.setObjectName(u"elevationMinEdit")
        self.elevationMinEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.elevationMinEdit.setDecimals(2)
        self.elevationMinEdit.setMinimum(0.000000000000000)
        self.elevationMinEdit.setMaximum(90.000000000000000)

        self.elevationRangeLayout.addWidget(self.elevationMinEdit)

        self.elevationMaxEdit = QDoubleSpinBox(self.tab)
        self.elevationMaxEdit.setObjectName(u"elevationMaxEdit")
        self.elevationMaxEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.elevationMaxEdit.setDecimals(2)
        self.elevationMaxEdit.setMinimum(0.000000000000000)
        self.elevationMaxEdit.setMaximum(90.000000000000000)
        self.elevationMaxEdit.setValue(90.000000000000000)

        self.elevationRangeLayout.addWidget(self.elevationMaxEdit)


        self.formLayout.setLayout(10, QFormLayout.FieldRole, self.elevationRangeLayout)

        self.labelAzimuthRange = QLabel(self.tab)
        self.labelAzimuthRange.setObjectName(u"labelAzimuthRange")

        self.formLayout.setWidget(11, QFormLayout.LabelRole, self.labelAzimuthRange)

        self.azimuthRangeLayout = QHBoxLayout()
        self.azimuthRangeLayout.setObjectName(u"azimuthRangeLayout")
        self.azimuthMinEdit = QDoubleSpinBox(self.tab)
        self.azimuthMinEdit.setObjectName(u"azimuthMinEdit")
        self.azimuthMinEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.azimuthMinEdit.setDecimals(2)
        self.azimuthMinEdit.setMinimum(0.000000000000000)
        self.azimuthMinEdit.setMaximum(360.000000000000000)

        self.azimuthRangeLayout.addWidget(self.azimuthMinEdit)

        self.azimuthMaxEdit = QDoubleSpinBox(self.tab)
        self.azimuthMaxEdit.setObjectName(u"azimuthMaxEdit")
        self.azimuthMaxEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.azimuthMaxEdit.setDecimals(2)
        self.azimuthMaxEdit.setMinimum(0.000000000000000)
        self.azimuthMaxEdit.setMaximum(360.000000000000000)
        self.azimuthMaxEdit.setValue(360.000000000000000)

        self.azimuthRangeLayout.addWidget(self.azimuthMaxEdit)


        self.formLayout.setLayout(11, QFormLayout.FieldRole, self.azimuthRangeLayout)

        self.labelMountType = QLabel(self.tab)
        self.labelMountType.setObjectName(u"labelMountType")

        self.formLayout.setWidget(12, QFormLayout.LabelRole, self.labelMountType)

        self.mountTypeCombo = QComboBox(self.tab)
        self.mountTypeCombo.addItem("")
        self.mountTypeCombo.addItem("")
        self.mountTypeCombo.setObjectName(u"mountTypeCombo")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.mountTypeCombo.setFont(font)
        self.mountTypeCombo.setStyleSheet(u"QComboBox {\n"
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

        self.formLayout.setWidget(12, QFormLayout.FieldRole, self.mountTypeCombo)

        self.labelIsActive = QLabel(self.tab)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(13, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(self.tab)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setStyleSheet(u"/* \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0441\u0442\u0438\u043b\u044c QCheckBox */\n"
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
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(13, QFormLayout.FieldRole, self.isActiveCheckBox)

        self.labelName = QLabel(self.tab)
        self.labelName.setObjectName(u"labelName")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelName)


        self.gridLayout.addLayout(self.formLayout, 0, 0, 1, 1)

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
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(9)
        font1.setBold(False)
        self.labelSurfaceEfficiencyTable.setFont(font1)

        self.gridLayout_3.addWidget(self.labelSurfaceEfficiencyTable, 4, 0, 1, 1)

        self.sefdTable = QTableView(self.tab_2)
        self.sefdTable.setObjectName(u"sefdTable")
        self.sefdTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external border to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"   "
                        " border-right: none; /* Avoid doubling with adjacent sections */\n"
"    border-left: none; /* Clean look */\n"
"    border-top: none; /* Clean look */\n"
"    padding: 4px;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"}\n"
"\n"
"QHeaderView::section:horizontal {\n"
"    border-right: 1px solid #d3d3d3; /* Separator between columns */\n"
"}\n"
"\n"
"QHeaderView::section:vertical {\n"
"    border-bottom: 1px solid #d3d3d3; /* Separator between rows */\n"
"}\n"
"\n"
"QHeaderView::section:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}")
        self.sefdTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.sefdTable.setAlternatingRowColors(True)
        self.sefdTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sefdTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.sefdTable, 2, 0, 1, 2)

        self.labelSefdTable = QLabel(self.tab_2)
        self.labelSefdTable.setObjectName(u"labelSefdTable")
        self.labelSefdTable.setFont(font1)

        self.gridLayout_3.addWidget(self.labelSefdTable, 0, 0, 1, 1)

        self.surfaceEfficiencyTable = QTableView(self.tab_2)
        self.surfaceEfficiencyTable.setObjectName(u"surfaceEfficiencyTable")
        self.surfaceEfficiencyTable.setAutoFillBackground(False)
        self.surfaceEfficiencyTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external border to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"   "
                        " border-right: none; /* Avoid doubling with adjacent sections */\n"
"    border-left: none; /* Clean look */\n"
"    border-top: none; /* Clean look */\n"
"    padding: 4px;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"}\n"
"\n"
"QHeaderView::section:horizontal {\n"
"    border-right: 1px solid #d3d3d3; /* Separator between columns */\n"
"}\n"
"\n"
"QHeaderView::section:vertical {\n"
"    border-bottom: 1px solid #d3d3d3; /* Separator between rows */\n"
"}\n"
"\n"
"QHeaderView::section:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}")
        self.surfaceEfficiencyTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.surfaceEfficiencyTable.setAlternatingRowColors(True)
        self.surfaceEfficiencyTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.surfaceEfficiencyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.surfaceEfficiencyTable, 5, 0, 1, 2)

        self.effectiveAreaTable = QTableView(self.tab_2)
        self.effectiveAreaTable.setObjectName(u"effectiveAreaTable")
        self.effectiveAreaTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external border to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"   "
                        " border-right: none; /* Avoid doubling with adjacent sections */\n"
"    border-left: none; /* Clean look */\n"
"    border-top: none; /* Clean look */\n"
"    padding: 4px;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"}\n"
"\n"
"QHeaderView::section:horizontal {\n"
"    border-right: 1px solid #d3d3d3; /* Separator between columns */\n"
"}\n"
"\n"
"QHeaderView::section:vertical {\n"
"    border-bottom: 1px solid #d3d3d3; /* Separator between rows */\n"
"}\n"
"\n"
"QHeaderView::section:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}")
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
        self.systemTemperatureTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external border to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"   "
                        " border-right: none; /* Avoid doubling with adjacent sections */\n"
"    border-left: none; /* Clean look */\n"
"    border-top: none; /* Clean look */\n"
"    padding: 4px;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"}\n"
"\n"
"QHeaderView::section:horizontal {\n"
"    border-right: 1px solid #d3d3d3; /* Separator between columns */\n"
"}\n"
"\n"
"QHeaderView::section:vertical {\n"
"    border-bottom: 1px solid #d3d3d3; /* Separator between rows */\n"
"}\n"
"\n"
"QHeaderView::section:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}")
        self.systemTemperatureTable.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.systemTemperatureTable.setAlternatingRowColors(True)
        self.systemTemperatureTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.systemTemperatureTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.systemTemperatureTable, 13, 0, 1, 2)

        self.effectiveAreaButtonLayout = QHBoxLayout()
        self.effectiveAreaButtonLayout.setObjectName(u"effectiveAreaButtonLayout")
        self.addEffectiveAreaButton = QPushButton(self.tab_2)
        self.addEffectiveAreaButton.setObjectName(u"addEffectiveAreaButton")
        self.addEffectiveAreaButton.setStyleSheet(u"QPushButton {\n"
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

        self.effectiveAreaButtonLayout.addWidget(self.addEffectiveAreaButton)

        self.removeEffectiveAreaButton = QPushButton(self.tab_2)
        self.removeEffectiveAreaButton.setObjectName(u"removeEffectiveAreaButton")
        self.removeEffectiveAreaButton.setStyleSheet(u"QPushButton {\n"
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

        self.effectiveAreaButtonLayout.addWidget(self.removeEffectiveAreaButton)

        self.clearEffectiveAreaButton = QPushButton(self.tab_2)
        self.clearEffectiveAreaButton.setObjectName(u"clearEffectiveAreaButton")
        self.clearEffectiveAreaButton.setStyleSheet(u"QPushButton {\n"
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

        self.effectiveAreaButtonLayout.addWidget(self.clearEffectiveAreaButton)

        self.horizontalSpacerEffectiveArea = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.effectiveAreaButtonLayout.addItem(self.horizontalSpacerEffectiveArea)


        self.gridLayout_3.addLayout(self.effectiveAreaButtonLayout, 10, 0, 1, 2)

        self.surfaceEfficiencyButtonLayout = QHBoxLayout()
        self.surfaceEfficiencyButtonLayout.setObjectName(u"surfaceEfficiencyButtonLayout")
        self.addSurfaceEfficiencyButton = QPushButton(self.tab_2)
        self.addSurfaceEfficiencyButton.setObjectName(u"addSurfaceEfficiencyButton")
        self.addSurfaceEfficiencyButton.setStyleSheet(u"QPushButton {\n"
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

        self.surfaceEfficiencyButtonLayout.addWidget(self.addSurfaceEfficiencyButton)

        self.removeSurfaceEfficiencyButton = QPushButton(self.tab_2)
        self.removeSurfaceEfficiencyButton.setObjectName(u"removeSurfaceEfficiencyButton")
        self.removeSurfaceEfficiencyButton.setStyleSheet(u"QPushButton {\n"
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

        self.surfaceEfficiencyButtonLayout.addWidget(self.removeSurfaceEfficiencyButton)

        self.clearSurfaceEfficiencyButton = QPushButton(self.tab_2)
        self.clearSurfaceEfficiencyButton.setObjectName(u"clearSurfaceEfficiencyButton")
        self.clearSurfaceEfficiencyButton.setStyleSheet(u"QPushButton {\n"
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

        self.surfaceEfficiencyButtonLayout.addWidget(self.clearSurfaceEfficiencyButton)

        self.horizontalSpacerSurfaceEfficiency = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.surfaceEfficiencyButtonLayout.addItem(self.horizontalSpacerSurfaceEfficiency)


        self.gridLayout_3.addLayout(self.surfaceEfficiencyButtonLayout, 6, 0, 1, 2)

        self.labelSystemTemperatureTable = QLabel(self.tab_2)
        self.labelSystemTemperatureTable.setObjectName(u"labelSystemTemperatureTable")
        self.labelSystemTemperatureTable.setFont(font1)

        self.gridLayout_3.addWidget(self.labelSystemTemperatureTable, 12, 0, 1, 2)

        self.systemTemperatureButtonLayout = QHBoxLayout()
        self.systemTemperatureButtonLayout.setObjectName(u"systemTemperatureButtonLayout")
        self.addSystemTemperatureButton = QPushButton(self.tab_2)
        self.addSystemTemperatureButton.setObjectName(u"addSystemTemperatureButton")
        self.addSystemTemperatureButton.setStyleSheet(u"QPushButton {\n"
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

        self.systemTemperatureButtonLayout.addWidget(self.addSystemTemperatureButton)

        self.removeSystemTemperatureButton = QPushButton(self.tab_2)
        self.removeSystemTemperatureButton.setObjectName(u"removeSystemTemperatureButton")
        self.removeSystemTemperatureButton.setStyleSheet(u"QPushButton {\n"
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

        self.systemTemperatureButtonLayout.addWidget(self.removeSystemTemperatureButton)

        self.clearSystemTemperatureButton = QPushButton(self.tab_2)
        self.clearSystemTemperatureButton.setObjectName(u"clearSystemTemperatureButton")
        self.clearSystemTemperatureButton.setStyleSheet(u"QPushButton {\n"
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

        self.systemTemperatureButtonLayout.addWidget(self.clearSystemTemperatureButton)

        self.horizontalSpacerSystemTemperature = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.systemTemperatureButtonLayout.addItem(self.horizontalSpacerSystemTemperature)


        self.gridLayout_3.addLayout(self.systemTemperatureButtonLayout, 14, 0, 1, 2)

        self.labelEffectiveAreaTable = QLabel(self.tab_2)
        self.labelEffectiveAreaTable.setObjectName(u"labelEffectiveAreaTable")
        self.labelEffectiveAreaTable.setFont(font1)

        self.gridLayout_3.addWidget(self.labelEffectiveAreaTable, 8, 0, 1, 2)

        self.sefdButtonLayout = QHBoxLayout()
        self.sefdButtonLayout.setObjectName(u"sefdButtonLayout")
        self.addSefdButton = QPushButton(self.tab_2)
        self.addSefdButton.setObjectName(u"addSefdButton")
        self.addSefdButton.setStyleSheet(u"QPushButton {\n"
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

        self.sefdButtonLayout.addWidget(self.addSefdButton)

        self.removeSefdButton = QPushButton(self.tab_2)
        self.removeSefdButton.setObjectName(u"removeSefdButton")
        self.removeSefdButton.setStyleSheet(u"QPushButton {\n"
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

        self.sefdButtonLayout.addWidget(self.removeSefdButton)

        self.clearSefdButton = QPushButton(self.tab_2)
        self.clearSefdButton.setObjectName(u"clearSefdButton")
        self.clearSefdButton.setStyleSheet(u"QPushButton {\n"
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


        self.gridLayout_2.addLayout(self.buttonLayout, 2, 0, 1, 1)


        self.retranslateUi(TelescopeEditorDialog)
        self.saveButton.clicked.connect(TelescopeEditorDialog.accept)
        self.cancelButton.clicked.connect(TelescopeEditorDialog.reject)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(TelescopeEditorDialog)
    # setupUi

    def retranslateUi(self, TelescopeEditorDialog):
        TelescopeEditorDialog.setWindowTitle(QCoreApplication.translate("TelescopeEditorDialog", u"Edit Telescope", None))
        TelescopeEditorDialog.setStyleSheet(QCoreApplication.translate("TelescopeEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelCode.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Code:", None))
        self.codeEdit.setPlaceholderText(QCoreApplication.translate("TelescopeEditorDialog", u"Enter telescope code", None))
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
        self.labelName.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Name:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("TelescopeEditorDialog", u"Main Parameters", None))
        self.labelSurfaceEfficiencyTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Surface Efficiency Table (MHz, Efficiency):", None))
        self.labelSefdTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"SEFD Table (MHz, Jy):", None))
        self.addEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearEffectiveAreaButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.addSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearSurfaceEfficiencyButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.labelSystemTemperatureTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"System Temperature Table (MHz, K):", None))
        self.addSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearSystemTemperatureButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.labelEffectiveAreaTable.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Effective Area Table (MHz, m\u00b2):", None))
        self.addSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Add", None))
        self.removeSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Remove", None))
        self.clearSefdButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Clear", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("TelescopeEditorDialog", u"Sensitivity", None))
        self.saveButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("TelescopeEditorDialog", u"Cancel", None))
    # retranslateUi

