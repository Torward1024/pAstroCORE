# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_visualize_observationXIMryb.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_tab_visualize_observation(object):
    def setupUi(self, tab_visualize_observation):
        if not tab_visualize_observation.objectName():
            tab_visualize_observation.setObjectName(u"tab_visualize_observation")
        tab_visualize_observation.resize(479, 355)
        tab_visualize_observation.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.verticalLayout = QVBoxLayout(tab_visualize_observation)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_plot_type = QLabel(tab_visualize_observation)
        self.label_plot_type.setObjectName(u"label_plot_type")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.label_plot_type.setFont(font)

        self.verticalLayout.addWidget(self.label_plot_type)

        self.combo_plot_type = QComboBox(tab_visualize_observation)
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.addItem("")
        self.combo_plot_type.setObjectName(u"combo_plot_type")
        self.combo_plot_type.setFont(font)

        self.verticalLayout.addWidget(self.combo_plot_type)

        self.label_freq = QLabel(tab_visualize_observation)
        self.label_freq.setObjectName(u"label_freq")
        self.label_freq.setFont(font)

        self.verticalLayout.addWidget(self.label_freq)

        self.combo_freq = QComboBox(tab_visualize_observation)
        self.combo_freq.setObjectName(u"combo_freq")
        self.combo_freq.setFont(font)

        self.verticalLayout.addWidget(self.combo_freq)

        self.btn_visualize = QPushButton(tab_visualize_observation)
        self.btn_visualize.setObjectName(u"btn_visualize")
        self.btn_visualize.setFont(font)
        icon = QIcon()
        icon.addFile(u":/icons/plot_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_visualize.setIcon(icon)

        self.verticalLayout.addWidget(self.btn_visualize)

        self.lbl_status = QLabel(tab_visualize_observation)
        self.lbl_status.setObjectName(u"lbl_status")
        self.lbl_status.setFont(font)
        self.lbl_status.setStyleSheet(u"color: #333333;")

        self.verticalLayout.addWidget(self.lbl_status)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(tab_visualize_observation)

        QMetaObject.connectSlotsByName(tab_visualize_observation)
    # setupUi

    def retranslateUi(self, tab_visualize_observation):
        tab_visualize_observation.setWindowTitle(QCoreApplication.translate("tab_visualize_observation", u"Form", None))
        self.label_plot_type.setText(QCoreApplication.translate("tab_visualize_observation", u"Visualization Type:", None))
        self.combo_plot_type.setItemText(0, QCoreApplication.translate("tab_visualize_observation", u"UV Coverage", None))
        self.combo_plot_type.setItemText(1, QCoreApplication.translate("tab_visualize_observation", u"Source Visibility", None))
        self.combo_plot_type.setItemText(2, QCoreApplication.translate("tab_visualize_observation", u"Sun Angles", None))
        self.combo_plot_type.setItemText(3, QCoreApplication.translate("tab_visualize_observation", u"Az/El or HA/Dec", None))
        self.combo_plot_type.setItemText(4, QCoreApplication.translate("tab_visualize_observation", u"Time on Source", None))
        self.combo_plot_type.setItemText(5, QCoreApplication.translate("tab_visualize_observation", u"Beam Pattern", None))
        self.combo_plot_type.setItemText(6, QCoreApplication.translate("tab_visualize_observation", u"Synthesized Beam", None))
        self.combo_plot_type.setItemText(7, QCoreApplication.translate("tab_visualize_observation", u"Baseline Projections", None))
        self.combo_plot_type.setItemText(8, QCoreApplication.translate("tab_visualize_observation", u"Mollweide Tracks", None))

        self.label_freq.setText(QCoreApplication.translate("tab_visualize_observation", u"Frequency (IF):", None))
        self.btn_visualize.setText(QCoreApplication.translate("tab_visualize_observation", u"Visualize", None))
        self.lbl_status.setText(QCoreApplication.translate("tab_visualize_observation", u"Status: Ready", None))
    # retranslateUi