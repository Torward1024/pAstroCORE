# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_vis_beam_pattern.ui'
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
class Ui_VisBeamPatternTab(object):
    def setupUi(self, VisBeamPatternTab):
        if not VisBeamPatternTab.objectName():
            VisBeamPatternTab.setObjectName(u"VisBeamPatternTab")
        VisBeamPatternTab.resize(881, 550)
        self.gridLayout_3 = QGridLayout(VisBeamPatternTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.widget = QWidget(VisBeamPatternTab)
        self.widget.setObjectName(u"widget")

        self.gridLayout_3.addWidget(self.widget, 0, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.listFrequencies = QListWidget(VisBeamPatternTab)
        self.listFrequencies.setObjectName(u"listFrequencies")

        self.gridLayout.addWidget(self.listFrequencies, 7, 0, 1, 1)

        self.lblTelescopes = QLabel(VisBeamPatternTab)
        self.lblTelescopes.setObjectName(u"lblTelescopes")

        self.gridLayout.addWidget(self.lblTelescopes, 0, 0, 1, 1)

        self.lblFrequencies = QLabel(VisBeamPatternTab)
        self.lblFrequencies.setObjectName(u"lblFrequencies")

        self.gridLayout.addWidget(self.lblFrequencies, 6, 0, 1, 1)

        self.listTelescopes = QListWidget(VisBeamPatternTab)
        self.listTelescopes.setObjectName(u"listTelescopes")

        self.gridLayout.addWidget(self.listTelescopes, 1, 0, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(VisBeamPatternTab)

        QMetaObject.connectSlotsByName(VisBeamPatternTab)
    # setupUi

    def retranslateUi(self, VisBeamPatternTab):
        self.lblTelescopes.setText(QCoreApplication.translate("VisBeamPatternTab", u"Telescopes:", None))
        self.lblFrequencies.setText(QCoreApplication.translate("VisBeamPatternTab", u"Frequencies:", None))
        pass
    # retranslateUi

