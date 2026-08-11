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
        VisBeamPatternTab.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.gridLayout_3 = QGridLayout(VisBeamPatternTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.widget = QWidget(VisBeamPatternTab)
        self.widget.setObjectName(u"widget")
        self.widget.setStyleSheet(u"QWidget{\n"
"    border: 1px solid #005BB5; /* \u0426\u0432\u0435\u0442 \u0433\u0440\u0430\u043d\u0438\u0446\u044b \u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d \u0441 \u0438\u043a\u043e\u043d\u043a\u0430\u043c\u0438 */\n"
"    border-radius: 6px; /* \u0421\u043a\u0440\u0443\u0433\u043b\u0435\u043d\u043d\u044b\u0435 \u0443\u0433\u043b\u044b \u0434\u043b\u044f \u0441\u043e\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u0433\u043e \u0432\u0438\u0434\u0430 */\n"
"    background-color: #FFFFFF; /* \u0421\u0432\u0435\u0442\u043b\u044b\u0439 \u0444\u043e\u043d, \u043d\u0435 \u043e\u0442\u0432\u043b\u0435\u043a\u0430\u044e\u0449\u0438\u0439 \u043e\u0442 \u0433\u0440\u0430\u0444\u0438\u043a\u0430 */\n"
"    padding: 4px; /* \u0412\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0439 \u043e\u0442\u0441\u0442\u0443\u043f \u0434\u043b\u044f \u0432\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u043a\u043e\u043c\u0444\u043e\u0440\u0442\u0430 */\n"
"}")

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

