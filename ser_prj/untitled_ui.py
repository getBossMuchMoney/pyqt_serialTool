# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'e:\gitHub_prj\pyqt_serialTool\ser_prj\untitled.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1160, 712)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.Data_Display = QtWidgets.QTextEdit(self.centralwidget)
        self.Data_Display.setGeometry(QtCore.QRect(10, 20, 819, 491))
        self.Data_Display.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.Data_Display.setPlaceholderText("")
        self.Data_Display.setObjectName("Data_Display")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(10, 520, 69, 19))
        self.label_2.setObjectName("label_2")
        self.Send_Data = QtWidgets.QPushButton(self.centralwidget)
        self.Send_Data.setGeometry(QtCore.QRect(10, 630, 93, 28))
        self.Send_Data.setObjectName("Send_Data")
        self.Send_Data_Display = QtWidgets.QTextEdit(self.centralwidget)
        self.Send_Data_Display.setGeometry(QtCore.QRect(10, 548, 819, 71))
        self.Send_Data_Display.setObjectName("Send_Data_Display")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(10, 0, 69, 19))
        self.label.setObjectName("label")
        self.Com_Band = QtWidgets.QComboBox(self.centralwidget)
        self.Com_Band.setGeometry(QtCore.QRect(890, 70, 129, 21))
        self.Com_Band.setObjectName("Com_Band")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(840, 70, 49, 19))
        self.label_4.setObjectName("label_4")
        self.Com_Port = QtWidgets.QComboBox(self.centralwidget)
        self.Com_Port.setGeometry(QtCore.QRect(890, 30, 129, 21))
        self.Com_Port.setObjectName("Com_Port")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(840, 30, 49, 19))
        self.label_3.setObjectName("label_3")
        self.Open_Com = QtWidgets.QPushButton(self.centralwidget)
        self.Open_Com.setGeometry(QtCore.QRect(840, 170, 93, 28))
        self.Open_Com.setObjectName("Open_Com")
        self.ClearRecShow = QtWidgets.QPushButton(self.centralwidget)
        self.ClearRecShow.setGeometry(QtCore.QRect(650, 520, 75, 23))
        self.ClearRecShow.setObjectName("ClearRecShow")
        self.recHexShow = QtWidgets.QCheckBox(self.centralwidget)
        self.recHexShow.setGeometry(QtCore.QRect(840, 500, 81, 16))
        self.recHexShow.setChecked(True)
        self.recHexShow.setTristate(False)
        self.recHexShow.setObjectName("recHexShow")
        self.sendHex = QtWidgets.QCheckBox(self.centralwidget)
        self.sendHex.setGeometry(QtCore.QRect(840, 550, 81, 16))
        self.sendHex.setChecked(False)
        self.sendHex.setObjectName("sendHex")
        self.ClearSendShow = QtWidgets.QPushButton(self.centralwidget)
        self.ClearSendShow.setGeometry(QtCore.QRect(750, 520, 75, 23))
        self.ClearSendShow.setObjectName("ClearSendShow")
        self.ComReflash = QtWidgets.QPushButton(self.centralwidget)
        self.ComReflash.setGeometry(QtCore.QRect(960, 170, 101, 28))
        self.ComReflash.setObjectName("ComReflash")
        self.send_freq = QtWidgets.QLineEdit(self.centralwidget)
        self.send_freq.setGeometry(QtCore.QRect(920, 580, 71, 16))
        self.send_freq.setEchoMode(QtWidgets.QLineEdit.Normal)
        self.send_freq.setObjectName("send_freq")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(1000, 580, 54, 12))
        self.label_5.setObjectName("label_5")
        self.send_auto = QtWidgets.QCheckBox(self.centralwidget)
        self.send_auto.setGeometry(QtCore.QRect(840, 580, 71, 16))
        self.send_auto.setObjectName("send_auto")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1160, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.Send_Data.clicked.connect(MainWindow.send_data_click) # type: ignore
        self.Open_Com.clicked.connect(MainWindow.open_com_click) # type: ignore
        self.ClearRecShow.clicked.connect(self.Data_Display.clear) # type: ignore
        self.Data_Display.textChanged.connect(MainWindow.drag_scroll) # type: ignore
        self.ClearSendShow.clicked.connect(self.Send_Data_Display.clear) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "串口助手beta版"))
        self.label_2.setText(_translate("MainWindow", "发送窗口"))
        self.Send_Data.setText(_translate("MainWindow", "发送数据"))
        self.label.setText(_translate("MainWindow", "数据窗口"))
        self.label_4.setText(_translate("MainWindow", "波特率"))
        self.label_3.setText(_translate("MainWindow", "串口号"))
        self.Open_Com.setText(_translate("MainWindow", "打开串口"))
        self.ClearRecShow.setText(_translate("MainWindow", "清接收区"))
        self.recHexShow.setText(_translate("MainWindow", "Hex显示"))
        self.sendHex.setText(_translate("MainWindow", "Hex发送"))
        self.ClearSendShow.setText(_translate("MainWindow", "清发送区"))
        self.ComReflash.setText(_translate("MainWindow", "刷新串口列表"))
        self.label_5.setText(_translate("MainWindow", "ms/次"))
        self.send_auto.setText(_translate("MainWindow", "定时发送"))
