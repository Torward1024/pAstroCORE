# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_aboutxeHKcI.ui'
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName(u"AboutDialog")
        AboutDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        AboutDialog.resize(300, 300)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(AboutDialog.sizePolicy().hasHeightForWidth())
        AboutDialog.setSizePolicy(sizePolicy)
        AboutDialog.setMinimumSize(QSize(300, 300))
        AboutDialog.setMaximumSize(QSize(300, 300))
        icon = QIcon()
        icon.addFile(u":/icons/about_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        AboutDialog.setWindowIcon(icon)
        AboutDialog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        AboutDialog.setModal(True)
        self.gridLayout_2 = QGridLayout(AboutDialog)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.labelTitle = QLabel(AboutDialog)
        self.labelTitle.setObjectName(u"labelTitle")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(16)
        font.setBold(False)
        self.labelTitle.setFont(font)
        self.labelTitle.setFrameShape(QFrame.Shape.NoFrame)
        self.labelTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.labelTitle, 1, 1, 1, 1)

        self.label_2 = QLabel(AboutDialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(120, 120))
        self.label_2.setMaximumSize(QSize(120, 120))
        self.label_2.setPixmap(QPixmap(u":/icons/pAstroCORE_icon.png"))
        self.label_2.setScaledContents(True)

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.line_3 = QFrame(AboutDialog)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_3, 4, 0, 1, 2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 12, 0, 1, 1)

        self.line_4 = QFrame(AboutDialog)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_4, 10, 0, 1, 2)

        self.label = QLabel(AboutDialog)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label, 9, 0, 1, 2)

        self.closeButton = QPushButton(AboutDialog)
        self.closeButton.setObjectName(u"closeButton")
        self.closeButton.setStyleSheet(u"QPushButton {\n"
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
        self.closeButton.setFlat(True)

        self.gridLayout.addWidget(self.closeButton, 12, 1, 1, 1)

        self.labelDescription = QLabel(AboutDialog)
        self.labelDescription.setObjectName(u"labelDescription")
        self.labelDescription.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelDescription.setWordWrap(True)

        self.gridLayout.addWidget(self.labelDescription, 7, 0, 1, 2)

        self.labelVersion = QLabel(AboutDialog)
        self.labelVersion.setObjectName(u"labelVersion")
        self.labelVersion.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.labelVersion, 5, 0, 1, 2)

        self.line = QFrame(AboutDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 6, 0, 1, 2)

        self.line_2 = QFrame(AboutDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 8, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 2, 0, 1, 2)


        self.retranslateUi(AboutDialog)
        self.closeButton.clicked.connect(AboutDialog.accept)

        QMetaObject.connectSlotsByName(AboutDialog)
    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QCoreApplication.translate("AboutDialog", u"About pAstroCORE", None))
        AboutDialog.setStyleSheet(QCoreApplication.translate("AboutDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelTitle.setText(QCoreApplication.translate("AboutDialog", u"pAstroCORE", None))
        self.label_2.setText("")
        self.label.setText(QCoreApplication.translate("AboutDialog", u"Ballistics Laboratory\n"
"Astro Space Center LPI, 2018-2025", None))
        self.closeButton.setText(QCoreApplication.translate("AboutDialog", u"Close", None))
        self.labelDescription.setText(QCoreApplication.translate("AboutDialog", u"A versatile tool for  radio astronomical observations\n"
" planning and visualization.", None))
        self.labelVersion.setText(QCoreApplication.translate("AboutDialog", u"Version 0.0.92a", None))
    # retranslateUi