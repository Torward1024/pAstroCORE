# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_editor_ifWDmUYn.ui'
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
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_IFEditorDialog(object):
    def setupUi(self, IFEditorDialog):
        if not IFEditorDialog.objectName():
            IFEditorDialog.setObjectName(u"IFEditorDialog")
        IFEditorDialog.resize(456, 304)
        self.verticalLayout = QVBoxLayout(IFEditorDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.labelFrequency = QLabel(IFEditorDialog)
        self.labelFrequency.setObjectName(u"labelFrequency")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.labelFrequency)

        self.frequencyEdit = QDoubleSpinBox(IFEditorDialog)
        self.frequencyEdit.setObjectName(u"frequencyEdit")
        self.frequencyEdit.setStyleSheet(u"")
        self.frequencyEdit.setDecimals(3)
        self.frequencyEdit.setMinimum(0.001000000000000)
        self.frequencyEdit.setMaximum(100000.000000000000000)
        self.frequencyEdit.setValue(1000.000000000000000)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.frequencyEdit)

        self.labelWavelength = QLabel(IFEditorDialog)
        self.labelWavelength.setObjectName(u"labelWavelength")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelWavelength)

        self.wavelengthDisplay = QLabel(IFEditorDialog)
        self.wavelengthDisplay.setObjectName(u"wavelengthDisplay")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.wavelengthDisplay)

        self.labelBandwidth = QLabel(IFEditorDialog)
        self.labelBandwidth.setObjectName(u"labelBandwidth")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelBandwidth)

        self.bandwidthEdit = QDoubleSpinBox(IFEditorDialog)
        self.bandwidthEdit.setObjectName(u"bandwidthEdit")
        self.bandwidthEdit.setDecimals(3)
        self.bandwidthEdit.setMinimum(0.001000000000000)
        self.bandwidthEdit.setMaximum(1000.000000000000000)
        self.bandwidthEdit.setValue(16.000000000000000)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.bandwidthEdit)

        self.labelIsActive = QLabel(IFEditorDialog)
        self.labelIsActive.setObjectName(u"labelIsActive")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.labelIsActive)

        self.isActiveCheckBox = QCheckBox(IFEditorDialog)
        self.isActiveCheckBox.setObjectName(u"isActiveCheckBox")
        self.isActiveCheckBox.setChecked(True)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.isActiveCheckBox)


        self.verticalLayout.addLayout(self.formLayout)

        self.labelPolarizations = QLabel(IFEditorDialog)
        self.labelPolarizations.setObjectName(u"labelPolarizations")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(10)
        font.setBold(True)
        self.labelPolarizations.setFont(font)

        self.verticalLayout.addWidget(self.labelPolarizations)

        self.polarizationsList = QListWidget(IFEditorDialog)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        QListWidgetItem(self.polarizationsList)
        self.polarizationsList.setObjectName(u"polarizationsList")
        self.polarizationsList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.verticalLayout.addWidget(self.polarizationsList)

        self.polarizationsButtonLayout = QHBoxLayout()
        self.polarizationsButtonLayout.setObjectName(u"polarizationsButtonLayout")
        self.clearPolarizationsButton = QPushButton(IFEditorDialog)
        self.clearPolarizationsButton.setObjectName(u"clearPolarizationsButton")
        self.clearPolarizationsButton.setStyleSheet(u"QPushButton {\n"
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

        self.polarizationsButtonLayout.addWidget(self.clearPolarizationsButton)

        self.horizontalSpacerPolarizations = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.polarizationsButtonLayout.addItem(self.horizontalSpacerPolarizations)

        self.saveButton = QPushButton(IFEditorDialog)
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

        self.polarizationsButtonLayout.addWidget(self.saveButton)

        self.cancelButton = QPushButton(IFEditorDialog)
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

        self.polarizationsButtonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.polarizationsButtonLayout)


        self.retranslateUi(IFEditorDialog)
        self.saveButton.clicked.connect(IFEditorDialog.accept)
        self.cancelButton.clicked.connect(IFEditorDialog.reject)

        QMetaObject.connectSlotsByName(IFEditorDialog)
    # setupUi

    def retranslateUi(self, IFEditorDialog):
        IFEditorDialog.setWindowTitle(QCoreApplication.translate("IFEditorDialog", u"Edit Intermediate Frequency", None))
        IFEditorDialog.setStyleSheet(QCoreApplication.translate("IFEditorDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelFrequency.setText(QCoreApplication.translate("IFEditorDialog", u"Frequency (MHz):", None))
        self.labelWavelength.setText(QCoreApplication.translate("IFEditorDialog", u"Wavelength (cm):", None))
        self.wavelengthDisplay.setStyleSheet(QCoreApplication.translate("IFEditorDialog", u"color: #6c757d;", None))
        self.wavelengthDisplay.setText(QCoreApplication.translate("IFEditorDialog", u"29.979", None))
        self.labelBandwidth.setText(QCoreApplication.translate("IFEditorDialog", u"Bandwidth (MHz):", None))
        self.labelIsActive.setText(QCoreApplication.translate("IFEditorDialog", u"Active:", None))
        self.labelPolarizations.setText(QCoreApplication.translate("IFEditorDialog", u"Polarizations:", None))

        __sortingEnabled = self.polarizationsList.isSortingEnabled()
        self.polarizationsList.setSortingEnabled(False)
        ___qlistwidgetitem = self.polarizationsList.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("IFEditorDialog", u"RCP", None));
        ___qlistwidgetitem1 = self.polarizationsList.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("IFEditorDialog", u"LCP", None));
        ___qlistwidgetitem2 = self.polarizationsList.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("IFEditorDialog", u"RR", None));
        ___qlistwidgetitem3 = self.polarizationsList.item(3)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("IFEditorDialog", u"LL", None));
        ___qlistwidgetitem4 = self.polarizationsList.item(4)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("IFEditorDialog", u"RL", None));
        ___qlistwidgetitem5 = self.polarizationsList.item(5)
        ___qlistwidgetitem5.setText(QCoreApplication.translate("IFEditorDialog", u"LR", None));
        ___qlistwidgetitem6 = self.polarizationsList.item(6)
        ___qlistwidgetitem6.setText(QCoreApplication.translate("IFEditorDialog", u"H", None));
        ___qlistwidgetitem7 = self.polarizationsList.item(7)
        ___qlistwidgetitem7.setText(QCoreApplication.translate("IFEditorDialog", u"V", None));
        self.polarizationsList.setSortingEnabled(__sortingEnabled)

        self.polarizationsList.setStyleSheet(QCoreApplication.translate("IFEditorDialog", u"border: 1px solid #d3d3d3;", None))
        self.clearPolarizationsButton.setText(QCoreApplication.translate("IFEditorDialog", u"Clear Polarizations", None))
        self.saveButton.setText(QCoreApplication.translate("IFEditorDialog", u"Save", None))
        self.cancelButton.setText(QCoreApplication.translate("IFEditorDialog", u"Cancel", None))
    # retranslateUi