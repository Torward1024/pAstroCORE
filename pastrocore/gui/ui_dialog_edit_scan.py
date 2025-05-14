# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_scanuwVTBR.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
    QDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableView, QWidget)

class Ui_ScanEditorDialog(object):
    def setupUi(self, ScanEditorDialog):
        if not ScanEditorDialog.objectName():
            ScanEditorDialog.setObjectName(u"ScanEditorDialog")
        ScanEditorDialog.resize(433, 518)
        ScanEditorDialog.setModal(True)
        self.gridLayout = QGridLayout(ScanEditorDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.labelSource = QLabel(ScanEditorDialog)
        self.labelSource.setObjectName(u"labelSource")

        self.gridLayout.addWidget(self.labelSource, 1, 0, 1, 1)

        self.labelDuration = QLabel(ScanEditorDialog)
        self.labelDuration.setObjectName(u"labelDuration")

        self.gridLayout.addWidget(self.labelDuration, 6, 0, 1, 1)

        self.lbl_active = QLabel(ScanEditorDialog)
        self.lbl_active.setObjectName(u"lbl_active")

        self.gridLayout.addWidget(self.lbl_active, 7, 0, 1, 1)

        self.chk_active = QCheckBox(ScanEditorDialog)
        self.chk_active.setObjectName(u"chk_active")

        self.gridLayout.addWidget(self.chk_active, 7, 1, 1, 1)

        self.startTimeEdit = QDateTimeEdit(ScanEditorDialog)
        self.startTimeEdit.setObjectName(u"startTimeEdit")
        self.startTimeEdit.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDateTime {\n"
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
"QDateTime:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDateTime:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state */\n"
"QDateTi"
                        "me:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDateTime:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDateTime:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDateTime::up-button, QDateTime::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDateTime::up-button:hover, QDoubleSpinBox::down-button"
                        ":hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDateTime::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDateTime::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.startTimeEdit.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0, 0)))

        self.gridLayout.addWidget(self.startTimeEdit, 3, 1, 1, 3)

        self.labelStartTime = QLabel(ScanEditorDialog)
        self.labelStartTime.setObjectName(u"labelStartTime")

        self.gridLayout.addWidget(self.labelStartTime, 3, 0, 1, 1)

        self.sourceCombo = QComboBox(ScanEditorDialog)
        self.sourceCombo.setObjectName(u"sourceCombo")
        self.sourceCombo.setStyleSheet(u"QComboBox {\n"
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

        self.gridLayout.addWidget(self.sourceCombo, 1, 1, 1, 3)

        self.tab_telescopes = QTableView(ScanEditorDialog)
        self.tab_telescopes.setObjectName(u"tab_telescopes")
        self.tab_telescopes.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
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

        self.gridLayout.addWidget(self.tab_telescopes, 12, 0, 1, 4)

        self.durationEdit = QLineEdit(ScanEditorDialog)
        self.durationEdit.setObjectName(u"durationEdit")
        self.durationEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.gridLayout.addWidget(self.durationEdit, 6, 1, 1, 3)

        self.lbl_offsource = QLabel(ScanEditorDialog)
        self.lbl_offsource.setObjectName(u"lbl_offsource")

        self.gridLayout.addWidget(self.lbl_offsource, 2, 0, 1, 1)

        self.chk_offsource = QCheckBox(ScanEditorDialog)
        self.chk_offsource.setObjectName(u"chk_offsource")

        self.gridLayout.addWidget(self.chk_offsource, 2, 1, 1, 1)

        self.label_2 = QLabel(ScanEditorDialog)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 13, 0, 1, 1)

        self.label = QLabel(ScanEditorDialog)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 8, 0, 1, 1)

        self.tab_frequencies = QTableView(ScanEditorDialog)
        self.tab_frequencies.setObjectName(u"tab_frequencies")
        self.tab_frequencies.setStyleSheet(u"/* QTableView and QHeaderView styles for pAstroCORE */\n"
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

        self.gridLayout.addWidget(self.tab_frequencies, 14, 0, 1, 4)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(ScanEditorDialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setStyleSheet(u"QPushButton {\n"
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
        self.pushButton.setAutoDefault(False)
        self.pushButton.setFlat(True)

        self.horizontalLayout.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton(ScanEditorDialog)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setStyleSheet(u"QPushButton {\n"
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
        self.pushButton_2.setAutoDefault(True)
        self.pushButton_2.setFlat(True)

        self.horizontalLayout.addWidget(self.pushButton_2)


        self.gridLayout.addLayout(self.horizontalLayout, 15, 0, 1, 4)


        self.retranslateUi(ScanEditorDialog)

        QMetaObject.connectSlotsByName(ScanEditorDialog)
    # setupUi

    def retranslateUi(self, ScanEditorDialog):
        ScanEditorDialog.setWindowTitle(QCoreApplication.translate("ScanEditorDialog", u"Edit Scan", None))
        ScanEditorDialog.setStyleSheet(QCoreApplication.translate("ScanEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelSource.setText(QCoreApplication.translate("ScanEditorDialog", u"Source:", None))
        self.labelDuration.setText(QCoreApplication.translate("ScanEditorDialog", u"Duration (s):", None))
        self.lbl_active.setText(QCoreApplication.translate("ScanEditorDialog", u"Active:", None))
        self.chk_active.setText("")
        self.labelStartTime.setText(QCoreApplication.translate("ScanEditorDialog", u"Start Time:", None))
        self.lbl_offsource.setText(QCoreApplication.translate("ScanEditorDialog", u"Off source scan:", None))
        self.chk_offsource.setText("")
        self.label_2.setText(QCoreApplication.translate("ScanEditorDialog", u"<html><head/><body><p><span style=\" font-weight:700;\">Frequencies:</span></p></body></html>", None))
        self.label.setText(QCoreApplication.translate("ScanEditorDialog", u"<html><head/><body><p><span style=\" font-weight:700;\">Telescopes:</span></p></body></html>", None))
        self.pushButton.setText(QCoreApplication.translate("ScanEditorDialog", u"\u041e\u041a", None))
        self.pushButton_2.setText(QCoreApplication.translate("ScanEditorDialog", u"Cancel", None))
    # retranslateUi