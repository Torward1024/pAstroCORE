# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_vis_mollweide.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_MollweideVisTab(object):
    def setupUi(self, MollweideVisTab):
        if not MollweideVisTab.objectName():
            MollweideVisTab.setObjectName(u"MollweideVisTab")
        MollweideVisTab.resize(881, 550)
        self.gridLayout_3 = QGridLayout(MollweideVisTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.widget = QWidget(MollweideVisTab)
        self.widget.setObjectName(u"widget")

        self.gridLayout_3.addWidget(self.widget, 0, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lblSources = QLabel(MollweideVisTab)
        self.lblSources.setObjectName(u"lblSources")

        self.gridLayout_2.addWidget(self.lblSources, 0, 0, 1, 1)

        self.listSources = QListWidget(MollweideVisTab)
        self.listSources.setObjectName(u"listSources")

        self.gridLayout_2.addWidget(self.listSources, 1, 0, 1, 1)

        self.layoutSourcesButtons = QHBoxLayout()
        self.layoutSourcesButtons.setSpacing(4)
        self.layoutSourcesButtons.setObjectName(u"layoutSourcesButtons")
        self.listSourcesSelectAll = QPushButton(MollweideVisTab)
        self.listSourcesSelectAll.setObjectName(u"listSourcesSelectAll")
        self.listSourcesSelectAll.setAutoDefault(False)

        self.layoutSourcesButtons.addWidget(self.listSourcesSelectAll)

        self.listSourcesClear = QPushButton(MollweideVisTab)
        self.listSourcesClear.setObjectName(u"listSourcesClear")
        self.listSourcesClear.setAutoDefault(False)

        self.layoutSourcesButtons.addWidget(self.listSourcesClear)


        self.gridLayout_2.addLayout(self.layoutSourcesButtons, 2, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.lblScans = QLabel(MollweideVisTab)
        self.lblScans.setObjectName(u"lblScans")

        self.gridLayout.addWidget(self.lblScans, 0, 0, 1, 2)

        self.listScans = QListWidget(MollweideVisTab)
        self.listScans.setObjectName(u"listScans")

        self.gridLayout.addWidget(self.listScans, 1, 0, 1, 2)

        self.layoutScansButtons = QHBoxLayout()
        self.layoutScansButtons.setSpacing(4)
        self.layoutScansButtons.setObjectName(u"layoutScansButtons")
        self.listScansSelectAll = QPushButton(MollweideVisTab)
        self.listScansSelectAll.setObjectName(u"listScansSelectAll")
        self.listScansSelectAll.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansSelectAll)

        self.listScansClear = QPushButton(MollweideVisTab)
        self.listScansClear.setObjectName(u"listScansClear")
        self.listScansClear.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansClear)


        self.gridLayout.addLayout(self.layoutScansButtons, 2, 0, 1, 2)

        self.lblTelescopes = QLabel(MollweideVisTab)
        self.lblTelescopes.setObjectName(u"lblTelescopes")

        self.gridLayout.addWidget(self.lblTelescopes, 3, 0, 1, 2)

        self.listTelescopes = QListWidget(MollweideVisTab)
        self.listTelescopes.setObjectName(u"listTelescopes")

        self.gridLayout.addWidget(self.listTelescopes, 4, 0, 1, 2)

        self.layoutTelescopesButtons = QHBoxLayout()
        self.layoutTelescopesButtons.setSpacing(4)
        self.layoutTelescopesButtons.setObjectName(u"layoutTelescopesButtons")
        self.listTelescopesSelectAll = QPushButton(MollweideVisTab)
        self.listTelescopesSelectAll.setObjectName(u"listTelescopesSelectAll")
        self.listTelescopesSelectAll.setAutoDefault(False)

        self.layoutTelescopesButtons.addWidget(self.listTelescopesSelectAll)

        self.listTelescopesClear = QPushButton(MollweideVisTab)
        self.listTelescopesClear.setObjectName(u"listTelescopesClear")
        self.listTelescopesClear.setAutoDefault(False)

        self.layoutTelescopesButtons.addWidget(self.listTelescopesClear)


        self.gridLayout.addLayout(self.layoutTelescopesButtons, 5, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 3, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(MollweideVisTab)

        QMetaObject.connectSlotsByName(MollweideVisTab)
    # setupUi

    def retranslateUi(self, MollweideVisTab):
        self.lblSources.setText(QCoreApplication.translate("MollweideVisTab", u"Sources:", None))
#if QT_CONFIG(tooltip)
        self.listSourcesSelectAll.setToolTip(QCoreApplication.translate("MollweideVisTab", u"Tick every source", None))
#endif // QT_CONFIG(tooltip)
        self.listSourcesSelectAll.setText(QCoreApplication.translate("MollweideVisTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listSourcesClear.setToolTip(QCoreApplication.translate("MollweideVisTab", u"Untick every source", None))
#endif // QT_CONFIG(tooltip)
        self.listSourcesClear.setText(QCoreApplication.translate("MollweideVisTab", u"Clear", None))
        self.lblScans.setText(QCoreApplication.translate("MollweideVisTab", u"Scans:", None))
#if QT_CONFIG(tooltip)
        self.listScansSelectAll.setToolTip(QCoreApplication.translate("MollweideVisTab", u"Tick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansSelectAll.setText(QCoreApplication.translate("MollweideVisTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listScansClear.setToolTip(QCoreApplication.translate("MollweideVisTab", u"Untick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansClear.setText(QCoreApplication.translate("MollweideVisTab", u"Clear", None))
        self.lblTelescopes.setText(QCoreApplication.translate("MollweideVisTab", u"Telescopes:", None))
#if QT_CONFIG(tooltip)
        self.listTelescopesSelectAll.setToolTip(QCoreApplication.translate("MollweideVisTab", u"Tick every telescope", None))
#endif // QT_CONFIG(tooltip)
        self.listTelescopesSelectAll.setText(QCoreApplication.translate("MollweideVisTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listTelescopesClear.setToolTip(QCoreApplication.translate("MollweideVisTab", u"Untick every telescope", None))
#endif // QT_CONFIG(tooltip)
        self.listTelescopesClear.setText(QCoreApplication.translate("MollweideVisTab", u"Clear", None))
        pass
    # retranslateUi

