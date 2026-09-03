# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_add_observation.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFrame,
    QGridLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_AddObservationDialog(object):
    def setupUi(self, AddObservationDialog):
        if not AddObservationDialog.objectName():
            AddObservationDialog.setObjectName(u"AddObservationDialog")
        AddObservationDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        AddObservationDialog.resize(330, 120)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(AddObservationDialog.sizePolicy().hasHeightForWidth())
        AddObservationDialog.setSizePolicy(sizePolicy)
        AddObservationDialog.setMinimumSize(QSize(330, 120))
        AddObservationDialog.setMaximumSize(QSize(330, 120))
        icon = QIcon()
        icon.addFile(u":/icons/add_observation_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        AddObservationDialog.setWindowIcon(icon)
        AddObservationDialog.setModal(True)
        self.gridLayout = QGridLayout(AddObservationDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.combo_obs_type = QComboBox(AddObservationDialog)
        self.combo_obs_type.setObjectName(u"combo_obs_type")
        self.combo_obs_type.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(150)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.combo_obs_type.sizePolicy().hasHeightForWidth())
        self.combo_obs_type.setSizePolicy(sizePolicy1)
        self.combo_obs_type.setMinimumSize(QSize(150, 0))
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.combo_obs_type.setFont(font)

        self.gridLayout.addWidget(self.combo_obs_type, 2, 1, 1, 2)

        self.okButton = QPushButton(AddObservationDialog)
        self.okButton.setObjectName(u"okButton")
        self.okButton.setFlat(True)

        self.gridLayout.addWidget(self.okButton, 4, 1, 1, 1)

        self.label = QLabel(AddObservationDialog)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 2, 0, 1, 1)

        self.obs_code = QLineEdit(AddObservationDialog)
        self.obs_code.setObjectName(u"obs_code")
        self.obs_code.setFont(font)

        self.gridLayout.addWidget(self.obs_code, 0, 1, 1, 2)

        self.lbl_obs_code = QLabel(AddObservationDialog)
        self.lbl_obs_code.setObjectName(u"lbl_obs_code")
        self.lbl_obs_code.setFont(font)

        self.gridLayout.addWidget(self.lbl_obs_code, 0, 0, 1, 1)

        self.closeButton = QPushButton(AddObservationDialog)
        self.closeButton.setObjectName(u"closeButton")
        self.closeButton.setAutoDefault(False)
        self.closeButton.setFlat(True)

        self.gridLayout.addWidget(self.closeButton, 4, 2, 1, 1)

        self.line = QFrame(AddObservationDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 3)

        self.line_2 = QFrame(AddObservationDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 3, 0, 1, 3)


        self.retranslateUi(AddObservationDialog)

        QMetaObject.connectSlotsByName(AddObservationDialog)
    # setupUi

    def retranslateUi(self, AddObservationDialog):
        AddObservationDialog.setWindowTitle(QCoreApplication.translate("AddObservationDialog", u"Dialog", None))
        self.combo_obs_type.setCurrentText("")
        self.okButton.setText(QCoreApplication.translate("AddObservationDialog", u"OK", None))
        self.label.setText(QCoreApplication.translate("AddObservationDialog", u"Observation type:", None))
        self.lbl_obs_code.setText(QCoreApplication.translate("AddObservationDialog", u"Observation code:", None))
        self.closeButton.setText(QCoreApplication.translate("AddObservationDialog", u"Cancel", None))
    # retranslateUi

