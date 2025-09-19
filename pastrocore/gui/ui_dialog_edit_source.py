# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_edtior_sourceKgFpYX.ui'
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

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.nameEdit)

        self.labelNameJ2000 = QLabel(SourceEditorDialog)
        self.labelNameJ2000.setObjectName(u"labelNameJ2000")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelNameJ2000)

        self.nameJ2000Edit = QLineEdit(SourceEditorDialog)
        self.nameJ2000Edit.setObjectName(u"nameJ2000Edit")
        self.nameJ2000Edit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.nameJ2000Edit)

        self.labelAltName = QLabel(SourceEditorDialog)
        self.labelAltName.setObjectName(u"labelAltName")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelAltName)

        self.altNameEdit = QLineEdit(SourceEditorDialog)
        self.altNameEdit.setObjectName(u"altNameEdit")
        self.altNameEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.altNameEdit)

        self.labelRa = QLabel(SourceEditorDialog)
        self.labelRa.setObjectName(u"labelRa")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelRa)

        self.raLayout = QHBoxLayout()
        self.raLayout.setObjectName(u"raLayout")
        self.raHEdit = QDoubleSpinBox(SourceEditorDialog)
        self.raHEdit.setObjectName(u"raHEdit")
        self.raHEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.raHEdit.setDecimals(0)
        self.raHEdit.setMaximum(23.000000000000000)

        self.raLayout.addWidget(self.raHEdit)

        self.raMEdit = QDoubleSpinBox(SourceEditorDialog)
        self.raMEdit.setObjectName(u"raMEdit")
        self.raMEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.raMEdit.setDecimals(0)
        self.raMEdit.setMaximum(59.000000000000000)

        self.raLayout.addWidget(self.raMEdit)

        self.raSEdit = QDoubleSpinBox(SourceEditorDialog)
        self.raSEdit.setObjectName(u"raSEdit")
        self.raSEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.deDEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.deDEdit.setDecimals(0)
        self.deDEdit.setMinimum(-90.000000000000000)
        self.deDEdit.setMaximum(90.000000000000000)

        self.decLayout.addWidget(self.deDEdit)

        self.deMEdit = QDoubleSpinBox(SourceEditorDialog)
        self.deMEdit.setObjectName(u"deMEdit")
        self.deMEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.deMEdit.setDecimals(0)
        self.deMEdit.setMaximum(59.000000000000000)

        self.decLayout.addWidget(self.deMEdit)

        self.deSEdit = QDoubleSpinBox(SourceEditorDialog)
        self.deSEdit.setObjectName(u"deSEdit")
        self.deSEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.deSEdit.setDecimals(3)
        self.deSEdit.setMaximum(59.999000000000002)

        self.decLayout.addWidget(self.deSEdit)


        self.formLayout.setLayout(4, QFormLayout.FieldRole, self.decLayout)

        self.labelSpectralIndex = QLabel(SourceEditorDialog)
        self.labelSpectralIndex.setObjectName(u"labelSpectralIndex")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.labelSpectralIndex)

        self.spectralIndexEdit = QDoubleSpinBox(SourceEditorDialog)
        self.spectralIndexEdit.setObjectName(u"spectralIndexEdit")
        self.spectralIndexEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.spectralIndexEdit.setDecimals(3)
        self.spectralIndexEdit.setMinimum(-999.000000000000000)
        self.spectralIndexEdit.setMaximum(999.000000000000000)

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.spectralIndexEdit)

        self.labelIsActive = QLabel(SourceEditorDialog)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(SourceEditorDialog)
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
        self.removeFluxButton.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout.addWidget(self.removeFluxButton)

        self.clearFluxButton = QPushButton(SourceEditorDialog)
        self.clearFluxButton.setObjectName(u"clearFluxButton")
        self.clearFluxButton.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout.addWidget(self.clearFluxButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.fluxTable = QTableView(SourceEditorDialog)
        self.fluxTable.setObjectName(u"fluxTable")
        self.fluxTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
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
        self.addFluxButton.setStyleSheet(QCoreApplication.translate("SourceEditorDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.addFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Add", None))
        self.removeFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Remove", None))
        self.clearFluxButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Clear", None))
        self.labelFluxTable.setText(QCoreApplication.translate("SourceEditorDialog", u"Flux Table (MHz, Jy):", None))
        self.saveButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("SourceEditorDialog", u"Cancel", None))
    # retranslateUi