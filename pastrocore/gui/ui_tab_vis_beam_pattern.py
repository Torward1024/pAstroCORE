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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QWidget)
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
        self.lblTelescopes = QLabel(VisBeamPatternTab)
        self.lblTelescopes.setObjectName(u"lblTelescopes")

        self.gridLayout.addWidget(self.lblTelescopes, 0, 0, 1, 2)

        self.listTelescopes = QListWidget(VisBeamPatternTab)
        self.listTelescopes.setObjectName(u"listTelescopes")

        self.gridLayout.addWidget(self.listTelescopes, 1, 0, 1, 2)

        self.layoutTelescopesButtons = QHBoxLayout()
        self.layoutTelescopesButtons.setSpacing(4)
        self.layoutTelescopesButtons.setObjectName(u"layoutTelescopesButtons")
        self.listTelescopesSelectAll = QPushButton(VisBeamPatternTab)
        self.listTelescopesSelectAll.setObjectName(u"listTelescopesSelectAll")
        self.listTelescopesSelectAll.setAutoDefault(False)

        self.layoutTelescopesButtons.addWidget(self.listTelescopesSelectAll)

        self.listTelescopesClear = QPushButton(VisBeamPatternTab)
        self.listTelescopesClear.setObjectName(u"listTelescopesClear")
        self.listTelescopesClear.setAutoDefault(False)

        self.layoutTelescopesButtons.addWidget(self.listTelescopesClear)


        self.gridLayout.addLayout(self.layoutTelescopesButtons, 2, 0, 1, 2)

        self.lblFrequencies = QLabel(VisBeamPatternTab)
        self.lblFrequencies.setObjectName(u"lblFrequencies")

        self.gridLayout.addWidget(self.lblFrequencies, 3, 0, 1, 2)

        self.listFrequencies = QListWidget(VisBeamPatternTab)
        self.listFrequencies.setObjectName(u"listFrequencies")

        self.gridLayout.addWidget(self.listFrequencies, 4, 0, 1, 2)

        self.layoutFrequenciesButtons = QHBoxLayout()
        self.layoutFrequenciesButtons.setSpacing(4)
        self.layoutFrequenciesButtons.setObjectName(u"layoutFrequenciesButtons")
        self.listFrequenciesSelectAll = QPushButton(VisBeamPatternTab)
        self.listFrequenciesSelectAll.setObjectName(u"listFrequenciesSelectAll")
        self.listFrequenciesSelectAll.setAutoDefault(False)

        self.layoutFrequenciesButtons.addWidget(self.listFrequenciesSelectAll)

        self.listFrequenciesClear = QPushButton(VisBeamPatternTab)
        self.listFrequenciesClear.setObjectName(u"listFrequenciesClear")
        self.listFrequenciesClear.setAutoDefault(False)

        self.layoutFrequenciesButtons.addWidget(self.listFrequenciesClear)


        self.gridLayout.addLayout(self.layoutFrequenciesButtons, 5, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.gridLayout_3.setColumnStretch(0, 5)
        self.gridLayout_3.setColumnStretch(1, 1)

        self.retranslateUi(VisBeamPatternTab)

        QMetaObject.connectSlotsByName(VisBeamPatternTab)
    # setupUi

    def retranslateUi(self, VisBeamPatternTab):
        self.lblTelescopes.setText(QCoreApplication.translate("VisBeamPatternTab", u"Telescopes:", None))
#if QT_CONFIG(tooltip)
        self.listTelescopesSelectAll.setToolTip(QCoreApplication.translate("VisBeamPatternTab", u"Tick every telescope", None))
#endif // QT_CONFIG(tooltip)
        self.listTelescopesSelectAll.setText(QCoreApplication.translate("VisBeamPatternTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listTelescopesClear.setToolTip(QCoreApplication.translate("VisBeamPatternTab", u"Untick every telescope", None))
#endif // QT_CONFIG(tooltip)
        self.listTelescopesClear.setText(QCoreApplication.translate("VisBeamPatternTab", u"Clear", None))
        self.lblFrequencies.setText(QCoreApplication.translate("VisBeamPatternTab", u"Frequencies:", None))
#if QT_CONFIG(tooltip)
        self.listFrequenciesSelectAll.setToolTip(QCoreApplication.translate("VisBeamPatternTab", u"Tick every frequency", None))
#endif // QT_CONFIG(tooltip)
        self.listFrequenciesSelectAll.setText(QCoreApplication.translate("VisBeamPatternTab", u"Select All", None))
#if QT_CONFIG(tooltip)
        self.listFrequenciesClear.setToolTip(QCoreApplication.translate("VisBeamPatternTab", u"Untick every frequency", None))
#endif // QT_CONFIG(tooltip)
        self.listFrequenciesClear.setText(QCoreApplication.translate("VisBeamPatternTab", u"Clear", None))
        pass
    # retranslateUi

