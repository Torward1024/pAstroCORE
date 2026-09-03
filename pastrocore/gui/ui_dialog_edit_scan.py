# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_scan.ui'
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
    QDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableView, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_ScanEditorDialog(object):
    def setupUi(self, ScanEditorDialog):
        if not ScanEditorDialog.objectName():
            ScanEditorDialog.setObjectName(u"ScanEditorDialog")
        ScanEditorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        ScanEditorDialog.resize(560, 420)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ScanEditorDialog.sizePolicy().hasHeightForWidth())
        ScanEditorDialog.setSizePolicy(sizePolicy)
        ScanEditorDialog.setMinimumSize(QSize(560, 420))
        ScanEditorDialog.setMaximumSize(QSize(560, 420))
        icon = QIcon()
        icon.addFile(u":/icons/edit_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        ScanEditorDialog.setWindowIcon(icon)
        ScanEditorDialog.setModal(True)
        self.gridLayout = QGridLayout(ScanEditorDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lbl_offsource = QLabel(ScanEditorDialog)
        self.lbl_offsource.setObjectName(u"lbl_offsource")

        self.gridLayout.addWidget(self.lbl_offsource, 2, 0, 1, 1)

        self.line = QFrame(ScanEditorDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 10, 0, 1, 4)

        self.durationEdit = QLineEdit(ScanEditorDialog)
        self.durationEdit.setObjectName(u"durationEdit")
        self.durationEdit.setInputMask(u"")
        self.durationEdit.setText(u"")
        self.durationEdit.setMaxLength(999999999)
        self.durationEdit.setPlaceholderText(u"")

        self.gridLayout.addWidget(self.durationEdit, 8, 1, 1, 3)

        self.chk_active = QCheckBox(ScanEditorDialog)
        self.chk_active.setObjectName(u"chk_active")

        self.gridLayout.addWidget(self.chk_active, 9, 1, 1, 1)

        self.chk_offsource = QCheckBox(ScanEditorDialog)
        self.chk_offsource.setObjectName(u"chk_offsource")

        self.gridLayout.addWidget(self.chk_offsource, 2, 1, 1, 1)

        self.line_2 = QFrame(ScanEditorDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 20, 0, 1, 4)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(ScanEditorDialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setAutoDefault(False)
        self.pushButton.setFlat(True)

        self.horizontalLayout.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton(ScanEditorDialog)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setAutoDefault(True)
        self.pushButton_2.setFlat(True)

        self.horizontalLayout.addWidget(self.pushButton_2)


        self.gridLayout.addLayout(self.horizontalLayout, 21, 0, 1, 4)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.btnClearAllTelescopes = QPushButton(ScanEditorDialog)
        self.btnClearAllTelescopes.setObjectName(u"btnClearAllTelescopes")

        self.gridLayout_2.addWidget(self.btnClearAllTelescopes, 2, 1, 1, 1)

        self.btnSelectAllFrequencies = QPushButton(ScanEditorDialog)
        self.btnSelectAllFrequencies.setObjectName(u"btnSelectAllFrequencies")

        self.gridLayout_2.addWidget(self.btnSelectAllFrequencies, 2, 3, 1, 1)

        self.btnSelectAllTelescopes = QPushButton(ScanEditorDialog)
        self.btnSelectAllTelescopes.setObjectName(u"btnSelectAllTelescopes")

        self.gridLayout_2.addWidget(self.btnSelectAllTelescopes, 2, 0, 1, 1)

        self.tab_telescopes = QTableView(ScanEditorDialog)
        self.tab_telescopes.setObjectName(u"tab_telescopes")

        self.gridLayout_2.addWidget(self.tab_telescopes, 1, 0, 1, 2)

        self.label = QLabel(ScanEditorDialog)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 2)

        self.btnClearAllFrequencies = QPushButton(ScanEditorDialog)
        self.btnClearAllFrequencies.setObjectName(u"btnClearAllFrequencies")

        self.gridLayout_2.addWidget(self.btnClearAllFrequencies, 2, 4, 1, 1)

        self.tab_frequencies = QTableView(ScanEditorDialog)
        self.tab_frequencies.setObjectName(u"tab_frequencies")

        self.gridLayout_2.addWidget(self.tab_frequencies, 1, 3, 1, 2)

        self.label_2 = QLabel(ScanEditorDialog)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 0, 3, 1, 2)

        self.line_3 = QFrame(ScanEditorDialog)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.VLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_3, 0, 2, 3, 1)


        self.gridLayout.addLayout(self.gridLayout_2, 16, 0, 1, 4)

        self.labelDuration = QLabel(ScanEditorDialog)
        self.labelDuration.setObjectName(u"labelDuration")

        self.gridLayout.addWidget(self.labelDuration, 8, 0, 1, 1)

        self.labelSource = QLabel(ScanEditorDialog)
        self.labelSource.setObjectName(u"labelSource")

        self.gridLayout.addWidget(self.labelSource, 1, 0, 1, 1)

        self.lbl_active = QLabel(ScanEditorDialog)
        self.lbl_active.setObjectName(u"lbl_active")

        self.gridLayout.addWidget(self.lbl_active, 9, 0, 1, 1)

        self.sourceCombo = QComboBox(ScanEditorDialog)
        self.sourceCombo.setObjectName(u"sourceCombo")

        self.gridLayout.addWidget(self.sourceCombo, 1, 1, 1, 3)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.labelStartTime = QLabel(ScanEditorDialog)
        self.labelStartTime.setObjectName(u"labelStartTime")

        self.horizontalLayout_2.addWidget(self.labelStartTime)

        self.startTimeEdit = QDateTimeEdit(ScanEditorDialog)
        self.startTimeEdit.setObjectName(u"startTimeEdit")
        self.startTimeEdit.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0, 0)))

        self.horizontalLayout_2.addWidget(self.startTimeEdit)

        self.labelEndTime = QLabel(ScanEditorDialog)
        self.labelEndTime.setObjectName(u"labelEndTime")

        self.horizontalLayout_2.addWidget(self.labelEndTime)

        self.endTimeEdit = QDateTimeEdit(ScanEditorDialog)
        self.endTimeEdit.setObjectName(u"endTimeEdit")

        self.horizontalLayout_2.addWidget(self.endTimeEdit)


        self.gridLayout.addLayout(self.horizontalLayout_2, 4, 0, 2, 4)


        self.retranslateUi(ScanEditorDialog)

        QMetaObject.connectSlotsByName(ScanEditorDialog)
    # setupUi

    def retranslateUi(self, ScanEditorDialog):
        ScanEditorDialog.setWindowTitle(QCoreApplication.translate("ScanEditorDialog", u"Edit Scan", None))
        self.lbl_offsource.setText(QCoreApplication.translate("ScanEditorDialog", u"Off source scan:", None))
        self.chk_active.setText("")
        self.chk_offsource.setText("")
        self.pushButton.setText(QCoreApplication.translate("ScanEditorDialog", u"\u041e\u041a", None))
        self.pushButton_2.setText(QCoreApplication.translate("ScanEditorDialog", u"Cancel", None))
        self.btnClearAllTelescopes.setText(QCoreApplication.translate("ScanEditorDialog", u"Clear", None))
        self.btnSelectAllFrequencies.setText(QCoreApplication.translate("ScanEditorDialog", u"Select All", None))
        self.btnSelectAllTelescopes.setText(QCoreApplication.translate("ScanEditorDialog", u"Select All", None))
        self.label.setText(QCoreApplication.translate("ScanEditorDialog", u"<html><head/><body><p>Telescopes:</p></body></html>", None))
        self.btnClearAllFrequencies.setText(QCoreApplication.translate("ScanEditorDialog", u"Clear", None))
        self.label_2.setText(QCoreApplication.translate("ScanEditorDialog", u"<html><head/><body><p>Frequencies:</p></body></html>", None))
        self.labelDuration.setText(QCoreApplication.translate("ScanEditorDialog", u"Duration (s):", None))
        self.labelSource.setText(QCoreApplication.translate("ScanEditorDialog", u"Source:", None))
        self.lbl_active.setText(QCoreApplication.translate("ScanEditorDialog", u"Active:", None))
        self.labelStartTime.setText(QCoreApplication.translate("ScanEditorDialog", u"Start Time:", None))
        self.labelEndTime.setText(QCoreApplication.translate("ScanEditorDialog", u"End Time:", None))
    # retranslateUi

