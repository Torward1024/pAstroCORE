# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_calculationsBaRfXt.ui'
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
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QWidget)

class Ui_CalculationDialog(object):
    def setupUi(self, CalculationDialog):
        if not CalculationDialog.objectName():
            CalculationDialog.setObjectName(u"CalculationDialog")
        CalculationDialog.resize(420, 416)
        icon = QIcon()
        icon.addFile(u":/icons/calculate.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CalculationDialog.setWindowIcon(icon)
        CalculationDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        CalculationDialog.setModal(True)
        self.gridLayout_3 = QGridLayout(CalculationDialog)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.labelCalculations = QLabel(CalculationDialog)
        self.labelCalculations.setObjectName(u"labelCalculations")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(True)
        self.labelCalculations.setFont(font)

        self.gridLayout_3.addWidget(self.labelCalculations, 0, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.selectAllButton = QPushButton(CalculationDialog)
        self.selectAllButton.setObjectName(u"selectAllButton")
        self.selectAllButton.setStyleSheet(u"QPushButton {\n"
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
        self.selectAllButton.setFlat(True)

        self.horizontalLayout.addWidget(self.selectAllButton)


        self.gridLayout.addLayout(self.horizontalLayout, 6, 0, 1, 1)

        self.labelParameters = QLabel(CalculationDialog)
        self.labelParameters.setObjectName(u"labelParameters")
        self.labelParameters.setFont(font)

        self.gridLayout.addWidget(self.labelParameters, 2, 1, 1, 1)

        self.labelTargets = QLabel(CalculationDialog)
        self.labelTargets.setObjectName(u"labelTargets")

        self.gridLayout.addWidget(self.labelTargets, 2, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.labelTimestep = QLabel(CalculationDialog)
        self.labelTimestep.setObjectName(u"labelTimestep")

        self.gridLayout_2.addWidget(self.labelTimestep, 0, 0, 1, 1)

        self.timeStepSpin = QDoubleSpinBox(CalculationDialog)
        self.timeStepSpin.setObjectName(u"timeStepSpin")
        self.timeStepSpin.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
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
        self.timeStepSpin.setMinimum(1.000000000000000)
        self.timeStepSpin.setMaximum(3600.000000000000000)
        self.timeStepSpin.setValue(600.000000000000000)

        self.gridLayout_2.addWidget(self.timeStepSpin, 0, 1, 1, 1)

        self.recalculateCheck = QCheckBox(CalculationDialog)
        self.recalculateCheck.setObjectName(u"recalculateCheck")

        self.gridLayout_2.addWidget(self.recalculateCheck, 1, 0, 1, 2)


        self.gridLayout.addLayout(self.gridLayout_2, 3, 1, 1, 1)

        self.targetList = QListWidget(CalculationDialog)
        self.targetList.setObjectName(u"targetList")
        self.targetList.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"    padding: 0; /* Ensure no default padding */\n"
"}\n"
"\n"
"QTableView::item, QTableWidget::item {\n"
"    padding: 4px; /* Consistent padding for normal state */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Consistent padding for selected state */\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Explicitly set same padding to avoid shift */\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external bord"
                        "er to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"    border-right: none; /* Avoid doubling with adjacent sections */\n"
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
"    padding: 4px; /* Explicitly set same padding to avoid shift */\n"
"}")
        self.targetList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.targetList, 3, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout, 2, 0, 1, 1)

        self.calcTable = QTableWidget(CalculationDialog)
        if (self.calcTable.columnCount() < 4):
            self.calcTable.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.calcTable.setObjectName(u"calcTable")
        self.calcTable.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
"\n"
"/* Table View */\n"
"QTableView, QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3; /* External border for table */\n"
"    padding: 0; /* Ensure no default padding */\n"
"}\n"
"\n"
"QTableView::item, QTableWidget::item {\n"
"    padding: 4px; /* Consistent padding for normal state */\n"
"}\n"
"\n"
"QTableView::item:selected, QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Consistent padding for selected state */\n"
"}\n"
"\n"
"QTableView::item:hover, QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"    padding: 4px; /* Explicitly set same padding to avoid shift */\n"
"}\n"
"\n"
"/* Header View */\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none; /* No external bord"
                        "er to avoid doubling with QTableView */\n"
"    border-bottom: 1px solid #d3d3d3; /* Bottom border to separate from content */\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none; /* No bottom border, handled by QHeaderView */\n"
"    border-right: none; /* Avoid doubling with adjacent sections */\n"
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
"    padding: 4px; /* Explicitly set same padding to avoid shift */\n"
"}")

        self.gridLayout_3.addWidget(self.calcTable, 1, 0, 1, 1)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.calcButton = QPushButton(CalculationDialog)
        self.calcButton.setObjectName(u"calcButton")
        self.calcButton.setStyleSheet(u"QPushButton {\n"
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
        self.calcButton.setAutoDefault(False)
        self.calcButton.setFlat(True)

        self.buttonLayout.addWidget(self.calcButton)

        self.cancelButton = QPushButton(CalculationDialog)
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


        self.gridLayout_3.addLayout(self.buttonLayout, 3, 0, 1, 1)


        self.retranslateUi(CalculationDialog)

        QMetaObject.connectSlotsByName(CalculationDialog)
    # setupUi

    def retranslateUi(self, CalculationDialog):
        CalculationDialog.setWindowTitle(QCoreApplication.translate("CalculationDialog", u"Perform Calculations", None))
        self.labelCalculations.setText(QCoreApplication.translate("CalculationDialog", u"Calculations:", None))
        self.selectAllButton.setText(QCoreApplication.translate("CalculationDialog", u"Select All", None))
        self.labelParameters.setText(QCoreApplication.translate("CalculationDialog", u"Parameters:", None))
        self.labelTargets.setText(QCoreApplication.translate("CalculationDialog", u"Observations:", None))
        self.labelTimestep.setText(QCoreApplication.translate("CalculationDialog", u"Time step (s):", None))
        self.recalculateCheck.setText(QCoreApplication.translate("CalculationDialog", u"Recalculate", None))
        ___qtablewidgetitem = self.calcTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("CalculationDialog", u"Select", None));
        ___qtablewidgetitem1 = self.calcTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("CalculationDialog", u"Calculation Type", None));
        ___qtablewidgetitem2 = self.calcTable.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("CalculationDialog", u"Status", None));
        ___qtablewidgetitem3 = self.calcTable.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("CalculationDialog", u"Dependencies", None));
        self.calcButton.setText(QCoreApplication.translate("CalculationDialog", u"Calculate", None))
        self.cancelButton.setText(QCoreApplication.translate("CalculationDialog", u"Cancel", None))
    # retranslateUi