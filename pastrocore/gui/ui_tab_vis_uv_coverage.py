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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QWidget)
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
        self.lblSource = QLabel(UVCoverageVisTab)
        self.lblSource.setObjectName(u"lblSource")

        self.gridLayout_2.addWidget(self.lblSource, 0, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.comboBox = QComboBox(UVCoverageVisTab)
        self.comboBox.setObjectName(u"comboBox")

        self.gridLayout.addWidget(self.comboBox, 0, 0, 1, 2)

        self.lblFrequencies = QLabel(UVCoverageVisTab)
        self.lblFrequencies.setObjectName(u"lblFrequencies")

        self.gridLayout.addWidget(self.lblFrequencies, 1, 0, 1, 2)

        self.listFrequencies = QListWidget(UVCoverageVisTab)
        self.listFrequencies.setObjectName(u"listFrequencies")

        self.gridLayout.addWidget(self.listFrequencies, 2, 0, 1, 2)

        self.layoutFrequenciesButtons = QHBoxLayout()
        self.layoutFrequenciesButtons.setSpacing(4)
        self.layoutFrequenciesButtons.setObjectName(u"layoutFrequenciesButtons")
        self.listFrequenciesSelectAll = QPushButton(UVCoverageVisTab)
        self.listFrequenciesSelectAll.setObjectName(u"listFrequenciesSelectAll")
        self.listFrequenciesSelectAll.setAutoDefault(False)

        self.layoutFrequenciesButtons.addWidget(self.listFrequenciesSelectAll)

        self.listFrequenciesClear = QPushButton(UVCoverageVisTab)
        self.listFrequenciesClear.setObjectName(u"listFrequenciesClear")
        self.listFrequenciesClear.setAutoDefault(False)

        self.layoutFrequenciesButtons.addWidget(self.listFrequenciesClear)


        self.gridLayout.addLayout(self.layoutFrequenciesButtons, 3, 0, 1, 2)

        self.lblScans = QLabel(UVCoverageVisTab)
        self.lblScans.setObjectName(u"lblScans")

        self.gridLayout.addWidget(self.lblScans, 4, 0, 1, 2)

        self.listScans = QListWidget(UVCoverageVisTab)
        self.listScans.setObjectName(u"listScans")

        self.gridLayout.addWidget(self.listScans, 5, 0, 1, 2)

        self.layoutScansButtons = QHBoxLayout()
        self.layoutScansButtons.setSpacing(4)
        self.layoutScansButtons.setObjectName(u"layoutScansButtons")
        self.listScansSelectAll = QPushButton(UVCoverageVisTab)
        self.listScansSelectAll.setObjectName(u"listScansSelectAll")
        self.listScansSelectAll.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansSelectAll)

        self.listScansClear = QPushButton(UVCoverageVisTab)
        self.listScansClear.setObjectName(u"listScansClear")
        self.listScansClear.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansClear)


        self.gridLayout.addLayout(self.layoutScansButtons, 6, 0, 1, 2)

        self.lblBaselines = QLabel(UVCoverageVisTab)
        self.lblBaselines.setObjectName(u"lblBaselines")

        self.gridLayout.addWidget(self.lblBaselines, 7, 0, 1, 2)

        self.listBaselines = QListWidget(UVCoverageVisTab)
        self.listBaselines.setObjectName(u"listBaselines")

        self.gridLayout.addWidget(self.listBaselines, 8, 0, 1, 2)

        self.layoutBaselinesButtons = QHBoxLayout()
        self.layoutBaselinesButtons.setSpacing(4)
        self.layoutBaselinesButtons.setObjectName(u"layoutBaselinesButtons")
        self.listBaselinesSelectAll = QPushButton(UVCoverageVisTab)
        self.listBaselinesSelectAll.setObjectName(u"listBaselinesSelectAll")
        self.listBaselinesSelectAll.setAutoDefault(False)

        self.layoutBaselinesButtons.addWidget(self.listBaselinesSelectAll)

        self.listBaselinesClear = QPushButton(UVCoverageVisTab)
        self.listBaselinesClear.setObjectName(u"listBaselinesClear")
        self.listBaselinesClear.setAutoDefault(False)

        self.layoutBaselinesButtons.addWidget(self.listBaselinesClear)


        self.gridLayout.addLayout(self.layoutBaselinesButtons, 9, 0, 1, 2)

        self.lblUnits = QLabel(UVCoverageVisTab)
        self.lblUnits.setObjectName(u"lblUnits")

        self.gridLayout.addWidget(self.lblUnits, 10, 0, 1, 2)

        self.comboBox_2 = QComboBox(UVCoverageVisTab)
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.gridLayout.addWidget(self.comboBox_2, 11, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(UVCoverageVisTab)

        QMetaObject.connectSlotsByName(UVCoverageVisTab)
    # setupUi

    def retranslateUi(self, UVCoverageVisTab):
        self.lblSource.setText(QCoreApplication.translate("UVCoverageVisTab", u"Source:", None))
        self.lblFrequencies.setText(QCoreApplication.translate("UVCoverageVisTab", u"Frequencies:", None))
#if QT_CONFIG(tooltip)
        self.listFrequenciesSelectAll.setToolTip(QCoreApplication.translate("UVCoverageVisTab", u"Tick every frequency", None))
#endif // QT_CONFIG(tooltip)
        self.listFrequenciesSelectAll.setText(QCoreApplication.translate("UVCoverageVisTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listFrequenciesClear.setToolTip(QCoreApplication.translate("UVCoverageVisTab", u"Untick every frequency", None))
#endif // QT_CONFIG(tooltip)
        self.listFrequenciesClear.setText(QCoreApplication.translate("UVCoverageVisTab", u"Clear", None))
        self.lblScans.setText(QCoreApplication.translate("UVCoverageVisTab", u"Scans:", None))
#if QT_CONFIG(tooltip)
        self.listScansSelectAll.setToolTip(QCoreApplication.translate("UVCoverageVisTab", u"Tick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansSelectAll.setText(QCoreApplication.translate("UVCoverageVisTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listScansClear.setToolTip(QCoreApplication.translate("UVCoverageVisTab", u"Untick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansClear.setText(QCoreApplication.translate("UVCoverageVisTab", u"Clear", None))
        self.lblBaselines.setText(QCoreApplication.translate("UVCoverageVisTab", u"Baselines:", None))
#if QT_CONFIG(tooltip)
        self.listBaselinesSelectAll.setToolTip(QCoreApplication.translate("UVCoverageVisTab", u"Tick every baseline", None))
#endif // QT_CONFIG(tooltip)
        self.listBaselinesSelectAll.setText(QCoreApplication.translate("UVCoverageVisTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listBaselinesClear.setToolTip(QCoreApplication.translate("UVCoverageVisTab", u"Untick every baseline", None))
#endif // QT_CONFIG(tooltip)
        self.listBaselinesClear.setText(QCoreApplication.translate("UVCoverageVisTab", u"Clear", None))
        self.lblUnits.setText(QCoreApplication.translate("UVCoverageVisTab", u"Units:", None))
        pass
    # retranslateUi

