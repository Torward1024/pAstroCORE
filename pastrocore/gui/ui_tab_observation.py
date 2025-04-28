# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_observationPClLSD.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QSizePolicy,
    QSpacerItem, QTabWidget, QTableView, QWidget)

class Ui_ObservationInfoTab(object):
    def setupUi(self, ObservationInfoTab):
        if not ObservationInfoTab.objectName():
            ObservationInfoTab.setObjectName(u"ObservationInfoTab")
        ObservationInfoTab.resize(587, 471)
        ObservationInfoTab.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        self.gridLayout = QGridLayout(ObservationInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(ObservationInfoTab)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 1, 2, 1, 1)

        self.tabWidget = QTabWidget(ObservationInfoTab)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setStyleSheet(u"QTabWidget::pane { border: 1px solid #d3d3d3; background: #ffffff; }\n"
"               QTabBar::tab { background: #e0e0e0; padding: 8px; }\n"
"               QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #0078d7; }")
        self.tab_freq = QWidget()
        self.tab_freq.setObjectName(u"tab_freq")
        self.gridLayout_2 = QGridLayout(self.tab_freq)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.search_freqs = QLineEdit(self.tab_freq)
        self.search_freqs.setObjectName(u"search_freqs")
        self.search_freqs.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout_2.addWidget(self.search_freqs, 1, 1, 1, 1)

        self.lbl_search_freqs = QLabel(self.tab_freq)
        self.lbl_search_freqs.setObjectName(u"lbl_search_freqs")

        self.gridLayout_2.addWidget(self.lbl_search_freqs, 1, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer, 1, 2, 1, 1)

        self.frequencies_table = QTableView(self.tab_freq)
        self.frequencies_table.setObjectName(u"frequencies_table")
        self.frequencies_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.frequencies_table.setAlternatingRowColors(True)
        self.frequencies_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.frequencies_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_2.addWidget(self.frequencies_table, 0, 0, 1, 3)

        self.tabWidget.addTab(self.tab_freq, "")
        self.tab_sources = QWidget()
        self.tab_sources.setObjectName(u"tab_sources")
        self.gridLayout_3 = QGridLayout(self.tab_sources)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.lbl_search_sources = QLabel(self.tab_sources)
        self.lbl_search_sources.setObjectName(u"lbl_search_sources")

        self.gridLayout_3.addWidget(self.lbl_search_sources, 1, 0, 1, 1)

        self.search_sources = QLineEdit(self.tab_sources)
        self.search_sources.setObjectName(u"search_sources")
        self.search_sources.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout_3.addWidget(self.search_sources, 1, 1, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_2, 1, 2, 1, 1)

        self.sources_table = QTableView(self.tab_sources)
        self.sources_table.setObjectName(u"sources_table")
        self.sources_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sources_table.setAlternatingRowColors(True)
        self.sources_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sources_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_3.addWidget(self.sources_table, 0, 0, 1, 3)

        self.tabWidget.addTab(self.tab_sources, "")
        self.tab_tels = QWidget()
        self.tab_tels.setObjectName(u"tab_tels")
        self.gridLayout_4 = QGridLayout(self.tab_tels)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.lbl_search_telescopes = QLabel(self.tab_tels)
        self.lbl_search_telescopes.setObjectName(u"lbl_search_telescopes")

        self.gridLayout_4.addWidget(self.lbl_search_telescopes, 1, 0, 1, 1)

        self.search_telescopes = QLineEdit(self.tab_tels)
        self.search_telescopes.setObjectName(u"search_telescopes")
        self.search_telescopes.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout_4.addWidget(self.search_telescopes, 1, 1, 1, 1)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_4.addItem(self.horizontalSpacer_3, 1, 2, 1, 1)

        self.telescopes_table = QTableView(self.tab_tels)
        self.telescopes_table.setObjectName(u"telescopes_table")
        self.telescopes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.telescopes_table.setAlternatingRowColors(True)
        self.telescopes_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.telescopes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_4.addWidget(self.telescopes_table, 0, 0, 1, 3)

        self.tabWidget.addTab(self.tab_tels, "")
        self.tab_scans = QWidget()
        self.tab_scans.setObjectName(u"tab_scans")
        self.gridLayout_5 = QGridLayout(self.tab_scans)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.lbl_search_scans = QLabel(self.tab_scans)
        self.lbl_search_scans.setObjectName(u"lbl_search_scans")

        self.gridLayout_5.addWidget(self.lbl_search_scans, 1, 0, 1, 1)

        self.search_scans = QLineEdit(self.tab_scans)
        self.search_scans.setObjectName(u"search_scans")
        self.search_scans.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout_5.addWidget(self.search_scans, 1, 1, 1, 1)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_5.addItem(self.horizontalSpacer_4, 1, 2, 1, 1)

        self.scans_table = QTableView(self.tab_scans)
        self.scans_table.setObjectName(u"scans_table")
        self.scans_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.scans_table.setAlternatingRowColors(True)
        self.scans_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.scans_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout_5.addWidget(self.scans_table, 0, 0, 1, 3)

        self.tabWidget.addTab(self.tab_scans, "")

        self.gridLayout.addWidget(self.tabWidget, 3, 0, 1, 5)

        self.obs_name_edit = QLineEdit(ObservationInfoTab)
        self.obs_name_edit.setObjectName(u"obs_name_edit")
        self.obs_name_edit.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout.addWidget(self.obs_name_edit, 1, 1, 1, 1)

        self.lbl_obs_info = QLabel(ObservationInfoTab)
        self.lbl_obs_info.setObjectName(u"lbl_obs_info")

        self.gridLayout.addWidget(self.lbl_obs_info, 2, 0, 1, 3)

        self.titleLabel = QLabel(ObservationInfoTab)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        font.setBold(True)
        self.titleLabel.setFont(font)

        self.gridLayout.addWidget(self.titleLabel, 1, 0, 1, 1)

        self.combo_obs_type = QComboBox(ObservationInfoTab)
        self.combo_obs_type.setObjectName(u"combo_obs_type")
        self.combo_obs_type.setMinimumSize(QSize(66, 0))
        self.combo_obs_type.setMaximumSize(QSize(66, 16777215))

        self.gridLayout.addWidget(self.combo_obs_type, 1, 4, 1, 1)


        self.retranslateUi(ObservationInfoTab)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ObservationInfoTab)
    # setupUi

    def retranslateUi(self, ObservationInfoTab):
        self.label.setText(QCoreApplication.translate("ObservationInfoTab", u"Type:", None))
        self.lbl_search_freqs.setText(QCoreApplication.translate("ObservationInfoTab", u"Search:", None))
        self.frequencies_table.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_freq), QCoreApplication.translate("ObservationInfoTab", u"Frequencies", None))
        self.lbl_search_sources.setText(QCoreApplication.translate("ObservationInfoTab", u"Search:", None))
        self.sources_table.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_sources), QCoreApplication.translate("ObservationInfoTab", u"Sources", None))
        self.lbl_search_telescopes.setText(QCoreApplication.translate("ObservationInfoTab", u"Search:", None))
        self.telescopes_table.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_tels), QCoreApplication.translate("ObservationInfoTab", u"Telescopes", None))
        self.lbl_search_scans.setText(QCoreApplication.translate("ObservationInfoTab", u"Search:", None))
        self.scans_table.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_scans), QCoreApplication.translate("ObservationInfoTab", u"Scans", None))
        self.lbl_obs_info.setText(QCoreApplication.translate("ObservationInfoTab", u"Start Time/Date: [get_start_time_date] Duration: [DURATION] sec.", None))
        self.titleLabel.setStyleSheet(QCoreApplication.translate("ObservationInfoTab", u"color: #333333; padding-bottom: 10px;", None))
        self.titleLabel.setText(QCoreApplication.translate("ObservationInfoTab", u"Observation:", None))
        self.combo_obs_type.setCurrentText("")
        pass
    # retranslateUi