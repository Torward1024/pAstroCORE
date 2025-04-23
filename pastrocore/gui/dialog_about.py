# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_aboutITJQQq.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QLabel,
    QPushButton, QSizePolicy, QWidget)

class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName(u"AboutDialog")
        AboutDialog.resize(319, 251)
        AboutDialog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        AboutDialog.setModal(True)
        self.labelTitle = QLabel(AboutDialog)
        self.labelTitle.setObjectName(u"labelTitle")
        self.labelTitle.setGeometry(QRect(150, 20, 151, 41))
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(16)
        font.setBold(False)
        self.labelTitle.setFont(font)
        self.labelTitle.setFrameShape(QFrame.Shape.NoFrame)
        self.labelTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelVersion = QLabel(AboutDialog)
        self.labelVersion.setObjectName(u"labelVersion")
        self.labelVersion.setGeometry(QRect(190, 80, 75, 16))
        self.labelVersion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelDescription = QLabel(AboutDialog)
        self.labelDescription.setObjectName(u"labelDescription")
        self.labelDescription.setGeometry(QRect(10, 150, 301, 28))
        self.labelDescription.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelDescription.setWordWrap(True)
        self.label = QLabel(AboutDialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(4, 192, 311, 20))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.closeButton = QPushButton(AboutDialog)
        self.closeButton.setObjectName(u"closeButton")
        self.closeButton.setGeometry(QRect(210, 220, 101, 26))
        self.closeButton.setFlat(True)
        self.label_2 = QLabel(AboutDialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 10, 121, 123))
        self.label_2.setPixmap(QPixmap(u"./pastrocore/gui/pAstroCORE_icon.png"))
        self.label_2.setScaledContents(True)

        self.retranslateUi(AboutDialog)
        self.closeButton.clicked.connect(AboutDialog.accept)

        QMetaObject.connectSlotsByName(AboutDialog)
    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QCoreApplication.translate("AboutDialog", u"About pAstroCORE", None))
        AboutDialog.setStyleSheet(QCoreApplication.translate("AboutDialog", u"background-color: #ffffff; font-family: Arial;", None))
        self.labelTitle.setText(QCoreApplication.translate("AboutDialog", u"pAstroCORE", None))
        self.labelVersion.setText(QCoreApplication.translate("AboutDialog", u"Version 0.01b", None))
        self.labelDescription.setText(QCoreApplication.translate("AboutDialog", u"A versatile tool for VLBI observation planning and visualization.", None))
        self.label.setText(QCoreApplication.translate("AboutDialog", u"Ballistics Laboratory, Astro Space Center LPI, 2025", None))
        self.closeButton.setStyleSheet(QCoreApplication.translate("AboutDialog", u"background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px;", None))
        self.closeButton.setText(QCoreApplication.translate("AboutDialog", u"Close", None))
        self.label_2.setText("")
    # retranslateUi