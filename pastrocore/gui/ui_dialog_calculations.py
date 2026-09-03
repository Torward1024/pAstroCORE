# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_calculations.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_CalculationDialog(object):
    def setupUi(self, CalculationDialog):
        if not CalculationDialog.objectName():
            CalculationDialog.setObjectName(u"CalculationDialog")
        CalculationDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        CalculationDialog.resize(600, 450)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(CalculationDialog.sizePolicy().hasHeightForWidth())
        CalculationDialog.setSizePolicy(sizePolicy)
        CalculationDialog.setMinimumSize(QSize(600, 450))
        CalculationDialog.setMaximumSize(QSize(600, 450))
        icon = QIcon()
        icon.addFile(u":/icons/calculate.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CalculationDialog.setWindowIcon(icon)
        CalculationDialog.setModal(True)
        self.gridLayout_3 = QGridLayout(CalculationDialog)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.line = QFrame(CalculationDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line, 1, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.selectAllCalcButton = QPushButton(CalculationDialog)
        self.selectAllCalcButton.setObjectName(u"selectAllCalcButton")

        self.horizontalLayout_2.addWidget(self.selectAllCalcButton)

        self.clearAllCalcButton = QPushButton(CalculationDialog)
        self.clearAllCalcButton.setObjectName(u"clearAllCalcButton")

        self.horizontalLayout_2.addWidget(self.clearAllCalcButton)


        self.gridLayout.addLayout(self.horizontalLayout_2, 6, 2, 1, 1)

        self.targetList = QListWidget(CalculationDialog)
        self.targetList.setObjectName(u"targetList")
        self.targetList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.targetList, 3, 3, 1, 1)

        self.labelTargets = QLabel(CalculationDialog)
        self.labelTargets.setObjectName(u"labelTargets")

        self.gridLayout.addWidget(self.labelTargets, 2, 3, 1, 1)

        self.labelCalc = QLabel(CalculationDialog)
        self.labelCalc.setObjectName(u"labelCalc")

        self.gridLayout.addWidget(self.labelCalc, 2, 2, 1, 1)

        self.calcList = QListWidget(CalculationDialog)
        self.calcList.setObjectName(u"calcList")

        self.gridLayout.addWidget(self.calcList, 3, 2, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.selectAllObsButton = QPushButton(CalculationDialog)
        self.selectAllObsButton.setObjectName(u"selectAllObsButton")
        self.selectAllObsButton.setFlat(True)

        self.horizontalLayout.addWidget(self.selectAllObsButton)

        self.clearAllObsButton = QPushButton(CalculationDialog)
        self.clearAllObsButton.setObjectName(u"clearAllObsButton")

        self.horizontalLayout.addWidget(self.clearAllObsButton)


        self.gridLayout.addLayout(self.horizontalLayout, 6, 3, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.labelParameters = QLabel(CalculationDialog)
        self.labelParameters.setObjectName(u"labelParameters")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(False)
        self.labelParameters.setFont(font)

        self.gridLayout_3.addWidget(self.labelParameters, 2, 0, 1, 1)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.clrButton = QPushButton(CalculationDialog)
        self.clrButton.setObjectName(u"clrButton")

        self.buttonLayout.addWidget(self.clrButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.calcButton = QPushButton(CalculationDialog)
        self.calcButton.setObjectName(u"calcButton")
        self.calcButton.setAutoDefault(False)
        self.calcButton.setFlat(True)

        self.buttonLayout.addWidget(self.calcButton)

        self.cancelButton = QPushButton(CalculationDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setAutoDefault(True)
        self.cancelButton.setFlat(True)

        self.buttonLayout.addWidget(self.cancelButton)


        self.gridLayout_3.addLayout(self.buttonLayout, 5, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.labelTimestep = QLabel(CalculationDialog)
        self.labelTimestep.setObjectName(u"labelTimestep")

        self.gridLayout_2.addWidget(self.labelTimestep, 0, 0, 1, 1)

        self.timeStepSpin = QDoubleSpinBox(CalculationDialog)
        self.timeStepSpin.setObjectName(u"timeStepSpin")
        self.timeStepSpin.setMinimum(1.000000000000000)
        self.timeStepSpin.setMaximum(3600.000000000000000)
        self.timeStepSpin.setValue(600.000000000000000)

        self.gridLayout_2.addWidget(self.timeStepSpin, 0, 1, 1, 1)

        self.recalculateCheck = QCheckBox(CalculationDialog)
        self.recalculateCheck.setObjectName(u"recalculateCheck")
        self.recalculateCheck.setChecked(False)
        self.recalculateCheck.setTristate(False)

        self.gridLayout_2.addWidget(self.recalculateCheck, 1, 0, 1, 2)


        self.gridLayout_3.addLayout(self.gridLayout_2, 3, 0, 1, 1)

        self.line_2 = QFrame(CalculationDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line_2, 4, 0, 1, 1)


        self.retranslateUi(CalculationDialog)

        QMetaObject.connectSlotsByName(CalculationDialog)
    # setupUi

    def retranslateUi(self, CalculationDialog):
        CalculationDialog.setWindowTitle(QCoreApplication.translate("CalculationDialog", u"Perform Calculations", None))
        self.selectAllCalcButton.setText(QCoreApplication.translate("CalculationDialog", u"Select All", None))
        self.clearAllCalcButton.setText(QCoreApplication.translate("CalculationDialog", u"Clear", None))
        self.labelTargets.setText(QCoreApplication.translate("CalculationDialog", u"Observations:", None))
        self.labelCalc.setText(QCoreApplication.translate("CalculationDialog", u"Calculations:", None))
        self.selectAllObsButton.setText(QCoreApplication.translate("CalculationDialog", u"Select All", None))
        self.clearAllObsButton.setText(QCoreApplication.translate("CalculationDialog", u"Clear", None))
        self.labelParameters.setText(QCoreApplication.translate("CalculationDialog", u"Parameters:", None))
        self.clrButton.setText(QCoreApplication.translate("CalculationDialog", u"Clear Data", None))
        self.calcButton.setText(QCoreApplication.translate("CalculationDialog", u"Calculate", None))
        self.cancelButton.setText(QCoreApplication.translate("CalculationDialog", u"Cancel", None))
        self.labelTimestep.setText(QCoreApplication.translate("CalculationDialog", u"Time step (s):", None))
#if QT_CONFIG(tooltip)
        self.recalculateCheck.setToolTip(QCoreApplication.translate("CalculationDialog", u"A run already recomputes whatever has gone stale. Tick this only to recompute results that are current -- after a change to a calculation itself, which freshness cannot see.", None))
#endif // QT_CONFIG(tooltip)
        self.recalculateCheck.setText(QCoreApplication.translate("CalculationDialog", u"Recompute everything", None))
    # retranslateUi

