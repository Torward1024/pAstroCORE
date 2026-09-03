# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_vis_uv_coverage.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_UVCoverageVisTab(object):
    def setupUi(self, UVCoverageVisTab):
        if not UVCoverageVisTab.objectName():
            UVCoverageVisTab.setObjectName(u"UVCoverageVisTab")
        UVCoverageVisTab.resize(881, 550)
        self.gridLayout_3 = QGridLayout(UVCoverageVisTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.widget = QWidget(UVCoverageVisTab)
        self.widget.setObjectName(u"widget")

        self.gridLayout_3.addWidget(self.widget, 0, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.listBaselines = QListWidget(UVCoverageVisTab)
        self.listBaselines.setObjectName(u"listBaselines")

        self.gridLayout.addWidget(self.listBaselines, 6, 0, 1, 2)

        self.listScans = QListWidget(UVCoverageVisTab)
        self.listScans.setObjectName(u"listScans")

        self.gridLayout.addWidget(self.listScans, 4, 0, 1, 2)

        self.comboBox = QComboBox(UVCoverageVisTab)
        self.comboBox.setObjectName(u"comboBox")

        self.gridLayout.addWidget(self.comboBox, 0, 0, 1, 2)

        self.lblScans = QLabel(UVCoverageVisTab)
        self.lblScans.setObjectName(u"lblScans")

        self.gridLayout.addWidget(self.lblScans, 3, 0, 1, 2)

        self.listFrequencies = QListWidget(UVCoverageVisTab)
        self.listFrequencies.setObjectName(u"listFrequencies")

        self.gridLayout.addWidget(self.listFrequencies, 2, 0, 1, 1)

        self.lblUnits = QLabel(UVCoverageVisTab)
        self.lblUnits.setObjectName(u"lblUnits")

        self.gridLayout.addWidget(self.lblUnits, 7, 0, 1, 1)

        self.lblBaselines = QLabel(UVCoverageVisTab)
        self.lblBaselines.setObjectName(u"lblBaselines")

        self.gridLayout.addWidget(self.lblBaselines, 5, 0, 1, 2)

        self.lblFrequencies = QLabel(UVCoverageVisTab)
        self.lblFrequencies.setObjectName(u"lblFrequencies")

        self.gridLayout.addWidget(self.lblFrequencies, 1, 0, 1, 2)

        self.comboBox_2 = QComboBox(UVCoverageVisTab)
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.gridLayout.addWidget(self.comboBox_2, 8, 0, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)

        self.lblSource = QLabel(UVCoverageVisTab)
        self.lblSource.setObjectName(u"lblSource")

        self.gridLayout_2.addWidget(self.lblSource, 0, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(UVCoverageVisTab)

        QMetaObject.connectSlotsByName(UVCoverageVisTab)
    # setupUi

    def retranslateUi(self, UVCoverageVisTab):
        self.lblScans.setText(QCoreApplication.translate("UVCoverageVisTab", u"Scans:", None))
        self.lblUnits.setText(QCoreApplication.translate("UVCoverageVisTab", u"Units:", None))
        self.lblBaselines.setText(QCoreApplication.translate("UVCoverageVisTab", u"Baselines:", None))
        self.lblFrequencies.setText(QCoreApplication.translate("UVCoverageVisTab", u"Frequencies:", None))
        self.lblSource.setText(QCoreApplication.translate("UVCoverageVisTab", u"Source:", None))
        pass
    # retranslateUi

