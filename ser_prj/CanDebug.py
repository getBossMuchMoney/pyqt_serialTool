from threading import Thread, Event
from PyQt5.QtWidgets import *
from Ui_untitled import Ui_MainWindow
from PyQt5.QtCore import Qt, QThread, QCoreApplication
import sys, os
import ctypes
from ctypes import *
from crc import *
from mySinal import *
import Time_get
import time

canDLL = windll.LoadLibrary('./ControlCAN.dll') 
VCI_USBCAN2 = 4


class ID_BIT(Structure):
    _fields_ = [("state_code", c_uint, 2),
                ("func_code", c_uint, 7),
                ("dev_id", c_uint, 6),
                ("scr_id", c_uint, 6),
                ("index", c_uint, 8),
               ]
    
class ID_VALUE(Union):
    _fields_ = [("bit",ID_BIT),
                ("id_frame", c_uint),
               ]



class VCI_BOARD_INFO(Structure):  
    _fields_ = [("hw_Version", c_ushort),
                ("fw_Version", c_ushort),
                ("dr_Version", c_ushort),
                ("in_Version", c_ushort),
                ("irq_Num", c_ushort),
                ("can_Num", c_ubyte),
                ("str_Serial_Num", c_ubyte * 20),
                ("str_hw_Type", c_ubyte * 40),
                ("Reserved", c_ubyte * 4),
                ]

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
    

class VCI_CAN_OBJ_ARRAY(Structure):
    _fields_ = [('SIZE', ctypes.c_uint16), ('STRUCT_ARRAY', ctypes.POINTER(VCI_CAN_OBJ))]

    def __init__(self,num_of_structs):
                                                                 #这个括号不能少
        self.STRUCT_ARRAY = ctypes.cast((VCI_CAN_OBJ * num_of_structs)(),ctypes.POINTER(VCI_CAN_OBJ))#结构体数组
        self.SIZE = num_of_structs#结构体长度
        self.ADDR = self.STRUCT_ARRAY[0]#结构体数组地址  byref()转c地址
    
rx_vci_can_obj = VCI_CAN_OBJ_ARRAY(2500)#结构体数组    
rxlen = 0

DeviceInfoArray = (VCI_BOARD_INFO * 5)()

# 定义函数签名
canDLL.VCI_FindUsbDevice2.argtypes = [POINTER(VCI_BOARD_INFO)]
canDLL.VCI_FindUsbDevice2.restype = c_uint
canDLL.VCI_UsbDeviceReset.argtypes = [c_uint,c_uint,c_uint]
canDLL.VCI_UsbDeviceReset.restype = c_int
canDLL.VCI_CloseDevice.argtypes = [c_uint,c_uint]
canDLL.VCI_CloseDevice.restype = c_int
canDLL.VCI_InitCAN.argtypes = [c_uint,c_uint,c_uint,POINTER(VCI_INIT_CONFIG)]
canDLL.VCI_InitCAN.restype = c_int
canDLL.VCI_StartCAN.argtypes = [c_uint,c_uint,c_uint]
canDLL.VCI_StartCAN.restype = c_int
canDLL.VCI_Transmit.argtypes = [c_uint,c_uint,c_uint,POINTER(VCI_CAN_OBJ),c_uint]
canDLL.VCI_Transmit.restype = c_int
canDLL.VCI_Receive.argtypes = [c_uint,c_uint,c_uint,POINTER(VCI_CAN_OBJ),c_uint,c_uint]
canDLL.VCI_Receive.restype = c_int

