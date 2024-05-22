# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextBrowser, QWidget)

class Ui_CDIGradingTool(object):
    def setupUi(self, CDIGradingTool):
        if not CDIGradingTool.objectName():
            CDIGradingTool.setObjectName(u"CDIGradingTool")
        CDIGradingTool.resize(959, 477)
        CDIGradingTool.setStyleSheet(u"		QMainWindow {\n"
"            background-color: #ffffff;\n"
"            color: #000000;\n"
"            selection-background-color: #5cb85c;\n"
"            selection-color: #000000;\n"
"        }")
        self.actionExit = QAction(CDIGradingTool)
        self.actionExit.setObjectName(u"actionExit")
        self.erase_it_central_widget = QWidget(CDIGradingTool)
        self.erase_it_central_widget.setObjectName(u"erase_it_central_widget")
        self.erase_it_central_widget.setStyleSheet(u"")
        self.gridLayout = QGridLayout(self.erase_it_central_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.logo_lbl = QLabel(self.erase_it_central_widget)
        self.logo_lbl.setObjectName(u"logo_lbl")
        self.logo_lbl.setMaximumSize(QSize(175, 100))
        self.logo_lbl.setAutoFillBackground(False)
        self.logo_lbl.setFrameShadow(QFrame.Plain)
        self.logo_lbl.setLineWidth(0)
        self.logo_lbl.setTextFormat(Qt.AutoText)
        self.logo_lbl.setPixmap(QPixmap(u"assets/images/cdi.png"))
        self.logo_lbl.setScaledContents(True)
        self.logo_lbl.setAlignment(Qt.AlignCenter)
        self.logo_lbl.setTextInteractionFlags(Qt.NoTextInteraction)

        self.header_layout.addWidget(self.logo_lbl)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout.addItem(self.header_spacer)

        self.devices_count = QLabel(self.erase_it_central_widget)
        self.devices_count.setObjectName(u"devices_count")
        self.devices_count.setStyleSheet(u"color: #3b7351;")

        self.header_layout.addWidget(self.devices_count)

        self.jobs_count = QLabel(self.erase_it_central_widget)
        self.jobs_count.setObjectName(u"jobs_count")
        self.jobs_count.setStyleSheet(u"color: #3b7351;")

        self.header_layout.addWidget(self.jobs_count)


        self.gridLayout.addLayout(self.header_layout, 0, 0, 1, 1)

        self.header_layout_2 = QHBoxLayout()
        self.header_layout_2.setObjectName(u"header_layout_2")
        self.power_button = QPushButton(self.erase_it_central_widget)
        self.power_button.setObjectName(u"power_button")
        self.power_button.setStyleSheet(u" background-color: #914343;\n"
" color: #fff;")

        self.header_layout_2.addWidget(self.power_button)

        self.settings_button = QPushButton(self.erase_it_central_widget)
        self.settings_button.setObjectName(u"settings_button")
        self.settings_button.setStyleSheet(u"background-color: #3b7351;\n"
"color: rgb(255, 255, 255);")

        self.header_layout_2.addWidget(self.settings_button)

        self.manual_button = QPushButton(self.erase_it_central_widget)
        self.manual_button.setObjectName(u"manual_button")
        self.manual_button.setStyleSheet(u"background-color: #3b7351;\n"
"color: rgb(255, 255, 255);")

        self.header_layout_2.addWidget(self.manual_button)

        self.about_button = QPushButton(self.erase_it_central_widget)
        self.about_button.setObjectName(u"about_button")
        self.about_button.setStyleSheet(u"background-color: #3b7351;\n"
"color: rgb(255, 255, 255);")

        self.header_layout_2.addWidget(self.about_button)

        self.header_spacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout_2.addItem(self.header_spacer_2)

        self.time_label = QLabel(self.erase_it_central_widget)
        self.time_label.setObjectName(u"time_label")

        self.header_layout_2.addWidget(self.time_label)


        self.gridLayout.addLayout(self.header_layout_2, 2, 0, 1, 1)

        self.tab_widget = QTabWidget(self.erase_it_central_widget)
        self.tab_widget.setObjectName(u"tab_widget")
        self.tab_widget.setStyleSheet(u"	QTabWidget::pane {\n"
"        border: none;\n"
"        border-bottom-left-radius: 4px;\n"
"        border-bottom-right-radius: 4px;\n"
"        background-color: 	#3e6071;\n"
"        \n"
"    }\n"
"    \n"
"    QTabWidget::tab-bar {\n"
"        spacing: 5px;\n"
"    }\n"
"    \n"
"    QTabBar::tab {\n"
"        background-color:  #9298a6;\n"
"        border-top-left-radius: 3px;\n"
"        border-top-right-radius: 3px;\n"
"        padding: 6px 8px;\n"
"        margin: 0;\n"
"        color: #fff;\n"
"        font-size: 14px;\n"
"    }\n"
"    \n"
"    QTabBar::tab:selected, QTabBar::tab:hover {\n"
"        background-color: #3e6071;\n"
"	 	 margin-left: 1px; \n"
"    }\n"
"    \n"
"    QTabBar::tab:!selected {\n"
"        margin-top: 2px; \n"
"		 margin-left: 1px; \n"
"    }\n"
"    \n"
"    QTabBar::tab:first {\n"
"        margin-left: 0; \n"
"    }")
        self.tab_widget.setIconSize(QSize(20, 20))
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_4 = QGridLayout(self.tab)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.devices_actions_layout = QHBoxLayout()
        self.devices_actions_layout.setObjectName(u"devices_actions_layout")
        self.refresh_devices_button = QPushButton(self.tab)
        self.refresh_devices_button.setObjectName(u"refresh_devices_button")
        self.refresh_devices_button.setStyleSheet(u"")

        self.devices_actions_layout.addWidget(self.refresh_devices_button)

        self.process_all_button = QPushButton(self.tab)
        self.process_all_button.setObjectName(u"process_all_button")
        self.process_all_button.setStyleSheet(u"")

        self.devices_actions_layout.addWidget(self.process_all_button)

        self.process_selected_button = QPushButton(self.tab)
        self.process_selected_button.setObjectName(u"process_selected_button")
        self.process_selected_button.setStyleSheet(u"")

        self.devices_actions_layout.addWidget(self.process_selected_button)

        self.hexview_selected_button = QPushButton(self.tab)
        self.hexview_selected_button.setObjectName(u"hexview_selected_button")
        self.hexview_selected_button.setStyleSheet(u"")

        self.devices_actions_layout.addWidget(self.hexview_selected_button)

        self.blink_selected_button = QPushButton(self.tab)
        self.blink_selected_button.setObjectName(u"blink_selected_button")
        self.blink_selected_button.setStyleSheet(u"")

        self.devices_actions_layout.addWidget(self.blink_selected_button)

        self.devices_actions_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.devices_actions_layout.addItem(self.devices_actions_spacer)

        self.filter_button = QPushButton(self.tab)
        self.filter_button.setObjectName(u"filter_button")
        self.filter_button.setStyleSheet(u"")

        self.devices_actions_layout.addWidget(self.filter_button)

        self.devices_search_field = QLineEdit(self.tab)
        self.devices_search_field.setObjectName(u"devices_search_field")
        self.devices_search_field.setClearButtonEnabled(True)

        self.devices_actions_layout.addWidget(self.devices_search_field)


        self.gridLayout_4.addLayout(self.devices_actions_layout, 0, 0, 1, 1)

        self.devices_layout = QGridLayout()
        self.devices_layout.setObjectName(u"devices_layout")
        self.devices_table = QTableWidget(self.tab)
        if (self.devices_table.columnCount() < 16):
            self.devices_table.setColumnCount(16)
        __qtablewidgetitem = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(9, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(10, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(11, __qtablewidgetitem11)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(12, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(13, __qtablewidgetitem13)
        __qtablewidgetitem14 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(14, __qtablewidgetitem14)
        __qtablewidgetitem15 = QTableWidgetItem()
        self.devices_table.setHorizontalHeaderItem(15, __qtablewidgetitem15)
        if (self.devices_table.rowCount() < 1):
            self.devices_table.setRowCount(1)
        __qtablewidgetitem16 = QTableWidgetItem()
        __qtablewidgetitem16.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 0, __qtablewidgetitem16)
        __qtablewidgetitem17 = QTableWidgetItem()
        __qtablewidgetitem17.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 1, __qtablewidgetitem17)
        __qtablewidgetitem18 = QTableWidgetItem()
        __qtablewidgetitem18.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 2, __qtablewidgetitem18)
        __qtablewidgetitem19 = QTableWidgetItem()
        __qtablewidgetitem19.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 3, __qtablewidgetitem19)
        __qtablewidgetitem20 = QTableWidgetItem()
        __qtablewidgetitem20.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 4, __qtablewidgetitem20)
        __qtablewidgetitem21 = QTableWidgetItem()
        __qtablewidgetitem21.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 5, __qtablewidgetitem21)
        __qtablewidgetitem22 = QTableWidgetItem()
        __qtablewidgetitem22.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 6, __qtablewidgetitem22)
        __qtablewidgetitem23 = QTableWidgetItem()
        __qtablewidgetitem23.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 7, __qtablewidgetitem23)
        __qtablewidgetitem24 = QTableWidgetItem()
        __qtablewidgetitem24.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 8, __qtablewidgetitem24)
        __qtablewidgetitem25 = QTableWidgetItem()
        __qtablewidgetitem25.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 9, __qtablewidgetitem25)
        __qtablewidgetitem26 = QTableWidgetItem()
        __qtablewidgetitem26.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 10, __qtablewidgetitem26)
        __qtablewidgetitem27 = QTableWidgetItem()
        __qtablewidgetitem27.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 11, __qtablewidgetitem27)
        __qtablewidgetitem28 = QTableWidgetItem()
        __qtablewidgetitem28.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 12, __qtablewidgetitem28)
        __qtablewidgetitem29 = QTableWidgetItem()
        __qtablewidgetitem29.setTextAlignment(Qt.AlignCenter);
        self.devices_table.setItem(0, 14, __qtablewidgetitem29)
        __qtablewidgetitem30 = QTableWidgetItem()
        self.devices_table.setItem(0, 15, __qtablewidgetitem30)
        self.devices_table.setObjectName(u"devices_table")
        self.devices_table.setFocusPolicy(Qt.NoFocus)
        self.devices_table.setStyleSheet(u"QTableWidget {\n"
"        background-color: #fff; /* White background */\n"
"        border: 1px solid #dee2e6; /* Light gray border */\n"
"        border-radius: 4px;\n"
"        color: #000;\n"
"    }\n"
"\n"
"    QTableWidget QHeaderView::section,\n"
"    QTableWidget::verticalHeader {\n"
"        background-color: #f8f9fa;\n"
"        color: #495057; \n"
"        border: none;\n"
"		border-bottom: 1px solid #d3d3d3;\n"
"        padding: 3px;\n"
"        font-size: 12px;\n"
"		font-weight: bold;\n"
"    }\n"
"\n"
"    QTableWidget::item:selected {\n"
"        background-color: #3d9970; \n"
"        color: #fff;\n"
"    }")
        self.devices_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.devices_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.devices_table.setTextElideMode(Qt.ElideNone)
        self.devices_table.setSortingEnabled(False)
        self.devices_table.horizontalHeader().setCascadingSectionResizes(True)
        self.devices_table.horizontalHeader().setProperty("showSortIndicator", False)
        self.devices_table.horizontalHeader().setStretchLastSection(True)
        self.devices_table.verticalHeader().setVisible(False)

        self.devices_layout.addWidget(self.devices_table, 0, 0, 1, 1)


        self.gridLayout_4.addLayout(self.devices_layout, 1, 0, 1, 1)

        icon = QIcon()
        icon.addFile(u"assets/images/hdd-tick.png", QSize(), QIcon.Normal, QIcon.Off)
        self.tab_widget.addTab(self.tab, icon, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_3 = QGridLayout(self.tab_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.devices_actions_layout_2 = QHBoxLayout()
        self.devices_actions_layout_2.setObjectName(u"devices_actions_layout_2")
        self.refresh_devices_button_2 = QPushButton(self.tab_2)
        self.refresh_devices_button_2.setObjectName(u"refresh_devices_button_2")

        self.devices_actions_layout_2.addWidget(self.refresh_devices_button_2)

        self.devices_actions_spacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.devices_actions_layout_2.addItem(self.devices_actions_spacer_2)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.devices_actions_layout_2.addItem(self.horizontalSpacer_3)

        self.devices_search_label_2 = QLabel(self.tab_2)
        self.devices_search_label_2.setObjectName(u"devices_search_label_2")

        self.devices_actions_layout_2.addWidget(self.devices_search_label_2)

        self.jobs_search_field = QLineEdit(self.tab_2)
        self.jobs_search_field.setObjectName(u"jobs_search_field")

        self.devices_actions_layout_2.addWidget(self.jobs_search_field)


        self.gridLayout_3.addLayout(self.devices_actions_layout_2, 0, 0, 1, 1)

        self.devices_layout_2 = QGridLayout()
        self.devices_layout_2.setObjectName(u"devices_layout_2")
        self.jobs_table = QTableWidget(self.tab_2)
        if (self.jobs_table.columnCount() < 9):
            self.jobs_table.setColumnCount(9)
        __qtablewidgetitem31 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(0, __qtablewidgetitem31)
        __qtablewidgetitem32 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(1, __qtablewidgetitem32)
        __qtablewidgetitem33 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(2, __qtablewidgetitem33)
        __qtablewidgetitem34 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(3, __qtablewidgetitem34)
        __qtablewidgetitem35 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(4, __qtablewidgetitem35)
        __qtablewidgetitem36 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(5, __qtablewidgetitem36)
        __qtablewidgetitem37 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(6, __qtablewidgetitem37)
        __qtablewidgetitem38 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(7, __qtablewidgetitem38)
        __qtablewidgetitem39 = QTableWidgetItem()
        self.jobs_table.setHorizontalHeaderItem(8, __qtablewidgetitem39)
        self.jobs_table.setObjectName(u"jobs_table")
        self.jobs_table.setFocusPolicy(Qt.NoFocus)
        self.jobs_table.setStyleSheet(u"QTableWidget {\n"
"        background-color: #fff; /* White background */\n"
"        border: 1px solid #dee2e6; /* Light gray border */\n"
"        border-radius: 4px;\n"
"        color: #000;\n"
"    }\n"
"\n"
"    QTableWidget QHeaderView::section,\n"
"    QTableWidget::verticalHeader {\n"
"        background-color: #f8f9fa;\n"
"        color: #495057; \n"
"        border: none;\n"
"		border-bottom: 1px solid #d3d3d3;\n"
"        padding: 3px;\n"
"        font-size: 12px;\n"
"		font-weight: bold;\n"
"    }\n"
"\n"
"    QTableWidget::item:selected {\n"
"        background-color: #3d9970; \n"
"        color: #fff;\n"
"    }")
        self.jobs_table.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.jobs_table.setRowCount(0)
        self.jobs_table.horizontalHeader().setCascadingSectionResizes(True)
        self.jobs_table.horizontalHeader().setProperty("showSortIndicator", True)
        self.jobs_table.horizontalHeader().setStretchLastSection(True)
        self.jobs_table.verticalHeader().setVisible(False)

        self.devices_layout_2.addWidget(self.jobs_table, 0, 0, 1, 1)


        self.gridLayout_3.addLayout(self.devices_layout_2, 1, 0, 1, 1)

        icon1 = QIcon()
        icon1.addFile(u"assets/images/jobs.png", QSize(), QIcon.Normal, QIcon.Off)
        self.tab_widget.addTab(self.tab_2, icon1, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.gridLayout_2 = QGridLayout(self.tab_3)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButton_2 = QPushButton(self.tab_3)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.horizontalLayout.addWidget(self.pushButton_2)

        self.line = QFrame(self.tab_3)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.VLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.pushButton_3 = QPushButton(self.tab_3)
        self.pushButton_3.setObjectName(u"pushButton_3")

        self.horizontalLayout.addWidget(self.pushButton_3)

        self.pushButton_4 = QPushButton(self.tab_3)
        self.pushButton_4.setObjectName(u"pushButton_4")

        self.horizontalLayout.addWidget(self.pushButton_4)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.label = QLabel(self.tab_3)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.lineEdit = QLineEdit(self.tab_3)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)


        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.listWidget = QListWidget(self.tab_3)
        self.listWidget.setObjectName(u"listWidget")

        self.gridLayout_2.addWidget(self.listWidget, 1, 0, 1, 1)

        icon2 = QIcon()
        icon2.addFile(u"assets/images/certificate.png", QSize(), QIcon.Normal, QIcon.Off)
        self.tab_widget.addTab(self.tab_3, icon2, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.gridLayout_7 = QGridLayout(self.tab_4)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_6 = QGridLayout()
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_6.addItem(self.horizontalSpacer_2, 0, 2, 1, 1)

        self.pushButton_8 = QPushButton(self.tab_4)
        self.pushButton_8.setObjectName(u"pushButton_8")

        self.gridLayout_6.addWidget(self.pushButton_8, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.tab_4)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout_6.addWidget(self.pushButton, 0, 3, 1, 1)

        self.lineEdit_2 = QLineEdit(self.tab_4)
        self.lineEdit_2.setObjectName(u"lineEdit_2")
        font = QFont()
        font.setFamilies([u"Sans"])
        font.setPointSize(11)
        font.setBold(False)
        font.setItalic(False)
        self.lineEdit_2.setFont(font)

        self.gridLayout_6.addWidget(self.lineEdit_2, 0, 1, 1, 1)

        self.pushButton_9 = QPushButton(self.tab_4)
        self.pushButton_9.setObjectName(u"pushButton_9")

        self.gridLayout_6.addWidget(self.pushButton_9, 0, 4, 1, 1)


        self.gridLayout_7.addLayout(self.gridLayout_6, 0, 0, 1, 1)

        self.textBrowser = QTextBrowser(self.tab_4)
        self.textBrowser.setObjectName(u"textBrowser")

        self.gridLayout_7.addWidget(self.textBrowser, 1, 0, 1, 1)

        icon3 = QIcon()
        icon3.addFile(u"assets/images/command.png", QSize(), QIcon.Normal, QIcon.Off)
        self.tab_widget.addTab(self.tab_4, icon3, "")

        self.gridLayout.addWidget(self.tab_widget, 1, 0, 1, 1)

        CDIGradingTool.setCentralWidget(self.erase_it_central_widget)

        self.retranslateUi(CDIGradingTool)

        self.tab_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(CDIGradingTool)
    # setupUi

    def retranslateUi(self, CDIGradingTool):
        CDIGradingTool.setWindowTitle(QCoreApplication.translate("CDIGradingTool", u"Circular Drive Initiative | Grading Tool", None))
        self.actionExit.setText(QCoreApplication.translate("CDIGradingTool", u"Exit", None))
        self.logo_lbl.setText("")
        self.devices_count.setText(QCoreApplication.translate("CDIGradingTool", u"Devices: 0", None))
        self.jobs_count.setText(QCoreApplication.translate("CDIGradingTool", u"Jobs: 0", None))
        self.power_button.setText(QCoreApplication.translate("CDIGradingTool", u"Exit", None))
        self.settings_button.setText(QCoreApplication.translate("CDIGradingTool", u"Settings", None))
        self.manual_button.setText(QCoreApplication.translate("CDIGradingTool", u"Manual", None))
        self.about_button.setText(QCoreApplication.translate("CDIGradingTool", u"About", None))
        self.time_label.setText("")
        self.refresh_devices_button.setText(QCoreApplication.translate("CDIGradingTool", u"Refresh", None))
        self.process_all_button.setText(QCoreApplication.translate("CDIGradingTool", u"Grade All", None))
        self.process_selected_button.setText(QCoreApplication.translate("CDIGradingTool", u"Grade Selected", None))
        self.hexview_selected_button.setText(QCoreApplication.translate("CDIGradingTool", u"Hex", None))
        self.blink_selected_button.setText(QCoreApplication.translate("CDIGradingTool", u"Blink", None))
        self.filter_button.setText(QCoreApplication.translate("CDIGradingTool", u"Filter", None))
        self.devices_search_field.setPlaceholderText(QCoreApplication.translate("CDIGradingTool", u"Search for Devices...", None))
        ___qtablewidgetitem = self.devices_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("CDIGradingTool", u"#", None));
        ___qtablewidgetitem1 = self.devices_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("CDIGradingTool", u"DUT", None));
        ___qtablewidgetitem2 = self.devices_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("CDIGradingTool", u"STATE", None));
        ___qtablewidgetitem3 = self.devices_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("CDIGradingTool", u"TYPE", None));
        ___qtablewidgetitem4 = self.devices_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("CDIGradingTool", u"TRAN", None));
        ___qtablewidgetitem5 = self.devices_table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("CDIGradingTool", u"VENDOR", None));
        ___qtablewidgetitem6 = self.devices_table.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("CDIGradingTool", u"MODEL NUMBER", None));
        ___qtablewidgetitem7 = self.devices_table.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("CDIGradingTool", u"SERIAL NUMBER", None));
        ___qtablewidgetitem8 = self.devices_table.horizontalHeaderItem(8)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("CDIGradingTool", u"F/W", None));
        ___qtablewidgetitem9 = self.devices_table.horizontalHeaderItem(9)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("CDIGradingTool", u"GB", None));
        ___qtablewidgetitem10 = self.devices_table.horizontalHeaderItem(10)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("CDIGradingTool", u"B/S", None));
        ___qtablewidgetitem11 = self.devices_table.horizontalHeaderItem(11)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("CDIGradingTool", u"PoH", None));
        ___qtablewidgetitem12 = self.devices_table.horizontalHeaderItem(12)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("CDIGradingTool", u"SMART", None));
        ___qtablewidgetitem13 = self.devices_table.horizontalHeaderItem(13)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("CDIGradingTool", u"GRADE", None));
        ___qtablewidgetitem14 = self.devices_table.horizontalHeaderItem(14)
        ___qtablewidgetitem14.setText(QCoreApplication.translate("CDIGradingTool", u"HEALTH", None));
        ___qtablewidgetitem15 = self.devices_table.horizontalHeaderItem(15)
        ___qtablewidgetitem15.setText(QCoreApplication.translate("CDIGradingTool", u"REMARKS", None));

        __sortingEnabled = self.devices_table.isSortingEnabled()
        self.devices_table.setSortingEnabled(False)
        ___qtablewidgetitem16 = self.devices_table.item(0, 0)
        ___qtablewidgetitem16.setText(QCoreApplication.translate("CDIGradingTool", u"1", None));
        ___qtablewidgetitem17 = self.devices_table.item(0, 1)
        ___qtablewidgetitem17.setText(QCoreApplication.translate("CDIGradingTool", u"/dev/sda", None));
        ___qtablewidgetitem18 = self.devices_table.item(0, 2)
        ___qtablewidgetitem18.setText(QCoreApplication.translate("CDIGradingTool", u"Ready", None));
        ___qtablewidgetitem19 = self.devices_table.item(0, 3)
        ___qtablewidgetitem19.setText(QCoreApplication.translate("CDIGradingTool", u"HDD", None));
        ___qtablewidgetitem20 = self.devices_table.item(0, 4)
        ___qtablewidgetitem20.setText(QCoreApplication.translate("CDIGradingTool", u"ATA", None));
        ___qtablewidgetitem21 = self.devices_table.item(0, 5)
        ___qtablewidgetitem21.setText(QCoreApplication.translate("CDIGradingTool", u"SEAGATE", None));
        ___qtablewidgetitem22 = self.devices_table.item(0, 6)
        ___qtablewidgetitem22.setText(QCoreApplication.translate("CDIGradingTool", u"ST1000NM0095-2DC10C", None));
        ___qtablewidgetitem23 = self.devices_table.item(0, 7)
        ___qtablewidgetitem23.setText(QCoreApplication.translate("CDIGradingTool", u"ZBS0HSJW", None));
        ___qtablewidgetitem24 = self.devices_table.item(0, 8)
        ___qtablewidgetitem24.setText(QCoreApplication.translate("CDIGradingTool", u"DB34", None));
        ___qtablewidgetitem25 = self.devices_table.item(0, 9)
        ___qtablewidgetitem25.setText(QCoreApplication.translate("CDIGradingTool", u"1000 GB", None));
        ___qtablewidgetitem26 = self.devices_table.item(0, 10)
        ___qtablewidgetitem26.setText(QCoreApplication.translate("CDIGradingTool", u"512 BPS", None));
        ___qtablewidgetitem27 = self.devices_table.item(0, 11)
        ___qtablewidgetitem27.setText(QCoreApplication.translate("CDIGradingTool", u"1024768", None));
        ___qtablewidgetitem28 = self.devices_table.item(0, 12)
        ___qtablewidgetitem28.setText(QCoreApplication.translate("CDIGradingTool", u"PASS", None));
        ___qtablewidgetitem29 = self.devices_table.item(0, 14)
        ___qtablewidgetitem29.setText(QCoreApplication.translate("CDIGradingTool", u"OK", None));
        ___qtablewidgetitem30 = self.devices_table.item(0, 15)
        ___qtablewidgetitem30.setText(QCoreApplication.translate("CDIGradingTool", u"Sanitize supported, Can IEEE Purge, Can NIST Purge", None));
        self.devices_table.setSortingEnabled(__sortingEnabled)

        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab), QCoreApplication.translate("CDIGradingTool", u"DEVICES", None))
        self.refresh_devices_button_2.setText(QCoreApplication.translate("CDIGradingTool", u"Clear Completed", None))
        self.devices_search_label_2.setText(QCoreApplication.translate("CDIGradingTool", u"Search Jobs", None))
        ___qtablewidgetitem31 = self.jobs_table.horizontalHeaderItem(0)
        ___qtablewidgetitem31.setText(QCoreApplication.translate("CDIGradingTool", u"DUT", None));
        ___qtablewidgetitem32 = self.jobs_table.horizontalHeaderItem(1)
        ___qtablewidgetitem32.setText(QCoreApplication.translate("CDIGradingTool", u"MODEL NUMBER", None));
        ___qtablewidgetitem33 = self.jobs_table.horizontalHeaderItem(2)
        ___qtablewidgetitem33.setText(QCoreApplication.translate("CDIGradingTool", u"SERIAL NUMBER", None));
        ___qtablewidgetitem34 = self.jobs_table.horizontalHeaderItem(3)
        ___qtablewidgetitem34.setText(QCoreApplication.translate("CDIGradingTool", u"GB", None));
        ___qtablewidgetitem35 = self.jobs_table.horizontalHeaderItem(4)
        ___qtablewidgetitem35.setText(QCoreApplication.translate("CDIGradingTool", u"STATE", None));
        ___qtablewidgetitem36 = self.jobs_table.horizontalHeaderItem(5)
        ___qtablewidgetitem36.setText(QCoreApplication.translate("CDIGradingTool", u"PROGRESS", None));
        ___qtablewidgetitem37 = self.jobs_table.horizontalHeaderItem(6)
        ___qtablewidgetitem37.setText(QCoreApplication.translate("CDIGradingTool", u"RESULT", None));
        ___qtablewidgetitem38 = self.jobs_table.horizontalHeaderItem(7)
        ___qtablewidgetitem38.setText(QCoreApplication.translate("CDIGradingTool", u"GRADE", None));
        ___qtablewidgetitem39 = self.jobs_table.horizontalHeaderItem(8)
        ___qtablewidgetitem39.setText(QCoreApplication.translate("CDIGradingTool", u"REMARKS", None));
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_2), QCoreApplication.translate("CDIGradingTool", u"JOBS", None))
        self.pushButton_2.setText(QCoreApplication.translate("CDIGradingTool", u"Customize", None))
        self.pushButton_3.setText(QCoreApplication.translate("CDIGradingTool", u"Open", None))
        self.pushButton_4.setText(QCoreApplication.translate("CDIGradingTool", u"Export", None))
        self.label.setText(QCoreApplication.translate("CDIGradingTool", u"Search", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_3), QCoreApplication.translate("CDIGradingTool", u"REPORTS", None))
        self.pushButton_8.setText(QCoreApplication.translate("CDIGradingTool", u"Run Command", None))
        self.pushButton.setText(QCoreApplication.translate("CDIGradingTool", u"Clear Console", None))
        self.pushButton_9.setText(QCoreApplication.translate("CDIGradingTool", u"Export Console", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_4), QCoreApplication.translate("CDIGradingTool", u"CONSOLE", None))
    # retranslateUi

