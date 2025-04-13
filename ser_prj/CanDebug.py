from threading import Thread, Event
from PyQt5.QtWidgets import *
from Ui_untitled import Ui_MainWindow
from PyQt5.QtCore import Qt, QThread, QCoreApplication
import sys, os
from ctypes import *
from crc import *
from mySinal import *
import Time_get

canDLL = windll.LoadLibrary('./ControlCAN.dll')
VCI_USBCAN2 = 4

class VCI_INIT_CONFIG(Structure):  
    _fields_ = [("AccCode", c_uint),
                ("AccMask", c_uint),
                ("Reserved", c_uint),
                ("Filter", c_ubyte),
                ("Timing0", c_ubyte),
                ("Timing1", c_ubyte),
                ("Mode", c_ubyte)
                ]  
class VCI_CAN_OBJ(Structure):  
    _fields_ = [("ID", c_uint),
                ("TimeStamp", c_uint),
                ("TimeFlag", c_ubyte),
                ("SendType", c_ubyte),
                ("RemoteFlag", c_ubyte),
                ("ExternFlag", c_ubyte),
                ("DataLen", c_ubyte),
                ("Data", c_ubyte*8),
                ("Reserved", c_ubyte*3)
                ] 


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
        global VCI_USBCAN2
        ret = canDLL.VCI_OpenDevice(VCI_USBCAN2, 0, 0)
        print("open_device")
      