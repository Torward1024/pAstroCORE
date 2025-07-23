# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_calc_progressBnNEsU.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout,
    QLabel, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_CalcDialog(object):
    def setupUi(self, CalcDialog):
        if not CalcDialog.objectName():
            CalcDialog.setObjectName(u"CalcDialog")
        CalcDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        CalcDialog.resize(450, 130)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(CalcDialog.sizePolicy().hasHeightForWidth())
        CalcDialog.setSizePolicy(sizePolicy)
        CalcDialog.setMinimumSize(QSize(450, 130))
        CalcDialog.setMaximumSize(QSize(450, 130))
        icon = QIcon()
        icon.addFile(u":/icons/calculate.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CalcDialog.setWindowIcon(icon)
        CalcDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        CalcDialog.setModal(True)
        self.gridLayout = QGridLayout(CalcDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.pushButton = QPushButton(CalcDialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff; /* \u0421\u0432\u0435\u0442\u043b\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5; /* \u0422\u0435\u043c\u043d\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0436\u0430\u0442\u0438\u0438 */\n"
"    padding-top: 7px; /* \u041b\u0435\u0433\u043a\u043e\u0435 \u0441\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u0432\u043d\u0438\u0437 \u0434\u043b\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0430 \"\u043f\u0440\u043e\u0434\u0430\u0432\u043b\u0438\u0432\u0430\u043d\u0438\u044f\" */\n"
"    padding-bottom: 5px;\n"
"}")

        self.gridLayout_2.addWidget(self.pushButton, 3, 1, 1, 1)

        self.progressBar = QProgressBar(CalcDialog)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setStyleSheet(u"QProgressBar {\n"
"    border: 1px solid #d3d3d3;\n"
"    border-radius: 4px;\n"
"    background-color: #ffffff;\n"
"    text-align: center;\n"
"    font-family: Arial;\n"
"    font-size: 12px;\n"
"    color: #000000;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QProgressBar::chunk {\n"
"    background-color: #0078d7;\n"
"    border-radius: 2px;\n"
"    margin: 1px; /* \u041e\u0442\u0441\u0442\u0443\u043f \u0434\u043b\u044f \u0433\u0430\u0440\u043c\u043e\u043d\u0438\u0447\u043d\u043e\u0433\u043e \u0432\u0438\u0434\u0430 \u0432\u043d\u0443\u0442\u0440\u0438 \u0433\u0440\u0430\u043d\u0438\u0446\u044b */\n"
"}\n"
"\n"
"QProgressBar:hover {\n"
"    background-color: #e0e0e0;\n"
"}\n"
"\n"
"QProgressBar:disabled {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f0f0f0;\n"
"    color: #808080;\n"
"}\n"
"\n"
"QProgressBar::chunk:disabled {\n"
"    background-color: #a0a0a0;\n"
"}")
        self.progressBar.setValue(24)

        self.gridLayout_2.addWidget(self.progressBar, 2, 0, 1, 2)

        self.lblCalcStatus = QLabel(CalcDialog)
        self.lblCalcStatus.setObjectName(u"lblCalcStatus")
        self.lblCalcStatus.setFrameShape(QFrame.Shape.Box)
        self.lblCalcStatus.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.lblCalcStatus, 0, 0, 1, 2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 1, 0, 1, 2)


        self.gridLayout.addLayout(self.gridLayout_2, 0, 0, 1, 1)


        self.retranslateUi(CalcDialog)

        QMetaObject.connectSlotsByName(CalcDialog)
    # setupUi

    def retranslateUi(self, CalcDialog):
        CalcDialog.setWindowTitle(QCoreApplication.translate("CalcDialog", u"Dialog", None))
        self.pushButton.setText(QCoreApplication.translate("CalcDialog", u"Cancel", None))
        self.lblCalcStatus.setText(QCoreApplication.translate("CalcDialog", u"Calculation information goes here.", None))
    # retranslateUi