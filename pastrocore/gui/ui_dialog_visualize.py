# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_visualize.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QTabWidget,
    QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_VisualizationDialog(object):
    def setupUi(self, VisualizationDialog):
        if not VisualizationDialog.objectName():
            VisualizationDialog.setObjectName(u"VisualizationDialog")
        VisualizationDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        VisualizationDialog.resize(1090, 802)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(VisualizationDialog.sizePolicy().hasHeightForWidth())
        VisualizationDialog.setSizePolicy(sizePolicy)
        icon = QIcon()
        icon.addFile(u":/icons/visualize.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        VisualizationDialog.setWindowIcon(icon)
        VisualizationDialog.setSizeGripEnabled(True)
        VisualizationDialog.setModal(True)
        self.gridLayout_3 = QGridLayout(VisualizationDialog)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(VisualizationDialog)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.comboBoxObservation = QComboBox(VisualizationDialog)
        self.comboBoxObservation.setObjectName(u"comboBoxObservation")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.comboBoxObservation)

        self.labelVisualizationType = QLabel(VisualizationDialog)
        self.labelVisualizationType.setObjectName(u"labelVisualizationType")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.labelVisualizationType.setFont(font)

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.labelVisualizationType)

        self.comboBoxVisualizationType = QComboBox(VisualizationDialog)
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.addItem("")
        self.comboBoxVisualizationType.setObjectName(u"comboBoxVisualizationType")
        self.comboBoxVisualizationType.setFont(font)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.comboBoxVisualizationType)


        self.gridLayout.addLayout(self.formLayout, 0, 0, 1, 1)

        self.pushButtonVisualize = QPushButton(VisualizationDialog)
        self.pushButtonVisualize.setObjectName(u"pushButtonVisualize")
        self.pushButtonVisualize.setFont(font)

        self.gridLayout.addWidget(self.pushButtonVisualize, 0, 3, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 1, 1, 1)

        self.pushButton = QPushButton(VisualizationDialog)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 0, 2, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 0, 1, 2)

        self.tabWidget = QTabWidget(VisualizationDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setTabsClosable(True)

        self.gridLayout_3.addWidget(self.tabWidget, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.closeButton = QPushButton(VisualizationDialog)
        self.closeButton.setObjectName(u"closeButton")

        self.horizontalLayout.addWidget(self.closeButton)


        self.gridLayout_3.addLayout(self.horizontalLayout, 4, 0, 1, 1)

        self.line = QFrame(VisualizationDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line, 3, 0, 1, 1)

        self.line_2 = QFrame(VisualizationDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line_2, 1, 0, 1, 1)


        self.retranslateUi(VisualizationDialog)

        self.tabWidget.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(VisualizationDialog)
    # setupUi

    def retranslateUi(self, VisualizationDialog):
        VisualizationDialog.setWindowTitle(QCoreApplication.translate("VisualizationDialog", u"Visualize Observation", None))
        self.label.setText(QCoreApplication.translate("VisualizationDialog", u"Observation:", None))
        self.labelVisualizationType.setText(QCoreApplication.translate("VisualizationDialog", u"Visualization Type:", None))
        self.comboBoxVisualizationType.setItemText(0, QCoreApplication.translate("VisualizationDialog", u"UV Coverage", None))
        self.comboBoxVisualizationType.setItemText(1, QCoreApplication.translate("VisualizationDialog", u"Source Visibility", None))
        self.comboBoxVisualizationType.setItemText(2, QCoreApplication.translate("VisualizationDialog", u"Sun Angles", None))
        self.comboBoxVisualizationType.setItemText(3, QCoreApplication.translate("VisualizationDialog", u"Az/El or HA/Dec", None))
        self.comboBoxVisualizationType.setItemText(4, QCoreApplication.translate("VisualizationDialog", u"Time on Source", None))
        self.comboBoxVisualizationType.setItemText(5, QCoreApplication.translate("VisualizationDialog", u"Beam Pattern", None))
        self.comboBoxVisualizationType.setItemText(6, QCoreApplication.translate("VisualizationDialog", u"Synthesized Beam", None))
        self.comboBoxVisualizationType.setItemText(7, QCoreApplication.translate("VisualizationDialog", u"Baseline Projections", None))
        self.comboBoxVisualizationType.setItemText(8, QCoreApplication.translate("VisualizationDialog", u"Mollweide Tracks", None))

        self.pushButtonVisualize.setText(QCoreApplication.translate("VisualizationDialog", u"View", None))
        self.pushButton.setText(QCoreApplication.translate("VisualizationDialog", u"Export", None))
        self.closeButton.setText(QCoreApplication.translate("VisualizationDialog", u"Close", None))
    # retranslateUi

