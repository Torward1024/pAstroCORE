# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_vis_sensitivity.ui'
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
class Ui_VisSensitivityTab(object):
    def setupUi(self, VisSensitivityTab):
        if not VisSensitivityTab.objectName():
            VisSensitivityTab.setObjectName(u"VisSensitivityTab")
        VisSensitivityTab.resize(881, 550)
        self.gridLayout_3 = QGridLayout(VisSensitivityTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.widget = QWidget(VisSensitivityTab)
        self.widget.setObjectName(u"widget")

        self.gridLayout_3.addWidget(self.widget, 0, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lblSource = QLabel(VisSensitivityTab)
        self.lblSource.setObjectName(u"lblSource")

        self.gridLayout_2.addWidget(self.lblSource, 0, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.cmbSource = QComboBox(VisSensitivityTab)
        self.cmbSource.setObjectName(u"cmbSource")

        self.gridLayout.addWidget(self.cmbSource, 0, 0, 1, 2)

        self.lblBand = QLabel(VisSensitivityTab)
        self.lblBand.setObjectName(u"lblBand")

        self.gridLayout.addWidget(self.lblBand, 1, 0, 1, 2)

        self.cmbBand = QComboBox(VisSensitivityTab)
        self.cmbBand.setObjectName(u"cmbBand")

        self.gridLayout.addWidget(self.cmbBand, 2, 0, 1, 2)

        self.lblScans = QLabel(VisSensitivityTab)
        self.lblScans.setObjectName(u"lblScans")

        self.gridLayout.addWidget(self.lblScans, 3, 0, 1, 2)

        self.listScans = QListWidget(VisSensitivityTab)
        self.listScans.setObjectName(u"listScans")

        self.gridLayout.addWidget(self.listScans, 4, 0, 1, 2)

        self.layoutScansButtons = QHBoxLayout()
        self.layoutScansButtons.setSpacing(4)
        self.layoutScansButtons.setObjectName(u"layoutScansButtons")
        self.listScansSelectAll = QPushButton(VisSensitivityTab)
        self.listScansSelectAll.setObjectName(u"listScansSelectAll")
        self.listScansSelectAll.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansSelectAll)

        self.listScansClear = QPushButton(VisSensitivityTab)
        self.listScansClear.setObjectName(u"listScansClear")
        self.listScansClear.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansClear)


        self.gridLayout.addLayout(self.layoutScansButtons, 5, 0, 1, 2)

        self.lblBaselines = QLabel(VisSensitivityTab)
        self.lblBaselines.setObjectName(u"lblBaselines")

        self.gridLayout.addWidget(self.lblBaselines, 6, 0, 1, 2)

        self.listBaselines = QListWidget(VisSensitivityTab)
        self.listBaselines.setObjectName(u"listBaselines")

        self.gridLayout.addWidget(self.listBaselines, 7, 0, 1, 2)

        self.layoutBaselinesButtons = QHBoxLayout()
        self.layoutBaselinesButtons.setSpacing(4)
        self.layoutBaselinesButtons.setObjectName(u"layoutBaselinesButtons")
        self.listBaselinesSelectAll = QPushButton(VisSensitivityTab)
        self.listBaselinesSelectAll.setObjectName(u"listBaselinesSelectAll")
        self.listBaselinesSelectAll.setAutoDefault(False)

        self.layoutBaselinesButtons.addWidget(self.listBaselinesSelectAll)

        self.listBaselinesClear = QPushButton(VisSensitivityTab)
        self.listBaselinesClear.setObjectName(u"listBaselinesClear")
        self.listBaselinesClear.setAutoDefault(False)

        self.layoutBaselinesButtons.addWidget(self.listBaselinesClear)


        self.gridLayout.addLayout(self.layoutBaselinesButtons, 8, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(VisSensitivityTab)

        QMetaObject.connectSlotsByName(VisSensitivityTab)
    # setupUi

    def retranslateUi(self, VisSensitivityTab):
        self.lblSource.setText(QCoreApplication.translate("VisSensitivityTab", u"Source:", None))
        self.lblBand.setText(QCoreApplication.translate("VisSensitivityTab", u"Band:", None))
#if QT_CONFIG(tooltip)
        self.cmbBand.setToolTip(QCoreApplication.translate("VisSensitivityTab", u"One band, or all of them together", None))
#endif // QT_CONFIG(tooltip)
        self.lblScans.setText(QCoreApplication.translate("VisSensitivityTab", u"Scans:", None))
#if QT_CONFIG(tooltip)
        self.listScansSelectAll.setToolTip(QCoreApplication.translate("VisSensitivityTab", u"Tick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansSelectAll.setText(QCoreApplication.translate("VisSensitivityTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listScansClear.setToolTip(QCoreApplication.translate("VisSensitivityTab", u"Untick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansClear.setText(QCoreApplication.translate("VisSensitivityTab", u"Clear", None))
        self.lblBaselines.setText(QCoreApplication.translate("VisSensitivityTab", u"Baselines:", None))
#if QT_CONFIG(tooltip)
        self.listBaselinesSelectAll.setToolTip(QCoreApplication.translate("VisSensitivityTab", u"Tick every baseline", None))
#endif // QT_CONFIG(tooltip)
        self.listBaselinesSelectAll.setText(QCoreApplication.translate("VisSensitivityTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listBaselinesClear.setToolTip(QCoreApplication.translate("VisSensitivityTab", u"Untick every baseline", None))
#endif // QT_CONFIG(tooltip)
        self.listBaselinesClear.setText(QCoreApplication.translate("VisSensitivityTab", u"Clear", None))
        pass
    # retranslateUi

