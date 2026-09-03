# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpinBox,
    QTabWidget, QWidget)
from pastrocore.gui import rc_icons  # noqa: F401
class Ui_PreferencesDialog(object):
    def setupUi(self, PreferencesDialog):
        if not PreferencesDialog.objectName():
            PreferencesDialog.setObjectName(u"PreferencesDialog")
        PreferencesDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        PreferencesDialog.resize(450, 350)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(PreferencesDialog.sizePolicy().hasHeightForWidth())
        PreferencesDialog.setSizePolicy(sizePolicy)
        PreferencesDialog.setMinimumSize(QSize(450, 350))
        PreferencesDialog.setMaximumSize(QSize(450, 350))
        icon = QIcon()
        icon.addFile(u":/icons/preferences.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        PreferencesDialog.setWindowIcon(icon)
        PreferencesDialog.setModal(True)
        self.gridLayout = QGridLayout(PreferencesDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.tabWidget = QTabWidget(PreferencesDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_3 = QGridLayout(self.tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lbl_telescopes_catalog_path = QLabel(self.tab)
        self.lbl_telescopes_catalog_path.setObjectName(u"lbl_telescopes_catalog_path")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.lbl_telescopes_catalog_path.setFont(font)

        self.gridLayout_2.addWidget(self.lbl_telescopes_catalog_path, 1, 0, 1, 1)

        self.openSourcesCatalogButton = QPushButton(self.tab)
        self.openSourcesCatalogButton.setObjectName(u"openSourcesCatalogButton")
        self.openSourcesCatalogButton.setAutoDefault(False)
        self.openSourcesCatalogButton.setFlat(True)

        self.gridLayout_2.addWidget(self.openSourcesCatalogButton, 0, 2, 1, 1)

        self.sourcesCatalogPath = QLineEdit(self.tab)
        self.sourcesCatalogPath.setObjectName(u"sourcesCatalogPath")

        self.gridLayout_2.addWidget(self.sourcesCatalogPath, 0, 1, 1, 1)

        self.lbl_sources_catalog_path = QLabel(self.tab)
        self.lbl_sources_catalog_path.setObjectName(u"lbl_sources_catalog_path")
        self.lbl_sources_catalog_path.setFont(font)

        self.gridLayout_2.addWidget(self.lbl_sources_catalog_path, 0, 0, 1, 1)

        self.openTelescopesCatalogButton = QPushButton(self.tab)
        self.openTelescopesCatalogButton.setObjectName(u"openTelescopesCatalogButton")
        self.openTelescopesCatalogButton.setAutoDefault(False)
        self.openTelescopesCatalogButton.setFlat(True)

        self.gridLayout_2.addWidget(self.openTelescopesCatalogButton, 1, 2, 1, 1)

        self.comboLogging = QComboBox(self.tab)
        self.comboLogging.setObjectName(u"comboLogging")

        self.gridLayout_2.addWidget(self.comboLogging, 2, 1, 1, 1)

        self.telescopesCatalogPath = QLineEdit(self.tab)
        self.telescopesCatalogPath.setObjectName(u"telescopesCatalogPath")

        self.gridLayout_2.addWidget(self.telescopesCatalogPath, 1, 1, 1, 1)

        self.labelLogging = QLabel(self.tab)
        self.labelLogging.setObjectName(u"labelLogging")

        self.gridLayout_2.addWidget(self.labelLogging, 2, 0, 1, 1)

        self.chkClearLog = QCheckBox(self.tab)
        self.chkClearLog.setObjectName(u"chkClearLog")

        self.gridLayout_2.addWidget(self.chkClearLog, 3, 0, 1, 3)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 0, 1, 2)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_4 = QGridLayout(self.tab_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.labelTimestep = QLabel(self.tab_2)
        self.labelTimestep.setObjectName(u"labelTimestep")

        self.horizontalLayout.addWidget(self.labelTimestep)

        self.timeStepSpin = QDoubleSpinBox(self.tab_2)
        self.timeStepSpin.setObjectName(u"timeStepSpin")
        self.timeStepSpin.setMinimum(1.000000000000000)
        self.timeStepSpin.setMaximum(99999999.000000000000000)
        self.timeStepSpin.setValue(600.000000000000000)

        self.horizontalLayout.addWidget(self.timeStepSpin)


        self.gridLayout_4.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.horizontalLayoutResultsMemory = QHBoxLayout()
        self.horizontalLayoutResultsMemory.setObjectName(u"horizontalLayoutResultsMemory")
        self.labelResultsMemory = QLabel(self.tab_2)
        self.labelResultsMemory.setObjectName(u"labelResultsMemory")

        self.horizontalLayoutResultsMemory.addWidget(self.labelResultsMemory)

        self.resultsMemorySpin = QSpinBox(self.tab_2)
        self.resultsMemorySpin.setObjectName(u"resultsMemorySpin")
        self.resultsMemorySpin.setMinimum(5)
        self.resultsMemorySpin.setMaximum(100)
        self.resultsMemorySpin.setValue(50)

        self.horizontalLayoutResultsMemory.addWidget(self.resultsMemorySpin)


        self.gridLayout_4.addLayout(self.horizontalLayoutResultsMemory, 1, 0, 1, 1)

        self.tabWidget.addTab(self.tab_2, "")

        self.gridLayout.addWidget(self.tabWidget, 3, 0, 1, 5)

        self.cancelButton = QPushButton(PreferencesDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setAutoDefault(False)
        self.cancelButton.setFlat(True)

        self.gridLayout.addWidget(self.cancelButton, 5, 4, 1, 1)

        self.okButton = QPushButton(PreferencesDialog)
        self.okButton.setObjectName(u"okButton")
        self.okButton.setAutoDefault(True)
        self.okButton.setFlat(True)

        self.gridLayout.addWidget(self.okButton, 5, 3, 1, 1)


        self.retranslateUi(PreferencesDialog)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PreferencesDialog)
    # setupUi

    def retranslateUi(self, PreferencesDialog):
        PreferencesDialog.setWindowTitle(QCoreApplication.translate("PreferencesDialog", u"Dialog", None))
        self.lbl_telescopes_catalog_path.setText(QCoreApplication.translate("PreferencesDialog", u"Telescopes catalog path:", None))
        self.openSourcesCatalogButton.setText(QCoreApplication.translate("PreferencesDialog", u"Open...", None))
        self.lbl_sources_catalog_path.setText(QCoreApplication.translate("PreferencesDialog", u"Sources catalog path:", None))
        self.openTelescopesCatalogButton.setText(QCoreApplication.translate("PreferencesDialog", u"Open...", None))
        self.labelLogging.setText(QCoreApplication.translate("PreferencesDialog", u"Logging level:", None))
        self.chkClearLog.setText(QCoreApplication.translate("PreferencesDialog", u"Clear log-file on start", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("PreferencesDialog", u"Common", None))
        self.labelTimestep.setText(QCoreApplication.translate("PreferencesDialog", u"Time step (s):", None))
        self.labelResultsMemory.setText(QCoreApplication.translate("PreferencesDialog", u"Results in memory, share of available:", None))
#if QT_CONFIG(tooltip)
        self.resultsMemorySpin.setToolTip(QCoreApplication.translate("PreferencesDialog", u"Share of available memory the calculated results may occupy before the least recently used are dropped. They are read back from the project directory when needed again, so this costs a read rather than a recalculation.", None))
#endif // QT_CONFIG(tooltip)
        self.resultsMemorySpin.setSuffix(QCoreApplication.translate("PreferencesDialog", u" %", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("PreferencesDialog", u"Calculations", None))
        self.cancelButton.setText(QCoreApplication.translate("PreferencesDialog", u"Cancel", None))
        self.okButton.setText(QCoreApplication.translate("PreferencesDialog", u"OK", None))
    # retranslateUi