class CanWindow(QWidget):
    def __init__(self,ui_main_window):
        self.CanDeviceIndex = 0
        self.devicePass_index = 0
        self.CanDeviceNum = 0
        self.DeviceIdList = list()
        self.DeviceOpenSta = 0
        DevicePass = ["CAN1", "CAN2"]
        self.DeviceTimming = [[0x03,0x1C],[0x01,0x1C],[0x00,0x1C],[0x00,0x14]]
        Band = ["125kbit", "250kbit", "500kbit", "1Mbit"]
        DeviceIdList = [
            "主机",
            "从机1",
            "从机2",
            "从机3",
            "从机4",
            "从机5",
            "从机6",
            "从机7",
            "从机8",
            "从机9",
            "从机10",
        ]
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
        self.CAN_DEVICE_INDEX = self.ui.CAN_DEVICE_INDEX
        self.SCAN_USBDEVICE = self.ui.SCAN_USBDEVICE
        self.BOOT_CMD = self.ui.BOOT_CMD

        self.OPEN_CAN_DEVICE.clicked.connect(self.Open_Devive_Click)
        self.SCAN_USBDEVICE.clicked.connect(self.CheckCanDevice)
        self.BOOT_CMD.clicked.connect(self.bootSend)

        self.ui_update = ui_show()
        self.ui_update.update_signal.connect(self.ui_show_refresh)

        self.CanCtrlThread = Thread(target=self.ctrl_CanDevice)
        self.rcvDataThread = Thread(target=self.rcv_Data)

        self.CheckCanDevice()


        # 加载通道选项
        for i in range(0, len(DevicePass)):
            self.CAN_DEVIEC_PASS.addItem(DevicePass[i])

        # 加载波特率选项
        for i in range(0, len(Band)):
            self.CAN_BAND.addItem(Band[i])

        # 加载选择设备选项
        for i in range(0, len(DeviceIdList)):
            self.CHOOSE_BOARD_CAN.addItem(DeviceIdList[i])

    def CheckCanDevice(self):
        global DeviceInfoArray          
        Num = canDLL.VCI_FindUsbDevice2(DeviceInfoArray)                     
        if self.CanDeviceNum !=  Num:
            self.CanDeviceNum = Num
            self.CAN_DEVICE_INDEX.clear()                  
            for i in range(Num):
                self.CAN_DEVICE_INDEX.addItem(str(i))    
    
    def Can_Transmit(self,devid,data:list):
        ubyte_array = c_ubyte*8
        a = ubyte_array(0,0,0,0,0,0,0,0)
        for i in range(8):
            a[i] = data[i]
        ubyte_3array = c_ubyte*3
        b = ubyte_3array(0, 0 , 0)
        vci_can_obj = VCI_CAN_OBJ(devid, 0, 0, 0, 0, 1, 8, a, b)#扩展帧正常发送
        timeStr = Time_get.get_strTime()
        ret = canDLL.VCI_Transmit(VCI_USBCAN2, self.CanDeviceIndex, self.devicePass_index, byref(vci_can_obj), 1)
        if ret == 1:
            idstr = " id:"+str(hex(devid)) + " "
            lenstr = "len:" + str(hex(8)) + " data:"
            datastr = ' '.join(f'{byte:02X}' for byte in a)
            show_str = "[" + timeStr + "]" + "发→◇" + idstr + lenstr + datastr
            self.ui_update.update(show_str)
            print('CAN发送成功\r\n')
        if ret != 1:
            print('CAN发送失败\r\n')

    def bootSend(self):
        id = ID_VALUE()
        data = [0] * 8
        id.bit.state_code = 0
        id.bit.func_code = 0x09
        id.bit.dev_id = 0x00
        id.bit.scr_id = 0x3f
        id.bit.index = 0
        self.Can_Transmit(id.id_frame, data)



    def rcv_Data(self):
        global rx_vci_can_obj,rxlen
        while True:
            if self.DeviceOpenSta == 0:
                break
            else:
                ret = canDLL.VCI_Receive(VCI_USBCAN2, self.CanDeviceIndex, self.devicePass_index, byref(rx_vci_can_obj.ADDR), 2500, 0)
                if ret > 0:#接收到数据
                    timeStr = Time_get.get_strTime()
                    for i in range(0,ret):
                        idstr = " id:"+str(hex(rx_vci_can_obj.STRUCT_ARRAY[i].ID)) + " "
                        lenstr = "len:" + str(hex(rx_vci_can_obj.STRUCT_ARRAY[i].DataLen)) + " data:"
                        datastr = ' '.join(f'{byte:02X}' for byte in rx_vci_can_obj.STRUCT_ARRAY[i].Data)
                        show_str = "[" + timeStr + "]" + "收←◆" + idstr + lenstr + datastr
                        self.ui_update.update(show_str)
                # rxlen += ret
                # print('CAN通道接收数据总数：' + str(rxlen))
            time.sleep(0.001)
        


    def ui_show_refresh (self, data):
        self.CAN_FRAME_SHOWED.append(data)

    def Open_Devive_Click(self):
        if not self.CanCtrlThread.is_alive():
            self.OPEN_CAN_DEVICE.setEnabled(False)
            self.CanCtrlThread = Thread(target=self.ctrl_CanDevice)
            self.CanCtrlThread.start()

    def ctrl_CanDevice(self):
        global VCI_USBCAN2
        if self.OPEN_CAN_DEVICE.text() == "打开CAN分析仪" and self.CAN_DEVICE_INDEX.count() > 0:
            self.SCAN_USBDEVICE.setEnabled(False)
            self.CanDeviceIndexx = self.CAN_DEVICE_INDEX.currentIndex()        
            ret = canDLL.VCI_UsbDeviceReset(VCI_USBCAN2, self.CanDeviceIndexx,0)       
            ret = canDLL.VCI_OpenDevice(VCI_USBCAN2, self.CanDeviceIndexx, 0)

            if ret == 0:
                print("打开分析仪错误")
                ret = canDLL.VCI_CloseDevice(VCI_USBCAN2, self.CanDeviceIndexx)
                self.SCAN_USBDEVICE.setEnabled(True)
            elif ret == 1:
                band_index = self.CAN_BAND.currentIndex()
                band_timming =  self.DeviceTimming[band_index]
                vci_initconfig = VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 3, band_timming[0], band_timming[1], 0)#正常模式,只接收扩展帧
                self.devicePass_index = self.CAN_DEVIEC_PASS.currentIndex()
                ret = canDLL.VCI_InitCAN(VCI_USBCAN2, self.CanDeviceIndexx, self.devicePass_index, ctypes.byref(vci_initconfig))
                if ret == 0:
                    print("分析仪初始化错误")
                    ret = canDLL.VCI_CloseDevice(VCI_USBCAN2, self.CanDeviceIndexx)
                    self.SCAN_USBDEVICE.setEnabled(True)
                elif ret == 1:
                    ret = canDLL.VCI_StartCAN(VCI_USBCAN2, self.CanDeviceIndexx, self.devicePass_index)
                    if ret == 0:
                        print("启动CAN通道失败")
                        ret = canDLL.VCI_CloseDevice(VCI_USBCAN2, self.CanDeviceIndexx)
                        self.SCAN_USBDEVICE.setEnabled(True)
                    elif ret == 1:
                        print("CAN分析仪初始化成功")
                        self.OPEN_CAN_DEVICE.setText("关闭CAN分析仪")
                        self.rcvDataThread = Thread(target=self.rcv_Data)
                        self.rcvDataThread.start()
                        self.DeviceOpenSta = 1
                    else:
                        print("CAN分析仪掉线")
                        self.SCAN_USBDEVICE.setEnabled(True)

                else:
                    print("CAN分析仪掉线")
                    self.SCAN_USBDEVICE.setEnabled(True)
           
            else:
                print("CAN分析仪掉线")
                self.SCAN_USBDEVICE.setEnabled(True)

        else:
            self.DeviceOpenSta = 0          
            self.rcvDataThread.join()        
            self.CanDeviceIndexx = self.CAN_DEVICE_INDEX.currentIndex()
            ret = canDLL.VCI_CloseDevice(VCI_USBCAN2, self.CanDeviceIndexx)
            self.SCAN_USBDEVICE.setEnabled(True)
            self.OPEN_CAN_DEVICE.setText("打开CAN分析仪")
            print("关闭CAN分析仪")

        self.OPEN_CAN_DEVICE.setEnabled(True)
        
      