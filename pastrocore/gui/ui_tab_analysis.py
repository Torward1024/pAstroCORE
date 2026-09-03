# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_analysis.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_AnalysisTab(object):
    def setupUi(self, AnalysisTab):
        if not AnalysisTab.objectName():
            AnalysisTab.setObjectName(u"AnalysisTab")
        AnalysisTab.resize(900, 620)
        self.verticalLayout = QVBoxLayout(AnalysisTab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.questionBox = QGroupBox(AnalysisTab)
        self.questionBox.setObjectName(u"questionBox")
        self.questionForm = QFormLayout(self.questionBox)
        self.questionForm.setObjectName(u"questionForm")
        self.questionLabel = QLabel(self.questionBox)
        self.questionLabel.setObjectName(u"questionLabel")

        self.questionForm.setWidget(0, QFormLayout.LabelRole, self.questionLabel)

        self.questionCombo = QComboBox(self.questionBox)
        self.questionCombo.setObjectName(u"questionCombo")

        self.questionForm.setWidget(0, QFormLayout.FieldRole, self.questionCombo)

        self.resultLabel = QLabel(self.questionBox)
        self.resultLabel.setObjectName(u"resultLabel")

        self.questionForm.setWidget(1, QFormLayout.LabelRole, self.resultLabel)

        self.resultCombo = QComboBox(self.questionBox)
        self.resultCombo.setObjectName(u"resultCombo")

        self.questionForm.setWidget(1, QFormLayout.FieldRole, self.resultCombo)

        self.columnsLabel = QLabel(self.questionBox)
        self.columnsLabel.setObjectName(u"columnsLabel")

        self.questionForm.setWidget(2, QFormLayout.LabelRole, self.columnsLabel)

        self.columnsList = QListWidget(self.questionBox)
        self.columnsList.setObjectName(u"columnsList")
        self.columnsList.setMaximumSize(QSize(16777215, 90))
        self.columnsList.setSelectionMode(QAbstractItemView.MultiSelection)

        self.questionForm.setWidget(2, QFormLayout.FieldRole, self.columnsList)

        self.groupByLabel = QLabel(self.questionBox)
        self.groupByLabel.setObjectName(u"groupByLabel")

        self.questionForm.setWidget(3, QFormLayout.LabelRole, self.groupByLabel)

        self.groupByList = QListWidget(self.questionBox)
        self.groupByList.setObjectName(u"groupByList")
        self.groupByList.setMaximumSize(QSize(16777215, 70))
        self.groupByList.setSelectionMode(QAbstractItemView.MultiSelection)

        self.questionForm.setWidget(3, QFormLayout.FieldRole, self.groupByList)

        self.gapsCheck = QCheckBox(self.questionBox)
        self.gapsCheck.setObjectName(u"gapsCheck")

        self.questionForm.setWidget(4, QFormLayout.FieldRole, self.gapsCheck)

        self.atLeastLabel = QLabel(self.questionBox)
        self.atLeastLabel.setObjectName(u"atLeastLabel")

        self.questionForm.setWidget(5, QFormLayout.LabelRole, self.atLeastLabel)

        self.atLeastSpin = QSpinBox(self.questionBox)
        self.atLeastSpin.setObjectName(u"atLeastSpin")
        self.atLeastSpin.setMinimum(1)
        self.atLeastSpin.setMaximum(64)
        self.atLeastSpin.setValue(2)

        self.questionForm.setWidget(5, QFormLayout.FieldRole, self.atLeastSpin)


        self.verticalLayout.addWidget(self.questionBox)

        self.filtersBox = QGroupBox(AnalysisTab)
        self.filtersBox.setObjectName(u"filtersBox")
        self.filtersForm = QFormLayout(self.filtersBox)
        self.filtersForm.setObjectName(u"filtersForm")

        self.verticalLayout.addWidget(self.filtersBox)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.refreshButton = QPushButton(AnalysisTab)
        self.refreshButton.setObjectName(u"refreshButton")

        self.buttonRow.addWidget(self.refreshButton)

        self.askButton = QPushButton(AnalysisTab)
        self.askButton.setObjectName(u"askButton")

        self.buttonRow.addWidget(self.askButton)


        self.verticalLayout.addLayout(self.buttonRow)

        self.resultTable = QTableWidget(AnalysisTab)
        self.resultTable.setObjectName(u"resultTable")
        self.resultTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.resultTable.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout.addWidget(self.resultTable)

        self.statusLabel = QLabel(AnalysisTab)
        self.statusLabel.setObjectName(u"statusLabel")

        self.verticalLayout.addWidget(self.statusLabel)


        self.retranslateUi(AnalysisTab)

        QMetaObject.connectSlotsByName(AnalysisTab)
    # setupUi

    def retranslateUi(self, AnalysisTab):
        AnalysisTab.setWindowTitle(QCoreApplication.translate("AnalysisTab", u"Analysis", None))
        self.questionBox.setTitle(QCoreApplication.translate("AnalysisTab", u"What to ask", None))
        self.questionLabel.setText(QCoreApplication.translate("AnalysisTab", u"Question", None))
        self.resultLabel.setText(QCoreApplication.translate("AnalysisTab", u"Result", None))
        self.columnsLabel.setText(QCoreApplication.translate("AnalysisTab", u"Columns", None))
        self.groupByLabel.setText(QCoreApplication.translate("AnalysisTab", u"Group by", None))
        self.gapsCheck.setText(QCoreApplication.translate("AnalysisTab", u"Gaps instead of windows", None))
        self.atLeastLabel.setText(QCoreApplication.translate("AnalysisTab", u"Stations at once", None))
        self.filtersBox.setTitle(QCoreApplication.translate("AnalysisTab", u"Only these", None))
        self.refreshButton.setText(QCoreApplication.translate("AnalysisTab", u"Refresh", None))
        self.askButton.setText(QCoreApplication.translate("AnalysisTab", u"Ask", None))
        self.statusLabel.setText("")
    # retranslateUi

