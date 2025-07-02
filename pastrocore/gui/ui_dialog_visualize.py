# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_visualizejIogtJ.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_VisualizationDialog(object):
    def setupUi(self, VisualizationDialog):
        if not VisualizationDialog.objectName():
            VisualizationDialog.setObjectName(u"VisualizationDialog")
        VisualizationDialog.resize(752, 567)
        self.verticalLayout = QVBoxLayout(VisualizationDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(VisualizationDialog)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.comboBoxObservation = QComboBox(VisualizationDialog)
        self.comboBoxObservation.setObjectName(u"comboBoxObservation")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.comboBoxObservation)

        self.labelVisualizationType = QLabel(VisualizationDialog)
        self.labelVisualizationType.setObjectName(u"labelVisualizationType")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.labelVisualizationType.setFont(font)

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelVisualizationType)

        self.comboBoxVisualizationType = QComboBox(VisualizationDialog)
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.setObjectName(u"comboBoxVisualizationType")
        self.comboBoxVisualizationType.setFont(font)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.comboBoxVisualizationType)

        self.labelFrequency = QLabel(VisualizationDialog)
        self.labelFrequency.setObjectName(u"labelFrequency")
        self.labelFrequency.setFont(font)

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.labelFrequency)

        self.comboBoxFrequency = QComboBox(VisualizationDialog)
        self.comboBoxFrequency.setObjectName(u"comboBoxFrequency")
        self.comboBoxFrequency.setFont(font)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.comboBoxFrequency)


        self.verticalLayout.addLayout(self.formLayout)

        self.pushButtonVisualize = QPushButton(VisualizationDialog)
        self.pushButtonVisualize.setObjectName(u"pushButtonVisualize")
        self.pushButtonVisualize.setFont(font)
        icon = QIcon()
        icon.addFile(u":/icons/plot_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pushButtonVisualize.setIcon(icon)

        self.verticalLayout.addWidget(self.pushButtonVisualize)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.closeButton = QPushButton(VisualizationDialog)
        self.closeButton.setObjectName(u"closeButton")

        self.verticalLayout.addWidget(self.closeButton)


        self.retranslateUi(VisualizationDialog)

        QMetaObject.connectSlotsByName(VisualizationDialog)
    # setupUi

    def retranslateUi(self, VisualizationDialog):
        VisualizationDialog.setWindowTitle(QCoreApplication.translate("VisualizationDialog", u"Visualize Observation", None))
        VisualizationDialog.setStyleSheet(QCoreApplication.translate("VisualizationDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.label.setText(QCoreApplication.translate("VisualizationDialog", u"Observation:", None))
        self.labelVisualizationType.setText(QCoreApplication.translate("VisualizationDialog", u"Visualization Type:", None))
        self.comboBoxVisualizationType.setItemText(0, QCoreApplication.translate("VisualizationDialog", u"UV Coverage", None))
        self.comboBoxVisualizationType.setItemText(1, QCoreApplication.translate("VisualizationDialog", u"Source Visibility", None))
        self.comboBoxVisualizationType.setItemText(2, QCoreApplication.translate("VisualizationDialog", u"Sun Angles", None))
        self.comboBoxVisualizationType.setItemText(3, QCoreApplication.translate("VisualizationDialog", u"Az/El or HA/Dec", None))
        self.comboBoxVisualizationType.setItemText(4, QCoreApplication.translate("VisualizationDialog", u"Time on Source", None))
        self.comboBoxVisualizationType.setItemText(5, QCoreApplication.translate("VisualizationDialog", u"Beam Pattern", None))
        self.comboBoxVisualizationType.setItemText(6, QCoreApplication.translate("VisualizationDialog", u"Synthesized Beam", None))
        self.comboBoxVisualizationType.setItemText(7, QCoreApplication.translate("VisualizationDialog", u"Baseline Projections", None))
        self.comboBoxVisualizationType.setItemText(8, QCoreApplication.translate("VisualizationDialog", u"Mollweide Tracks", None))

        self.labelFrequency.setText(QCoreApplication.translate("VisualizationDialog", u"Frequency (IF):", None))
        self.pushButtonVisualize.setText(QCoreApplication.translate("VisualizationDialog", u"View", None))
        self.closeButton.setText(QCoreApplication.translate("VisualizationDialog", u"Close", None))
    # retranslateUi