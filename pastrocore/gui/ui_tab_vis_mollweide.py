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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QListWidget,
    QListWidgetItem, QSizePolicy, QWidget)
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

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.lblScans = QLabel(MollweideVisTab)
        self.lblScans.setObjectName(u"lblScans")

        self.gridLayout.addWidget(self.lblScans, 0, 0, 1, 2)

        self.listTelescopes = QListWidget(MollweideVisTab)
        self.listTelescopes.setObjectName(u"listTelescopes")

        self.gridLayout.addWidget(self.listTelescopes, 3, 0, 1, 2)

        self.lblTelescopes = QLabel(MollweideVisTab)
        self.lblTelescopes.setObjectName(u"lblTelescopes")

        self.gridLayout.addWidget(self.lblTelescopes, 2, 0, 1, 2)

        self.listScans = QListWidget(MollweideVisTab)
        self.listScans.setObjectName(u"listScans")

        self.gridLayout.addWidget(self.listScans, 1, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 2, 0, 1, 1)

        self.listWidget = QListWidget(MollweideVisTab)
        self.listWidget.setObjectName(u"listWidget")

        self.gridLayout_2.addWidget(self.listWidget, 1, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(MollweideVisTab)

        QMetaObject.connectSlotsByName(MollweideVisTab)
    # setupUi

    def retranslateUi(self, MollweideVisTab):
        self.lblSources.setText(QCoreApplication.translate("MollweideVisTab", u"Sources:", None))
        self.lblScans.setText(QCoreApplication.translate("MollweideVisTab", u"Scans:", None))
        self.lblTelescopes.setText(QCoreApplication.translate("MollweideVisTab", u"Telescopes:", None))
        pass
    # retranslateUi

