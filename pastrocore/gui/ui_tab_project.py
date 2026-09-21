# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_project.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QSizePolicy,
    QTableView, QWidget)

class Ui_ProjectInfoTab(object):
    def setupUi(self, ProjectInfoTab):
        if not ProjectInfoTab.objectName():
            ProjectInfoTab.setObjectName(u"ProjectInfoTab")
        ProjectInfoTab.resize(598, 468)
        self.gridLayout = QGridLayout(ProjectInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(ProjectInfoTab)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.lineEdit = QLineEdit(ProjectInfoTab)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setReadOnly(True)

        self.gridLayout.addWidget(self.lineEdit, 0, 1, 1, 1)

        self.search = QLineEdit(ProjectInfoTab)
        self.search.setObjectName(u"search")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumSize(QSize(260, 16777215))

        self.gridLayout.addWidget(self.search, 0, 2, 1, 1)

        self.projectInfoTable = QTableView(ProjectInfoTab)
        self.projectInfoTable.setObjectName(u"projectInfoTable")
        self.projectInfoTable.setFrameShadow(QFrame.Shadow.Plain)
        self.projectInfoTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projectInfoTable.setAlternatingRowColors(True)
        self.projectInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projectInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.projectInfoTable.setSortingEnabled(False)
        self.projectInfoTable.verticalHeader().setVisible(False)

        self.gridLayout.addWidget(self.projectInfoTable, 1, 0, 1, 3)


        self.retranslateUi(ProjectInfoTab)

        QMetaObject.connectSlotsByName(ProjectInfoTab)
    # setupUi

    def retranslateUi(self, ProjectInfoTab):
        self.label.setText(QCoreApplication.translate("ProjectInfoTab", u"Name:", None))
        self.search.setPlaceholderText(QCoreApplication.translate("ProjectInfoTab", u"Search observations...", None))
#if QT_CONFIG(tooltip)
        self.search.setToolTip(QCoreApplication.translate("ProjectInfoTab", u"Show only the observations matching this.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

