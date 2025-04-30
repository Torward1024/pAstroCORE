# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_scanbducgq.ui'
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
    QDialog, QGridLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTableView,
    QWidget)

class Ui_ScanEditorDialog(object):
    def setupUi(self, ScanEditorDialog):
        if not ScanEditorDialog.objectName():
            ScanEditorDialog.setObjectName(u"ScanEditorDialog")
        ScanEditorDialog.resize(600, 400)
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpenRecent))
        ScanEditorDialog.setWindowIcon(icon)
        self.gridLayout = QGridLayout(ScanEditorDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.gridLayout.setSpacing(6)

        self.labelSource = QLabel(ScanEditorDialog)
        self.labelSource.setObjectName(u"labelSource")
        self.gridLayout.addWidget(self.labelSource, 0, 0, 1, 1)

        self.sourceCombo = QComboBox(ScanEditorDialog)
        self.sourceCombo.setObjectName(u"sourceCombo")
        self.sourceCombo.setStyleSheet(u"""
            QComboBox {
                font-family: Arial;
                font-size: 9pt;
                color: #333333;
                padding: 4px;
                border-radius: 3px;
                background-color: #f9f9f9;
                border: 1px solid #d3d3d3;
            }
            QComboBox:editable, QComboBox:!editable {
                background-color: #f0f6ff;
                border: 1px solid #0078d7;
            }
            QComboBox:hover {
                border: 1px solid #1a8cff;
            }
            QComboBox:focus {
                border: 1px solid #005bb5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                width: 20px;
                border-left: 1px solid #d3d3d3;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                background-color: #f9f9f9;
            }
            QComboBox::drop-down:hover {
                background-color: #0078d7;
            }
            QComboBox QAbstractItemView {
                font-family: Arial;
                font-size: 9pt;
                color: #333333;
                background-color: #ffffff;
                border: 1px solid #d3d3d3;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
                padding: 4px;
            }
        """)
        self.gridLayout.addWidget(self.sourceCombo, 0, 1, 1, 3)

        self.lbl_offsource = QLabel(ScanEditorDialog)
        self.lbl_offsource.setObjectName(u"lbl_offsource")
        self.gridLayout.addWidget(self.lbl_offsource, 1, 0, 1, 1)

        self.chk_offsource = QCheckBox(ScanEditorDialog)
        self.chk_offsource.setObjectName(u"chk_offsource")
        self.gridLayout.addWidget(self.chk_offsource, 1, 1, 1, 1)

        self.labelStartTime = QLabel(ScanEditorDialog)
        self.labelStartTime.setObjectName(u"labelStartTime")
        self.gridLayout.addWidget(self.labelStartTime, 2, 0, 1, 1)

        self.startTimeEdit = QDateTimeEdit(ScanEditorDialog)
        self.startTimeEdit.setObjectName(u"startTimeEdit")
        self.startTimeEdit.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0, 0)))
        self.startTimeEdit.setStyleSheet(u"""
            QDateTimeEdit {
                font-family: Arial;
                font-size: 9pt;
                color: #333333;
                padding: 4px;
                border-radius: 3px;
                background-color: #f0f6ff;
                border: 1px solid #0078d7;
            }
            QDateTimeEdit:hover {
                border: 1px solid #1a8cff;
            }
            QDateTimeEdit:focus {
                border: 1px solid #005bb5;
                background-color: #ffffff;
            }
        """)
        self.gridLayout.addWidget(self.startTimeEdit, 2, 1, 1, 3)

        self.labelDuration = QLabel(ScanEditorDialog)
        self.labelDuration.setObjectName(u"labelDuration")
        self.gridLayout.addWidget(self.labelDuration, 3, 0, 1, 1)

        self.durationEdit = QLineEdit(ScanEditorDialog)
        self.durationEdit.setObjectName(u"durationEdit")
        self.durationEdit.setStyleSheet(u"""
            QLineEdit {
                font-family: Arial;
                font-size: 9pt;
                color: #333333;
                padding: 4px;
                border-radius: 3px;
            }
            QLineEdit[readOnly="true"] {
                border: 1px solid #d3d3d3;
                background-color: #f9f9f9;
            }
            QLineEdit[readOnly="false"] {
                border: 1px solid #0078d7;
                background-color: #f0f6ff;
            }
            QLineEdit[readOnly="false"]:hover {
                border: 1px solid #1a8cff;
            }
            QLineEdit[readOnly="false"]:focus {
                border: 1px solid #005bb5;
                background-color: #ffffff;
            }
        """)
        self.gridLayout.addWidget(self.durationEdit, 3, 1, 1, 3)

        self.lbl_active = QLabel(ScanEditorDialog)
        self.lbl_active.setObjectName(u"lbl_active")
        self.gridLayout.addWidget(self.lbl_active, 4, 0, 1, 1)

        self.chk_active = QCheckBox(ScanEditorDialog)
        self.chk_active.setObjectName(u"chk_active")
        self.gridLayout.addWidget(self.chk_active, 4, 1, 1, 1)

        self.label = QLabel(ScanEditorDialog)
        self.label.setObjectName(u"label")
        self.gridLayout.addWidget(self.label, 5, 0, 1, 1)

        self.label_2 = QLabel(ScanEditorDialog)
        self.label_2.setObjectName(u"label_2")
        self.gridLayout.addWidget(self.label_2, 5, 1, 1, 1)

        self.tab_telescopes = QTableView(ScanEditorDialog)
        self.tab_telescopes.setObjectName(u"tab_telescopes")
        self.tab_telescopes.setStyleSheet(u"""
            QTableView {
                border: 1px solid #d3d3d3;
                background-color: #ffffff;
                font-family: Arial;
                font-size: 9pt;
                alternate-background-color: #f9f9f9;
            }
            QTableView::item {
                padding: 4px;
            }
            QTableView::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f0f6ff;
                border: 1px solid #d3d3d3;
                padding: 4px;
                font-family: Arial;
                font-size: 9pt;
            }
            QTableView QTableCornerButton::section {
                background-color: #f0f6ff;
                border: 1px solid #d3d3d3;
            }
        """)
        self.gridLayout.addWidget(self.tab_telescopes, 6, 0, 1, 1)

        self.tab_frequencies = QTableView(ScanEditorDialog)
        self.tab_frequencies.setObjectName(u"tab_frequencies")
        self.tab_frequencies.setStyleSheet(u"""
            QTableView {
                border: 1px solid #d3d3d3;
                background-color: #ffffff;
                font-family: Arial;
                font-size: 9pt;
                alternate-background-color: #f9f9f9;
            }
            QTableView::item {
                padding: 4px;
            }
            QTableView::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f0f6ff;
                border: 1px solid #d3d3d3;
                padding: 4px;
                font-family: Arial;
                font-size: 9pt;
            }
            QTableView QTableCornerButton::section {
                background-color: #f0f6ff;
                border: 1px solid #d3d3d3;
            }
        """)
        self.gridLayout.addWidget(self.tab_frequencies, 6, 1, 1, 1)

        self.pushButton = QPushButton(ScanEditorDialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setStyleSheet(u"""
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                padding: 6px;
                border-radius: 3px;
                border: none;
                font-family: Arial;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #1a8cff;
            }
            QPushButton:pressed {
                background-color: #005bb5;
                padding-top: 7px;
                padding-bottom: 5px;
            }
        """)
        self.pushButton.setAutoDefault(False)
        self.pushButton.setFlat(True)
        self.gridLayout.addWidget(self.pushButton, 7, 2, 1, 1)

        self.pushButton_2 = QPushButton(ScanEditorDialog)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setStyleSheet(u"""
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                padding: 6px;
                border-radius: 3px;
                border: none;
                font-family: Arial;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #1a8cff;
            }
            QPushButton:pressed {
                background-color: #005bb5;
                padding-top: 7px;
                padding-bottom: 5px;
            }
        """)
        self.pushButton_2.setAutoDefault(True)
        self.pushButton_2.setFlat(True)
        self.gridLayout.addWidget(self.pushButton_2, 7, 3, 1, 1)

        self.retranslateUi(ScanEditorDialog)

        QMetaObject.connectSlotsByName(ScanEditorDialog)
    # setupUi

    def retranslateUi(self, ScanEditorDialog):
        ScanEditorDialog.setWindowTitle(QCoreApplication.translate("ScanEditorDialog", u"Edit Scan", None))
        ScanEditorDialog.setStyleSheet(QCoreApplication.translate("ScanEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelSource.setText(QCoreApplication.translate("ScanEditorDialog", u"Source:", None))
        self.lbl_offsource.setText(QCoreApplication.translate("ScanEditorDialog", u"Off source scan:", None))
        self.labelStartTime.setText(QCoreApplication.translate("ScanEditorDialog", u"Start Time:", None))
        self.labelDuration.setText(QCoreApplication.translate("ScanEditorDialog", u"Duration (s):", None))
        self.lbl_active.setText(QCoreApplication.translate("ScanEditorDialog", u"Active:", None))
        self.chk_active.setText("")
        self.chk_offsource.setText("")
        self.label.setText(QCoreApplication.translate("ScanEditorDialog", u"Telescopes:", None))
        self.label_2.setText(QCoreApplication.translate("ScanEditorDialog", u"Frequencies:", None))
        self.pushButton.setText(QCoreApplication.translate("ScanEditorDialog", u"OK", None))
        self.pushButton_2.setText(QCoreApplication.translate("ScanEditorDialog", u"Cancel", None))
    # retranslateUi