from threading import Thread, Event
from PyQt5.QtWidgets import *
from Ui_untitled import Ui_MainWindow
from PyQt5.QtCore import Qt, QThread, QCoreApplication
import sys, os
from ctypes import *
from crc import *
from mySinal import *
import Time_get


class CanWindow(QMainWindow):
    def __init__(self,ui_main_window):
        super().__init__()
        self.ui = ui_main_window
        self.OPEN_CAN_DEVICE = self.ui.OPEN_CAN_DEVICE
        self.CHOOSE_FILE_OF_CAN = self.ui.CHOOSE_FILE_OF_CAN
        self.CAN_FILE_SHOWED = self.ui.CAN_FILE_SHOWED
        self.CHOOSE_BOARD_CAN = self.ui.CHOOSE_BOARD_CAN
        self.CAN_BAND = self.ui.CAN_BAND
        self.START_CAN_IAP = self.ui.START_CAN_IAP
        self.CAN_DEVIEC_PASS = self.ui.CAN_DEVIEC_PASS
        self.CAN_FRAME_SHOWED = self.ui.CAN_FRAME_SHOWED
        self.OPEN_CAN_DEVICE.clicked.connect(self.open_device)


    def open_device(self):
        print("open_device")
      