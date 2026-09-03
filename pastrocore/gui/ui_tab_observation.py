# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_observation.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QLabel, QLineEdit, QSizePolicy, QTabWidget,
    QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_ObservationInfoTab(object):
    def setupUi(self, ObservationInfoTab):
        if not ObservationInfoTab.objectName():
            ObservationInfoTab.setObjectName(u"ObservationInfoTab")
        ObservationInfoTab.resize(587, 471)
        self.gridLayout = QGridLayout(ObservationInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.obs_name_edit = QLineEdit(ObservationInfoTab)
        self.obs_name_edit.setObjectName(u"obs_name_edit")
        self.obs_name_edit.setEnabled(True)
        self.obs_name_edit.setReadOnly(True)

        self.gridLayout.addWidget(self.obs_name_edit, 0, 1, 1, 1)

        self.tabWidget = QTabWidget(ObservationInfoTab)
        self.tabWidget.setObjectName(u"tabWidget")

        self.gridLayout.addWidget(self.tabWidget, 4, 0, 1, 5)

        self.lbl_obs_info = QLabel(ObservationInfoTab)
        self.lbl_obs_info.setObjectName(u"lbl_obs_info")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.lbl_obs_info.setFont(font)

        self.gridLayout.addWidget(self.lbl_obs_info, 2, 0, 1, 5)

        self.label_2 = QLabel(ObservationInfoTab)
        self.label_2.setObjectName(u"label_2")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setBold(False)
        self.label_2.setFont(font1)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.label = QLabel(ObservationInfoTab)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 2, 1, 1)

        self.combo_obs_type = QComboBox(ObservationInfoTab)
        self.combo_obs_type.setObjectName(u"combo_obs_type")
        self.combo_obs_type.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(150)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.combo_obs_type.sizePolicy().hasHeightForWidth())
        self.combo_obs_type.setSizePolicy(sizePolicy)
        self.combo_obs_type.setMinimumSize(QSize(150, 0))
        self.combo_obs_type.setMaximumSize(QSize(150, 16777215))

        self.gridLayout.addWidget(self.combo_obs_type, 0, 4, 1, 1)

        self.line = QFrame(ObservationInfoTab)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 5)

        self.line_2 = QFrame(ObservationInfoTab)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 3, 0, 1, 5)


        self.retranslateUi(ObservationInfoTab)

        self.tabWidget.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(ObservationInfoTab)
    # setupUi

    def retranslateUi(self, ObservationInfoTab):
        self.lbl_obs_info.setText(QCoreApplication.translate("ObservationInfoTab", u"Start Time/Date: [get_start_time_date]; Duration: [DURATION] sec.", None))
        self.label_2.setText(QCoreApplication.translate("ObservationInfoTab", u"Observation code:", None))
        self.label.setText(QCoreApplication.translate("ObservationInfoTab", u"Type:", None))
        self.combo_obs_type.setCurrentText("")
        pass
    # retranslateUi

