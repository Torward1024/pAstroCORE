# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_vis_default.ui'
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
class Ui_VisDefaultTab(object):
    def setupUi(self, VisDefaultTab):
        if not VisDefaultTab.objectName():
            VisDefaultTab.setObjectName(u"VisDefaultTab")
        VisDefaultTab.resize(881, 550)
        self.gridLayout_3 = QGridLayout(VisDefaultTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.widget = QWidget(VisDefaultTab)
        self.widget.setObjectName(u"widget")

        self.gridLayout_3.addWidget(self.widget, 0, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lblSource = QLabel(VisDefaultTab)
        self.lblSource.setObjectName(u"lblSource")

        self.gridLayout_2.addWidget(self.lblSource, 0, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.cmbSource = QComboBox(VisDefaultTab)
        self.cmbSource.setObjectName(u"cmbSource")

        self.gridLayout.addWidget(self.cmbSource, 0, 0, 1, 2)

        self.lblScans = QLabel(VisDefaultTab)
        self.lblScans.setObjectName(u"lblScans")

        self.gridLayout.addWidget(self.lblScans, 1, 0, 1, 2)

        self.listScans = QListWidget(VisDefaultTab)
        self.listScans.setObjectName(u"listScans")

        self.gridLayout.addWidget(self.listScans, 2, 0, 1, 2)

        self.layoutScansButtons = QHBoxLayout()
        self.layoutScansButtons.setSpacing(4)
        self.layoutScansButtons.setObjectName(u"layoutScansButtons")
        self.listScansSelectAll = QPushButton(VisDefaultTab)
        self.listScansSelectAll.setObjectName(u"listScansSelectAll")
        self.listScansSelectAll.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansSelectAll)

        self.listScansClear = QPushButton(VisDefaultTab)
        self.listScansClear.setObjectName(u"listScansClear")
        self.listScansClear.setAutoDefault(False)

        self.layoutScansButtons.addWidget(self.listScansClear)


        self.gridLayout.addLayout(self.layoutScansButtons, 3, 0, 1, 2)

        self.lblTelescopes = QLabel(VisDefaultTab)
        self.lblTelescopes.setObjectName(u"lblTelescopes")

        self.gridLayout.addWidget(self.lblTelescopes, 4, 0, 1, 2)

        self.listTelescopes = QListWidget(VisDefaultTab)
        self.listTelescopes.setObjectName(u"listTelescopes")

        self.gridLayout.addWidget(self.listTelescopes, 5, 0, 1, 2)

        self.layoutTelescopesButtons = QHBoxLayout()
        self.layoutTelescopesButtons.setSpacing(4)
        self.layoutTelescopesButtons.setObjectName(u"layoutTelescopesButtons")
        self.listTelescopesSelectAll = QPushButton(VisDefaultTab)
        self.listTelescopesSelectAll.setObjectName(u"listTelescopesSelectAll")
        self.listTelescopesSelectAll.setAutoDefault(False)

        self.layoutTelescopesButtons.addWidget(self.listTelescopesSelectAll)

        self.listTelescopesClear = QPushButton(VisDefaultTab)
        self.listTelescopesClear.setObjectName(u"listTelescopesClear")
        self.listTelescopesClear.setAutoDefault(False)

        self.layoutTelescopesButtons.addWidget(self.listTelescopesClear)


        self.gridLayout.addLayout(self.layoutTelescopesButtons, 6, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(VisDefaultTab)

        QMetaObject.connectSlotsByName(VisDefaultTab)
    # setupUi

    def retranslateUi(self, VisDefaultTab):
        self.lblSource.setText(QCoreApplication.translate("VisDefaultTab", u"Source:", None))
        self.lblScans.setText(QCoreApplication.translate("VisDefaultTab", u"Scans:", None))
#if QT_CONFIG(tooltip)
        self.listScansSelectAll.setToolTip(QCoreApplication.translate("VisDefaultTab", u"Tick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansSelectAll.setText(QCoreApplication.translate("VisDefaultTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listScansClear.setToolTip(QCoreApplication.translate("VisDefaultTab", u"Untick every scan", None))
#endif // QT_CONFIG(tooltip)
        self.listScansClear.setText(QCoreApplication.translate("VisDefaultTab", u"Clear", None))
        self.lblTelescopes.setText(QCoreApplication.translate("VisDefaultTab", u"Telescopes:", None))
#if QT_CONFIG(tooltip)
        self.listTelescopesSelectAll.setToolTip(QCoreApplication.translate("VisDefaultTab", u"Tick every telescope", None))
#endif // QT_CONFIG(tooltip)
        self.listTelescopesSelectAll.setText(QCoreApplication.translate("VisDefaultTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listTelescopesClear.setToolTip(QCoreApplication.translate("VisDefaultTab", u"Untick every telescope", None))
#endif // QT_CONFIG(tooltip)
        self.listTelescopesClear.setText(QCoreApplication.translate("VisDefaultTab", u"Clear", None))
        pass
    # retranslateUi

