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
    QSpacerItem, QTableView, QWidget)

class Ui_ProjectInfoTab(object):
    def setupUi(self, ProjectInfoTab):
        if not ProjectInfoTab.objectName():
            ProjectInfoTab.setObjectName(u"ProjectInfoTab")
        ProjectInfoTab.resize(598, 468)
        self.gridLayout = QGridLayout(ProjectInfoTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(ProjectInfoTab)
        self.label_2.setObjectName(u"label_2")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.label_2.setFont(font)

        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)

        self.line = QFrame(ProjectInfoTab)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 3, 0, 1, 3)

        self.label = QLabel(ProjectInfoTab)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(9)
        font1.setBold(False)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 2, 1, 1)

        self.projectInfoTable = QTableView(ProjectInfoTab)
        self.projectInfoTable.setObjectName(u"projectInfoTable")
        self.projectInfoTable.setFrameShadow(QFrame.Shadow.Sunken)
        self.projectInfoTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projectInfoTable.setAlternatingRowColors(True)
        self.projectInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projectInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.projectInfoTable.setSortingEnabled(False)
        self.projectInfoTable.verticalHeader().setVisible(False)

        self.gridLayout.addWidget(self.projectInfoTable, 2, 0, 1, 3)

        self.lineEdit = QLineEdit(ProjectInfoTab)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setFont(font)
        self.lineEdit.setReadOnly(True)

        self.gridLayout.addWidget(self.lineEdit, 0, 1, 1, 1)

        self.search = QLineEdit(ProjectInfoTab)
        self.search.setObjectName(u"search")

        self.gridLayout.addWidget(self.search, 4, 1, 1, 1)

        self.line_2 = QFrame(ProjectInfoTab)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 1, 0, 1, 3)


        self.retranslateUi(ProjectInfoTab)

        QMetaObject.connectSlotsByName(ProjectInfoTab)
    # setupUi

    def retranslateUi(self, ProjectInfoTab):
        self.label_2.setText(QCoreApplication.translate("ProjectInfoTab", u"Search:", None))
        self.label.setText(QCoreApplication.translate("ProjectInfoTab", u"Name:", None))
        pass
    # retranslateUi

