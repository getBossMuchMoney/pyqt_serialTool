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
from multiprocessing import*
from enum import IntEnum

canDLL = windll.LoadLibrary('./ControlCAN.dll') 
VCI_USBCAN2 = 4
iapRXdata = Queue()

class can_err_code(IntEnum):
    DATA_LEN_OVERRANGE_ERR = 5
    FILE_NOT_EXIST_ERR = 6
    FILE_SIZE_OVERRANGE = 7
    FILE_READ_ERR = 8
    FILE_SEND_ERR = 9
    NO_DEVICE_FOUND_ERR = 10
    DEVICE_RESPOND_TIMEOUT_ERR = 11
    DEVICE_FLASH_ERASE_ERR = 12
    DEVICE_FLASH_WRITE_ERR = 13
    DEVICE_FLASH_CHECK_ERR = 14
    DEVICE_FLASH_CHECK_SUCCESS = 15
    DEVICE_NOT_CORRECT_RESPOND_ERR = 16



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
        self.deviceID = 0
        self.errCode = 0
        self.index = ctypes.c_uint8(0)
        self.crc16 = 0
        self.sendProcessCount = 0
        self.file_size = 0
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
        self.CLEAR_DATA = self.ui.CLEAR_DATA

        self.OPEN_CAN_DEVICE.clicked.connect(self.Open_Devive_Click)
        self.SCAN_USBDEVICE.clicked.connect(self.CheckCanDevice)
        self.BOOT_CMD.clicked.connect(self.bootSend)
        self.CHOOSE_FILE_OF_CAN.clicked.connect(self.open_file)
        self.START_CAN_IAP.clicked.connect(self.send_file)
        self.CLEAR_DATA.clicked.connect(self.clear_data)

        self.ui_update = ui_show()
        self.ui_update.update_signal.connect(self.ui_show_refresh)

        self.CanCtrlThread = Thread(target=self.ctrl_CanDevice)
        self.rcvDataThread = Thread(target=self.rcv_Data)
        self.Updatathread = Thread(target=self.Updateprocess)

        self.canErr = number_check()
        self.canErr.update_signal.connect(self.err_code_warning)

        self.send_process_show_start = number_check()
        self.send_process_show_start.update_signal.connect(self.send_process_window)

        self.send_process_count_update = number_check()
        self.send_process_count_update.update_signal.connect(
            self.send_process_count_reflash
        )

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

    
    def open_file(self):
        if not self.Updatathread.is_alive():
            self.fname = QFileDialog.getOpenFileName(
                self, "打开文件", "/",filter='*.bin'
            )  # filter='*.txt',此参数指定文件类型

            if self.fname[0]:
                self.file_size = os.path.getsize(self.fname[0])
                print("文件大小", self.file_size)
                if self.file_size > 1024 * 1024 * 1024 or self.file_size < 2048:
                    self.errCode = can_err_code.FILE_SIZE_OVERRANGE
                    self.canErr.update(self.errCode)
                    return
                try:
                    self.openFile = open(self.fname[0], "rb")
                    self.CAN_FILE_SHOWED.clear()
                    self.CAN_FILE_SHOWED.setText(self.fname[0])
                except:
                    return
            else:
                self.file_size = 0  

    def send_file(self):
        if not self.Updatathread.is_alive():
            self.deviceID = self.CHOOSE_BOARD_CAN.currentIndex() + 1
            if self.file_size > 0:
                print(self.CAN_FILE_SHOWED.text())
                if self.CAN_FILE_SHOWED.text() == self.fname[0]:
                    self.Updatathread = Thread(target=self.Updateprocess)
                    self.Updatathread.start()
                    self.START_CAN_IAP.setEnabled(False)

                else:
                    try:
                        self.openFile = open(self.CAN_FILE_SHOWED.text(), "rb")
                        self.file_size = os.path.getsize(self.CAN_FILE_SHOWED.text())
                        self.Updatathread = Thread(target=self.Updateprocess)
                        self.Updatathread.start()
                        self.START_CAN_IAP.setEnabled(False)

                    except:
                        self.errCode = can_err_code.FILE_NOT_EXIST_ERR
                        self.canErr.update(self.errCode)

            else:
                try:
                    self.openFile = open(self.CAN_FILE_SHOWED.text(), "rb")
                    self.file_size = os.path.getsize(self.CAN_FILE_SHOWED.text())
                    self.Updatathread = Thread(target=self.Updateprocess)
                    self.Updatathread.start()
                    self.START_CAN_IAP.setEnabled(False)

                except:
                    self.errCode = can_err_code.FILE_NOT_EXIST_ERR
                    self.canErr.update(self.errCode)


    def Updateprocess(self):    
        self.txbuff = list()
        filebuff = list(self.openFile.read(self.file_size))
        k = self.file_size % 16
        if k != 0:
            for i in range(16 - k):
                filebuff.append(0xFF)
                self.file_size += 1
        rxid = ID_VALUE()
        group_index = 0
        list_index = 0
        list_index1 = 0
        self.index.value = 0
        rxbuff = list()
        self.crc16 = calculate_crc16(filebuff)
        data_group = self.file_size // 2048
        left_data_size = self.file_size % 2048

        if left_data_size > 0:
            self.sendProcessCount = data_group + 1
        else:
            self.sendProcessCount = data_group

        print(self.crc16, data_group, left_data_size)
        self.send_process_show_start.update(1)

        for i in range(3):
            try:
                self.bootSend()
                rxbuff = list(iapRXdata.get(timeout=1))
                break
            except:
                if i == 2:
                    self.file_size = 0
                    self.errCode = can_err_code.NO_DEVICE_FOUND_ERR
                    self.canErr.update(self.errCode)
                    self.START_CAN_IAP.setEnabled(True)
                    self.send_process_show_start.update(0)
                    self.openFile.close()
                    return
                else:
                    continue

        for i in range(3):
            try:
                self.Iap_Req()
                rxbuff = list(iapRXdata.get(timeout=1))
                break
            except:
                if i == 2:
                    self.file_size = 0
                    self.errCode = can_err_code.NO_DEVICE_FOUND_ERR
                    self.canErr.update(self.errCode)
                    self.START_CAN_IAP.setEnabled(True)
                    self.send_process_show_start.update(0)
                    self.openFile.close()
                    return
                else:
                    continue
        self.file_size = 0
        rxid.id_frame = int(rxbuff[0])
        if rxid.bit.state_code == 0:
            for i in range(3):
                try:
                    self.Iap_Erase()
                    rxbuff = list(iapRXdata.get(timeout=1))
                    break
                except:
                    if i == 2:
                        self.errCode = can_err_code.NO_DEVICE_FOUND_ERR
                        self.canErr.update(self.errCode)
                        self.START_CAN_IAP.setEnabled(True)
                        self.send_process_show_start.update(0)
                        self.openFile.close()
                        return
                    else:
                        continue
        else:
            self.errCode = can_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
            self.canErr.update(self.errCode)
            self.START_CAN_IAP.setEnabled(True)
            self.send_process_show_start.update(0)
            self.openFile.close()
            return
        

        rxid.id_frame = int(rxbuff[0])
        if rxid.bit.state_code == 0:
            for group_index in range(data_group):
                file_data_buf = list(filebuff[list_index:list_index+2048])
                list_index+=2048
                list_index1 = 0
                self.index.value = 0
                for j in range(256):
                    txdata = list(file_data_buf[list_index1:list_index1+8])
                    list_index1+=8           
                    self.Iap_SendData(txdata)
                    self.index.value += 1

                crc16 = calculate_crc16(file_data_buf)
                for k in range(3):
                    try:
                        self.Iap_Download(crc16)
                        rxbuff = list(iapRXdata.get(timeout=1))
                        break
                    except:
                        if k == 2:
                            self.errCode = can_err_code.NO_DEVICE_FOUND_ERR
                            self.canErr.update(self.errCode)
                            self.START_CAN_IAP.setEnabled(True)
                            self.send_process_show_start.update(0)
                            self.openFile.close()
                            return
                        else:
                            continue
                rxid.id_frame = int(rxbuff[0])
                if rxid.bit.state_code != 0:
                    self.errCode = can_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                    self.canErr.update(self.errCode)
                    self.START_CAN_IAP.setEnabled(True)
                    self.send_process_show_start.update(0)
                    self.openFile.close()
                    return
                
                self.send_process_count_update.update(group_index + 1)

            if left_data_size > 0:
                file_data_buf = list(filebuff[list_index:list_index+left_data_size])
                list_index1 = 0
                self.index.value = 0

                for i in range(left_data_size // 8):
                    txdata = list(file_data_buf[list_index1:list_index1+8])
                    list_index1+=8
                    self.Iap_SendData(txdata)
                    self.index.value+=1

                crc16 = calculate_crc16(file_data_buf)
                for k in range(3):
                    try:
                        self.Iap_Download(crc16)
                        rxbuff = list(iapRXdata.get(timeout=1))
                        break
                    except:
                        if k == 2:
                            self.errCode = can_err_code.NO_DEVICE_FOUND_ERR
                            self.canErr.update(self.errCode)
                            self.START_CAN_IAP.setEnabled(True)
                            self.send_process_show_start.update(0)
                            self.openFile.close()
                            return
                        else:
                            continue
                rxid.id_frame = int(rxbuff[0])
                if rxid.bit.state_code != 0:
                    self.errCode = can_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                    self.canErr.update(self.errCode)
                    self.START_CAN_IAP.setEnabled(True)
                    self.send_process_show_start.update(0)
                    self.openFile.close()
                    return
                self.send_process_count_update.update(data_group + 1)
                self.openFile.close()
            else:
                self.openFile.close()

            for i in range(3):
                try:
                    self.Iap_Done()
                    rxbuff = list(iapRXdata.get(timeout=1))
                    break
                except:
                    if i == 2:
                        self.errCode = can_err_code.NO_DEVICE_FOUND_ERR
                        self.canErr.update(self.errCode)
                        self.START_CAN_IAP.setEnabled(True)
                        self.send_process_show_start.update(0)
                        return
                    else:
                        continue

            rxid.id_frame = int(rxbuff[0])
            if rxid.bit.state_code != 0:
                self.errCode = can_err_code.DEVICE_FLASH_CHECK_ERR
                self.canErr.update(self.errCode)
                self.START_CAN_IAP.setEnabled(True)
                return
            self.errCode = can_err_code.DEVICE_FLASH_CHECK_SUCCESS
            self.canErr.update(self.errCode)
        else:
            self.errCode = can_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
            self.canErr.update(self.errCode)
            self.START_CAN_IAP.setEnabled(True)
            return

        self.START_CAN_IAP.setEnabled(True)



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
        return ret
    
    def bootSend(self):
        id = ID_VALUE()
        data = [0] * 8
        id.bit.state_code = 0
        id.bit.func_code = 0x09
        id.bit.dev_id = 0x00
        id.bit.scr_id = 0x3f
        id.bit.index = 0
        self.Can_Transmit(id.id_frame, data)

    def Iap_Req(self):
        id = ID_VALUE()
        data = [0] * 8
        data[0] = self.file_size & 0xFF
        data[1] = (self.file_size >> 8) & 0xFF
        data[2] = (self.file_size >> 16) & 0xFF
        data[3] = self.file_size >> 24
        data[4] = self.crc16 & 0xFF
        data[5] = (self.crc16 >> 8) & 0xFF
        data[6] = 0
        data[7] = 0
        id.bit.state_code = 0
        id.bit.func_code = 0x19
        id.bit.dev_id = self.deviceID
        id.bit.scr_id = 0x3f
        id.bit.index = 0
        self.Can_Transmit(id.id_frame, data)

    def Iap_Erase(self):
        id = ID_VALUE()
        data = [0] * 8
        id.bit.state_code = 0
        id.bit.func_code = 0x29
        id.bit.dev_id = self.deviceID
        id.bit.scr_id = 0x3f
        id.bit.index = 0
        self.Can_Transmit(id.id_frame, data)

    def Iap_SendData(self,bindata: list):
        id = ID_VALUE()
        data = list(bindata)
        id.bit.state_code = 0
        id.bit.func_code = 0x39
        id.bit.dev_id = self.deviceID
        id.bit.scr_id = 0x3f
        id.bit.index = self.index.value
        self.Can_Transmit(id.id_frame, data)

    def Iap_Download(self,crc16: int):
        id = ID_VALUE()
        data = [0] * 8
        data[0] = crc16 & 0xFF
        data[1] = (crc16 >> 8) & 0xFF
        id.bit.state_code = 0
        id.bit.func_code = 0x49
        id.bit.dev_id = self.deviceID
        id.bit.scr_id = 0x3f
        id.bit.index = 0
        self.Can_Transmit(id.id_frame, data)

    def Iap_Done(self):
        id = ID_VALUE()
        data = [0] * 8
        id.bit.state_code = 0
        id.bit.func_code = 0x59
        id.bit.dev_id = self.deviceID
        id.bit.scr_id = 0x3f
        id.bit.index = 0
        self.Can_Transmit(id.id_frame, data)

    def rcv_Data(self):
        global rx_vci_can_obj,rxlen
        print('CAN通道接收线程启动')
        time.sleep(0.001)
        while self.DeviceOpenSta == 1:
            ret = canDLL.VCI_Receive(VCI_USBCAN2, self.CanDeviceIndex, self.devicePass_index, byref(rx_vci_can_obj.ADDR), 2500, 0)
            if ret > 0:#接收到数据
                timeStr = Time_get.get_strTime()
                for i in range(0,ret):
                    if self.Updatathread.is_alive():
                        rcvID = ID_VALUE()
                        rcvID.id_frame = int(rx_vci_can_obj.STRUCT_ARRAY[i].ID)
                        if (rcvID.bit.scr_id == self.deviceID) and (rcvID.bit.dev_id == 0x3F) or (rcvID.bit.func_code & 0x09 == 0x09):
                            data = [0] * 9
                            data[0] = int(rcvID.id_frame)
                            for a in range(8):
                                data[a+1] = int(rx_vci_can_obj.STRUCT_ARRAY[i].Data[i])
                            iapRXdata.put(data)

                    idstr = " id:"+str(hex(rx_vci_can_obj.STRUCT_ARRAY[i].ID)) + " "
                    lenstr = "len:" + str(hex(rx_vci_can_obj.STRUCT_ARRAY[i].DataLen)) + " data:"
                    datastr = ' '.join(f'{byte:02X}' for byte in rx_vci_can_obj.STRUCT_ARRAY[i].Data)
                    show_str = "[" + timeStr + "]" + "收←◆" + idstr + lenstr + datastr
                    self.ui_update.update(show_str)
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
            if self.rcvDataThread.is_alive():
                self.rcvDataThread.join()                 
            self.CanDeviceIndexx = self.CAN_DEVICE_INDEX.currentIndex()
            ret = canDLL.VCI_CloseDevice(VCI_USBCAN2, self.CanDeviceIndexx)
            self.SCAN_USBDEVICE.setEnabled(True)
            self.OPEN_CAN_DEVICE.setText("打开CAN分析仪")
            print("关闭CAN分析仪")

        self.OPEN_CAN_DEVICE.setEnabled(True)

    def clear_data(self):
        self.CAN_FRAME_SHOWED.clear()

    def send_process_count_reflash(self, cnt):
        self.sendProgress.setValue(cnt)

    def send_process_window(self, ctr):
        if ctr:
            self.sendProgress = QProgressDialog(
                "更新进度", "取消", 0, self.sendProcessCount, self
            )
            self.sendProgress.setFixedSize(300, 150)
            self.sendProgress.setWindowTitle("正在更新")
            self.sendProgress.show()
        else:
            self.sendProgress.close()
    def err_code_warning(self, index):
        match index:
            case can_err_code.DATA_LEN_OVERRANGE_ERR:
                QMessageBox.warning(
                    None, "警告", "数据超过1024Bytes! ! !", QMessageBox.Ok
                )
                self.errCode = 0


            case can_err_code.FILE_NOT_EXIST_ERR:
                QMessageBox.warning(
                    None, "警告", "文件不存在或路径错误！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.FILE_SIZE_OVERRANGE:
                QMessageBox.warning(
                    None, "警告", "文件大小超出限制！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.FILE_READ_ERR:
                QMessageBox.critical(
                    None, "错误", "文件读取出现错误！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.FILE_SEND_ERR:
                QMessageBox.critical(
                    None, "错误", "文件发送出现中断,发送失败！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.NO_DEVICE_FOUND_ERR:
                QMessageBox.critical(
                    None, "错误", "目标设备未响应,中断升级", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.DEVICE_RESPOND_TIMEOUT_ERR:
                QMessageBox.critical(
                    None, "错误", "目标设备响应超时,中断升级", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.DEVICE_FLASH_ERASE_ERR:
                QMessageBox.critical(None, "错误", "擦除失败,中断升级", QMessageBox.Ok)
                self.errCode = 0

            case can_err_code.DEVICE_FLASH_WRITE_ERR:
                QMessageBox.critical(None, "错误", "烧录错误,中断升级", QMessageBox.Ok)
                self.errCode = 0

            case can_err_code.DEVICE_FLASH_CHECK_ERR:
                QMessageBox.critical(None, "错误", "校验失败,升级失败", QMessageBox.Ok)
                self.errCode = 0

            case can_err_code.DEVICE_FLASH_CHECK_SUCCESS:
                QMessageBox.information(
                    None, "提示", "固件已完成升级！", QMessageBox.Ok
                )
                self.errCode = 0

            case can_err_code.DEVICE_FLASH_CHECK_ERR:
                QMessageBox.critical(
                    None, "错误", "设备回应错误,中断升级", QMessageBox.Ok
                )
                self.errCode = 0
        
      