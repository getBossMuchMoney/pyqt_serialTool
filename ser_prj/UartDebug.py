import sys, os
from serial import Serial
from cushy_serial import CushySerial
from serial.tools import list_ports
from threading import Thread, Event
from PyQt5.QtWidgets import *
from Ui_untitled import Ui_MainWindow
from PyQt5.QtCore import Qt, QThread, QCoreApplication
import multiprocessing
from multiprocessing import Pool, Process, Value, Array, Manager, Queue
from enum import IntEnum
import time
from PyQt5.QtGui import QTextCursor, QIntValidator
from myTimer import msTimer, msTimer_Call
import Time_get
import ctypes
from crc import *
from mySinal import *


class WorkThread(QThread):
    def __int__(self):
        # 初始化函数
        super().__init__()

    def run(self):
        {}


class com_err_code(IntEnum):
    AUTO_SEND_TIME_SET_ERR = 0
    AUTO_SEND_TIME_NONE_ERR = 1
    AUTO_SEND_OPEN_ERR = 2
    COM_OPEN_ERR = 3
    SEND_DATA_FORMAT_ERR = 4
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


class com_state(IntEnum):
    CLOSE = 0
    OPEN = 1


# 父进程全局变量
Com_Open_Flag = com_state.CLOSE  # 串口打开标志
custom_serial = CushySerial
usart_process = None
usart_workState = Queue()
serial_cfg = Queue()
usart_data = Queue()
rx_data = Queue()
tx_data = Queue()
heartbeat = Queue()
subPkg_timeout = Value("i", 0)
comState = Value("i", com_state.CLOSE)
comListTimer = msTimer(None, 0)
auto_send_timer = msTimer(None, 0)
working_com = None
_1000msTimer = msTimer_Call(1000)
cmdrxQueue = Queue()
File_Process_Flag = Value("i", 0)


@_1000msTimer.msTimer_callback()
def pprocess_heartbeat():
    heartbeat.put(1)
    print("心跳开启")


# 子进程全局变量
sSerial = 0
recClose_event = Event()
sendClose_event = Event()
pprocess_killed = False
subpkgTimeCNT = 0
subpkgTimeCfg = 0
timerMScnt = ctypes.c_uint64(0)
recvStart = 0
recvMsgBuff = list()
recvLen = 0
_1msTimer = msTimer_Call(1)


@_1msTimer.msTimer_callback()
def subpackage_timecheck():
    global subpkgTimeCNT, subpkgTimeCfg, timerMScnt
    if subpkgTimeCNT < subpkgTimeCfg and recvStart == 1:
        subpkgTimeCNT += 1
    timerMScnt.value += 1


_2000msTimer = msTimer_Call(2000)


@_2000msTimer.msTimer_callback()
def subprocess_quit():
    global pprocess_killed
    pprocess_killed = True


def clear(q):
    while q.empty() == False:
        q.get_nowait()


def getTimerMS():
    return timerMScnt.value


# 串口接收数据处理线程
def rec_deal(recClose_event, rx_data, subPkg_timeout, cmdrxQueue, File_Process_Flag):
    global sSerial,subpkgTimeCfg, subpkgTimeCNT, recvMsgBuff, recvStart, recvLen

    while not recClose_event.is_set():
        subpkgTimeCfg = subPkg_timeout.value
        recdata = sSerial.read_all()
        dataLen = len(recdata)
        if dataLen > 0:
            recvLen += dataLen
            if recvLen == dataLen:
                strTimeRcv = Time_get.get_strTime()
                recvMsgBuff.extend([strTimeRcv])
            recvStart = 1
            recvMsgBuff += recdata
            subpkgTimeCNT = 0

            if recvLen > 4000:
                subpkgTimeCNT = subpkgTimeCfg

            if 0 == subpkgTimeCfg or subpkgTimeCNT == subpkgTimeCfg:
                recvLen = 0
                rx_data.put(recvMsgBuff)
                if File_Process_Flag.value == 1:
                    rcvcmd = list(recvMsgBuff)
                    rcvcmd.pop(0)
                    time.sleep(0.001)
                    cmdrxQueue.put(rcvcmd)
                recvMsgBuff = list()

        else:
            if subpkgTimeCNT == subpkgTimeCfg and recvLen > 0:
                recvLen = 0
                rx_data.put(recvMsgBuff)
                if File_Process_Flag.value == 1:
                    rcvcmd = list(recvMsgBuff)
                    rcvcmd.pop(0)
                    time.sleep(0.001)
                    cmdrxQueue.put(rcvcmd)
                recvMsgBuff = list()
            else:
                time.sleep(0.001)


def send_deal(sendClose_event, usart_workState, tx_data):
    global sSerial
    while not sendClose_event.is_set():
        if tx_data.empty() == False:
            data = tx_data.get()
            try:
                sSerial.write(data)
                send_finish = 1
                usart_workState.put(send_finish)
            except:
                send_fail = 0
                usart_workState.put(send_fail)

        else:
            time.sleep(0.001)  # 降低cpu占用率


# 进行串口配置
def usart_setting(
    serial_cfg,
    usart_workState,
    rx_data,
    tx_data,
    heartbeat,
    subPkg_timeout,
    cmdrxQueue,
    File_Process_Flag,
):
    global sSerial, recClose_event
    try:
        seriConf = serial_cfg.get(block=True)
        sSerial = CushySerial(seriConf[0], seriConf[1], timeout=0.5)
    except:
        usart_workState.put(com_state.CLOSE)
        print("串口配置失败")
        return

    if sSerial.isOpen() == True:
        print("串口打开成功")
        rec_thread = Thread(
            target=rec_deal,
            args=(
                recClose_event,
                rx_data,
                subPkg_timeout,
                cmdrxQueue,
                File_Process_Flag,
            ),
        )
        send_thread = Thread(
            target=send_deal, args=(sendClose_event, usart_workState, tx_data)
        )
        rec_thread.start()
        send_thread.start()
        _2000msTimer.start()
        _1msTimer.start()
        usart_workState.put(com_state.OPEN)
        while True:
            if pprocess_killed == True:
                recClose_event.set()
                sendClose_event.set()
                rec_thread.join()
                send_thread.join()
                clear(rx_data)
                clear(tx_data)
                sSerial.close()
                _2000msTimer.pause()
                _1msTimer.pause()
                break

            if serial_cfg.empty() == False:
                if serial_cfg.get() == com_state.CLOSE:
                    print("串口关闭")
                    recClose_event.set()
                    sendClose_event.set()
                    rec_thread.join()
                    send_thread.join()
                    clear(rx_data)
                    clear(tx_data)
                    sSerial.close()
                    _2000msTimer.pause()
                    _1msTimer.pause()
                    break

            if heartbeat.empty() == False:
                heartbeat.get()
                _2000msTimer.pause()
                _2000msTimer.start()
            else:
                time.sleep(0.001)


# 获取串口列表
def Get_Com_List():
    return list(list_ports.comports())


# 字节串转整形列表
def bytesrialtoarray(msg):
    data = []
    buf = [hex(x) for x in bytes(msg)]
    for i in range(len(buf)):
        data.append(int(buf[i], 16))

    return data


class UartWindow(QWidget):
    def __init__(self,ui_main_window):
        band = ["9600", "19200", "115200", "460800", "2000000"]
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
        self.errCode = 0
        self.send_len = 0
        self.recv_len = 0
        self.sendProcessCount = 0

        super().__init__()
        self.ui = ui_main_window

        self.send_thread = Thread(target=self.send_data_process)
        self.send_file_thread = Thread(target=self.send_file_process)

        self.now_enco_form = "UTF-8"
        self.file_data_buf = list()
        self.file_size = 0
        self.crc32 = 0
        self.deviceID = 0
        self.index = ctypes.c_uint8(0)

        self.ui_update = ui_show()
        self.ui_update.update_signal.connect(self.ui_show_refresh)

        self.comErr = number_check()
        self.comErr.update_signal.connect(self.err_code_warning)

        self.send_count_update = state_check()
        self.send_count_update.update_signal.connect(self.send_cnt_reflash)
        self.recv_count_update = state_check()
        self.recv_count_update.update_signal.connect(self.recv_cnt_reflash)

        self.send_process_show_start = number_check()
        self.send_process_show_start.update_signal.connect(self.send_process_window)

        self.send_process_count_update = number_check()
        self.send_process_count_update.update_signal.connect(
            self.send_process_count_reflash
        )

        self.ClearRecShow = self.ui.ClearRecShow
        self.ClearSendShow = self.ui.ClearSendShow
        self.Send_Data = self.ui.Send_Data
        self.Open_Com = self.ui.Open_Com
        self.send_auto = self.ui.send_auto
        self.encodingFormat = self.ui.encodingFormat
        self.open_file_click = self.ui.open_file_click
        self.start_update_click = self.ui.start_update_click
        self.subpackageCheck = self.ui.subpackageCheck
        self.SaveDataCheck = self.ui.SaveDataCheck
        self.Data_Display = self.ui.Data_Display
        self.ChosedeviceID = self.ui.ChosedeviceID
        self.sendLength = self.ui.sendLength
        self.file_selected = self.ui.file_selected
        self.ComReflash = self.ui.ComReflash
        self.sendHex = self.ui.sendHex
        self.send_freq = self.ui.send_freq
        self.Com_Port = self.ui.Com_Port
        self.receiveLength = self.ui.receiveLength
        self.recSubpackageTimeOut_input = self.ui.recSubpackageTimeOut_input
        self.recHexShow = self.ui.recHexShow
        self.Com_Band = self.ui.Com_Band
        self.Send_Data_Display = self.ui.Send_Data_Display

        self.ClearRecShow.clicked.connect(self.recv_show_clear)
        self.ClearSendShow.clicked.connect(self.send_show_clear)
        self.Send_Data.clicked.connect(self.send_data_click) # type: ignore
        self.Open_Com.clicked.connect(self.open_com_click) # type: ignore
        self.send_auto.clicked.connect(self.send_auto_click) # type: ignore
        self.encodingFormat.clicked.connect(self.switch_encodingFormat) # type: ignore
        self.open_file_click.clicked.connect(self.open_file) # type: ignore
        self.start_update_click.clicked.connect(self.send_file) # type: ignore
        self.subpackageCheck.clicked.connect(self.subpackage_click) # type: ignore
        self.SaveDataCheck.clicked.connect(self.save_data_click) # type: ignore

        self.ui.sendLength.setText(str(0))
        self.ui.receiveLength.setText(str(0))

        self.savedatafile = None

        # 创建一个整数验证器
        validator = QIntValidator()
        # 设置验证器的范围，这里可以设置允许的最小值和最大值
        validator.setRange(0, 999999)  # 定时发送范围 单位毫秒
        # 设置验证器到 send_freq 中
        self.send_freq.setValidator(validator)

        recSubpackageTimeOut_validator = QIntValidator()
        recSubpackageTimeOut_validator.setRange(0, 999)
        self.recSubpackageTimeOut_input.setValidator(recSubpackageTimeOut_validator)
        self.recSubpackageTimeOut_input.setText(str(0))

        self.ComReflash.clicked.connect(self.com_reflash)
        self.combuf = 0
        self.COM_List = 0

        self.com_thread = Thread(target=self.com_conctrl)

        self.com_reflash()
        comListTimer.change(self.com_reflash, 3000)
        comListTimer.start()


        # 加载串口波特率选项
        for i in range(0, len(band)):
            self.Com_Band.addItem(band[i])

        # 加载选择设备选项
        for i in range(0, len(DeviceIdList)):
            self.ChosedeviceID.addItem(DeviceIdList[i])

    def save_data_click(self):
        if self.SaveDataCheck.isChecked():
            Time_get.get_DataFileName()
            self.SaveDataCheck.setEnabled(False)
            self.create_datafile_thread = Thread(target=self.create_datafile_process)
            self.create_datafile_thread.start()
        else:
            if self.savedatafile != None:
                self.savedatafile.close()
                self.savedatafile = None

    def create_datafile_process(self):
        if not os.path.exists("datafile"):
            os.makedirs("datafile")
            print("Folder created")
        else:
            print("Folder already exists")
        filePath = os.getcwd() + "\\datafile\\" + Time_get.get_DataFileName() + ".txt"
        self.savedatafile = open(filePath, "w")
        print(self.savedatafile.name)
        time.sleep(1)
        self.SaveDataCheck.setEnabled(True)

    def subpackage_click(self):
        global subPkg_timeout
        if self.subpackageCheck.isChecked():
            self.recSubpackageTimeOut_input.setEnabled(False)
            time = int(self.recSubpackageTimeOut_input.text())
            if time > 0:
                subPkg_timeout.value = time

        else:
            self.recSubpackageTimeOut_input.setEnabled(True)
            subPkg_timeout.value = 0

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

    def open_file(self):
        if not self.send_file_thread.is_alive():
            self.fname = QFileDialog.getOpenFileName(
                self, "打开文件", "/"
            )  # filter='*.txt',此参数指定文件类型

            if self.fname[0]:
                self.file_size = os.path.getsize(self.fname[0])
                print("文件大小", self.file_size)
                if self.file_size > 1024 * 1024 * 1024:
                    self.errCode = com_err_code.FILE_SIZE_OVERRANGE
                    self.comErr.update(self.errCode)
                    return

                try:
                    self.openFile = open(self.fname[0], "rb")
                    self.file_selected.clear()
                    self.file_selected.setText(self.fname[0])
                except:
                    return
            else:
                self.file_size = 0

    def send_file(self):
        if not self.send_file_thread.is_alive():
            if self.file_size > 0:
                print(self.file_selected.text())
                if self.file_selected.text() == self.fname[0]:
                    self.send_file_thread = Thread(target=self.send_file_process)
                    self.send_file_thread.start()
                    self.start_update_click.setEnabled(False)
                    self.Send_Data.setEnabled(False)

                else:
                    try:
                        self.openFile = open(self.file_selected.text(), "rb")
                        self.file_size = os.path.getsize(self.file_selected.text())
                        self.send_file_thread = Thread(target=self.send_file_process)
                        self.send_file_thread.start()
                        self.start_update_click.setEnabled(False)
                        self.Send_Data.setEnabled(False)

                    except:
                        self.errCode = com_err_code.FILE_NOT_EXIST_ERR
                        self.comErr.update(self.errCode)

            else:
                try:
                    self.openFile = open(self.file_selected.text(), "rb")
                    self.file_size = os.path.getsize(self.file_selected.text())
                    self.send_file_thread = Thread(target=self.send_file_process)
                    self.send_file_thread.start()
                    self.start_update_click.setEnabled(False)
                    self.Send_Data.setEnabled(False)

                except:
                    self.errCode = com_err_code.FILE_NOT_EXIST_ERR
                    self.comErr.update(self.errCode)

    def Iap_Req(self):     
        self.txbuff = [0] * 12
        self.txbuff[0] = ord("i")
        self.txbuff[1] = ord("a")
        self.txbuff[2] = ord("p")
        self.txbuff[3] = self.deviceID
        self.txbuff[4] = self.file_size & 0xFF
        self.txbuff[5] = (self.file_size >> 8) & 0xFF
        self.txbuff[6] = (self.file_size >> 16) & 0xFF
        self.txbuff[7] = self.file_size >> 24
        self.txbuff[8] = self.crc32 & 0xFF
        self.txbuff[9] = (self.crc32 >> 8) & 0xFF
        self.txbuff[10] = (self.crc32 >> 16) & 0xFF
        self.txbuff[11] = self.crc32 >> 24
        add_crc16_to_list(self.txbuff)
        tx_data.put(self.txbuff)

    def Iap_Erase(self):
        self.txbuff = [0] * 6
        self.txbuff[0] = ord("e")
        self.txbuff[1] = ord("r")
        self.txbuff[2] = ord("a")
        self.txbuff[3] = ord("s")
        self.txbuff[4] = ord("e")
        self.txbuff[5] = self.deviceID
        add_crc16_to_list(self.txbuff)
        tx_data.put(self.txbuff)

    def Iap_Write(self, bindata: list):
        self.txbuff = [0] * 6
        self.txbuff[0] = 0x55
        self.txbuff[1] = 0xAA
        self.txbuff[2] = self.deviceID
        self.txbuff[3] = (len(bindata) >> 8) & 0xFF
        self.txbuff[4] = len(bindata) & 0xFF
        self.txbuff[5] = self.index.value
        self.txbuff.extend(bindata)
        add_crc16_to_list(self.txbuff)
        tx_data.put(self.txbuff)

    def Iap_Done(self):
        self.txbuff = [0] * 5
        self.txbuff[0] = ord("d")
        self.txbuff[1] = ord("o")
        self.txbuff[2] = ord("n")
        self.txbuff[3] = ord("e")
        self.txbuff[4] = self.deviceID
        add_crc16_to_list(self.txbuff)
        tx_data.put(self.txbuff)

    def check_uartSendFileSta(self):
        send_fail = 0
        timeStr = Time_get.get_strTime()
        try:
            if (
                usart_process.is_alive() == False
                or Com_Open_Flag == com_state.CLOSE
                or send_fail == usart_workState.get(timeout=3)
            ):  # 等待一帧发送完毕，超时3秒
                print("发送失败")
                subPkg_timeout.value = 0
                self.openFile.close()
                self.send_process_show_start.update(0)
                self.errCode = com_err_code.FILE_SEND_ERR
                self.comErr.update(self.errCode)
                self.start_update_click.setEnabled(True)
                self.Send_Data.setEnabled(True)
                self.ChosedeviceID.setEnabled(True)
                return
        except:
            print("发送超时")
            subPkg_timeout.value = 0
            self.openFile.close()
            self.send_process_show_start.update(0)
            self.errCode = com_err_code.FILE_SEND_ERR
            self.comErr.update(self.errCode)
            self.start_update_click.setEnabled(True)
            self.Send_Data.setEnabled(True)
            self.ChosedeviceID.setEnabled(True)
            return
        

        if self.recHexShow.isChecked():
            show_str = ' '.join(f'{byte:02X}' for byte in self.txbuff)
            
        else:

            show_str = ''.join(chr(i) if 0 <= i <= 127 else '?' for i in self.txbuff)

        show_str = "[" + timeStr + "]" + "发→◇" + show_str + "\n"
        self.ui_update.update(show_str)

        if self.SaveDataCheck.isChecked() and self.savedatafile != None:
            self.savedatafile.write(show_str + "\n")


    def send_file_process(self):
        self.txbuff = list()
        filebuff = list(self.openFile.read(self.file_size))
        k = self.file_size % 16
        if k != 0:
            for i in range(16 - k):
                filebuff.append(0xFF)
                self.file_size += 1

        group_index = 0
        list_index = 0
        rxbuff = list()
        File_Process_Flag.value = 1
        subPkg_timeout.value = 20
        self.index.value = 0
        self.ChosedeviceID.setEnabled(False)
        self.deviceID = self.ChosedeviceID.currentIndex() + 1
        self.crc32 = crc32_for_byte_list(filebuff)
        data_group = self.file_size // 2048
        left_data_size = self.file_size % 2048
        if data_group > 0 and left_data_size > 0:
            self.sendProcessCount = data_group + 1
        elif data_group == 0:
            self.sendProcessCount = 1
        else:
            self.sendProcessCount = data_group
        print(self.crc32, data_group, left_data_size)
        self.send_process_show_start.update(1)

        for i in range(3):
            try:
                self.Iap_Req()
                self.check_uartSendFileSta()
                # 更新软件已发送字节数
                self.send_len += 14
                self.send_count_update.update()
                rxbuff = cmdrxQueue.get(timeout=2)
                break
            except:
                if i == 2:
                    subPkg_timeout.value = 0
                    self.send_process_show_start.update(0)
                    self.errCode = com_err_code.NO_DEVICE_FOUND_ERR
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return
                else:
                    continue
                1

        self.file_size = 0

        if (
            rxbuff[0] == ord("i")
            and rxbuff[1] == ord("a")
            and rxbuff[2] == ord("p")
            and rxbuff[3] == self.deviceID
        ):
            crc16L, crc16H = list_to_crc16(rxbuff, len(rxbuff) - 2)
            if crc16L == rxbuff[len(rxbuff) - 2] and crc16H == rxbuff[len(rxbuff) - 1]:
                for i in range(3):
                    try:
                        self.Iap_Erase()
                        self.check_uartSendFileSta()
                        # 更新软件已发送字节数
                        self.send_len += 8
                        self.send_count_update.update()
                        rxbuff = list()
                        rxbuff = cmdrxQueue.get(timeout=2)
                        break
                    except:
                        if i == 2:
                            subPkg_timeout.value = 0
                            self.send_process_show_start.update(0)
                            self.errCode = com_err_code.DEVICE_FLASH_ERASE_ERR
                            self.comErr.update(self.errCode)
                            self.ChosedeviceID.setEnabled(True)
                            self.start_update_click.setEnabled(True)
                            self.Send_Data.setEnabled(True)
                            File_Process_Flag.value = 0
                            return
                        else:
                            continue
            else:
                subPkg_timeout.value = 0
                self.send_process_show_start.update(0)
                self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                self.comErr.update(self.errCode)
                self.ChosedeviceID.setEnabled(True)
                self.start_update_click.setEnabled(True)
                self.Send_Data.setEnabled(True)
                File_Process_Flag.value = 0
                return

        else:
            subPkg_timeout.value = 0
            self.send_process_show_start.update(0)
            self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
            self.comErr.update(self.errCode)
            self.ChosedeviceID.setEnabled(True)
            self.start_update_click.setEnabled(True)
            self.Send_Data.setEnabled(True)
            File_Process_Flag.value = 0
            return

        if (
            rxbuff[0] == ord("e")
            and rxbuff[1] == ord("r")
            and rxbuff[2] == ord("a")
            and rxbuff[3] == ord("s")
            and rxbuff[4] == ord("e")
            and rxbuff[5] == self.deviceID
        ):
            crc16L, crc16H = list_to_crc16(rxbuff, len(rxbuff) - 2)
            if crc16L == rxbuff[len(rxbuff) - 2] and crc16H == rxbuff[len(rxbuff) - 1]:
                if rxbuff[6] != 0:
                    subPkg_timeout.value = 0
                    self.errCode = com_err_code.DEVICE_FLASH_ERASE_ERR
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return
            else:
                subPkg_timeout.value = 0
                self.send_process_show_start.update(0)
                self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                self.comErr.update(self.errCode)
                self.ChosedeviceID.setEnabled(True)
                self.start_update_click.setEnabled(True)
                self.Send_Data.setEnabled(True)
                File_Process_Flag.value = 0
                return
        else:
            subPkg_timeout.value = 0
            self.send_process_show_start.update(0)
            self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
            self.comErr.update(self.errCode)
            self.ChosedeviceID.setEnabled(True)
            self.start_update_click.setEnabled(True)
            self.Send_Data.setEnabled(True)
            File_Process_Flag.value = 0
            return

        if data_group > 0:
            for group_index in range(0, data_group):
                if (
                    self.sendProgress.wasCanceled()
                    or Com_Open_Flag == com_state.CLOSE
                    or usart_process.is_alive() == False
                ):
                    self.file_size = 0
                    self.openFile.close()
                    self.send_process_show_start.update(0)
                    self.errCode = com_err_code.FILE_SEND_ERR
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return

                try:
                    self.file_data_buf = list(filebuff[list_index:list_index+2048])
                    list_index+=2048
                    for i in range(3):
                        try:
                            self.Iap_Write(self.file_data_buf)
                            self.check_uartSendFileSta()
                            # 更新软件已发送字节数
                            self.send_len += 2056
                            self.send_count_update.update()
                            rxbuff = list()
                            rxbuff = cmdrxQueue.get(timeout=5)
                            break
                        except:
                            if i == 2:
                                subPkg_timeout.value = 0
                                self.errCode = com_err_code.NO_DEVICE_FOUND_ERR
                                self.comErr.update(self.errCode)
                                self.send_process_show_start.update(0)
                                self.ChosedeviceID.setEnabled(True)
                                self.start_update_click.setEnabled(True)
                                self.Send_Data.setEnabled(True)
                                File_Process_Flag.value = 0
                                return
                            else:
                                continue
                except:
                    subPkg_timeout.value = 0
                    self.openFile.close()
                    self.send_process_show_start.update(0)
                    self.errCode = com_err_code.FILE_SEND_ERR
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return

                if (
                    rxbuff[0] == 0x55
                    and rxbuff[1] == 0xAA
                    and rxbuff[2] == self.deviceID
                    and rxbuff[3] == self.index.value
                ):
                    crc16L, crc16H = list_to_crc16(rxbuff, len(rxbuff) - 2)
                    if (
                        crc16L == rxbuff[len(rxbuff) - 2]
                        and crc16H == rxbuff[len(rxbuff) - 1]
                    ):
                        if rxbuff[4] == 0x00:
                            self.index.value += 1
                            self.send_process_count_update.update(group_index + 1)
                        else:
                            subPkg_timeout.value = 0
                            self.errCode = com_err_code.DEVICE_FLASH_WRITE_ERR
                            self.send_process_show_start.update(0)
                            self.comErr.update(self.errCode)
                            self.ChosedeviceID.setEnabled(True)
                            self.start_update_click.setEnabled(True)
                            self.Send_Data.setEnabled(True)
                            File_Process_Flag.value = 0
                            return

                    else:
                        subPkg_timeout.value = 0
                        self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                        self.comErr.update(self.errCode)
                        self.send_process_show_start.update(0)
                        self.ChosedeviceID.setEnabled(True)
                        self.start_update_click.setEnabled(True)
                        self.Send_Data.setEnabled(True)
                        File_Process_Flag.value = 0
                        return

                else:
                    subPkg_timeout.value = 0
                    self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                    self.comErr.update(self.errCode)
                    self.send_process_show_start.update(0)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return

                if i == data_group - 1 and left_data_size == 0:
                    self.openFile.close()

            if left_data_size > 0:
                self.file_data_buf = list(filebuff[list_index:list_index+left_data_size])
                for i in range(3):
                    try:
                        self.Iap_Write(self.file_data_buf)
                        self.check_uartSendFileSta()
                        # 更新软件已发送字节数
                        self.send_len += left_data_size + 8
                        self.send_count_update.update()
                        rxbuff = list()
                        rxbuff = cmdrxQueue.get(timeout=5)
                        break
                    except:
                        if i == 2:
                            subPkg_timeout.value = 0
                            self.errCode = com_err_code.NO_DEVICE_FOUND_ERR
                            self.comErr.update(self.errCode)
                            self.send_process_show_start.update(0)
                            self.ChosedeviceID.setEnabled(True)
                            self.start_update_click.setEnabled(True)
                            self.Send_Data.setEnabled(True)
                            File_Process_Flag.value = 0
                            return
                        else:
                            continue

                if (
                    rxbuff[0] == 0x55
                    and rxbuff[1] == 0xAA
                    and rxbuff[2] == self.deviceID
                    and rxbuff[3] == self.index.value
                ):
                    crc16L, crc16H = list_to_crc16(rxbuff, len(rxbuff) - 2)
                    if (
                        crc16L == rxbuff[len(rxbuff) - 2]
                        and crc16H == rxbuff[len(rxbuff) - 1]
                    ):
                        if rxbuff[4] == 0x00:
                            self.send_process_count_update.update(data_group + 1)
                            self.openFile.close()
                        else:
                            subPkg_timeout.value = 0
                            self.errCode = com_err_code.DEVICE_FLASH_WRITE_ERR
                            self.comErr.update(self.errCode)
                            self.send_process_show_start.update(0)
                            self.ChosedeviceID.setEnabled(True)
                            self.start_update_click.setEnabled(True)
                            self.Send_Data.setEnabled(True)
                            File_Process_Flag.value = 0
                            self.openFile.close()
                            return

                    else:
                        subPkg_timeout.value = 0
                        self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                        self.comErr.update(self.errCode)
                        self.send_process_show_start.update(0)
                        self.ChosedeviceID.setEnabled(True)
                        self.start_update_click.setEnabled(True)
                        self.Send_Data.setEnabled(True)
                        self.openFile.close()
                        File_Process_Flag.value = 0
                        return

                else:
                    subPkg_timeout.value = 0
                    self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    self.openFile.close()
                    File_Process_Flag.value = 0
                    return

        else:
            try:
                self.file_data_buf = list(filebuff[0:left_data_size])
                for i in range(3):
                    try:
                        self.Iap_Write(self.file_data_buf)
                        self.check_uartSendFileSta()
                        # 更新软件已发送字节数
                        self.send_len += left_data_size + 8
                        self.send_count_update.update()
                        rxbuff = list()
                        rxbuff = cmdrxQueue.get(timeout=5)
                        break
                    except:
                        if i == 2:
                            subPkg_timeout.value = 0
                            self.errCode = com_err_code.NO_DEVICE_FOUND_ERR
                            self.comErr.update(self.errCode)
                            self.send_process_show_start.update(0)
                            self.ChosedeviceID.setEnabled(True)
                            self.start_update_click.setEnabled(True)
                            self.Send_Data.setEnabled(True)
                            File_Process_Flag.value = 0
                            self.openFile.close()
                            return
                        else:
                            continue
            except:
                subPkg_timeout.value = 0
                self.send_process_show_start.update(0)
                self.errCode = com_err_code.FILE_SEND_ERR
                self.comErr.update(self.errCode)
                self.ChosedeviceID.setEnabled(True)
                self.start_update_click.setEnabled(True)
                self.Send_Data.setEnabled(True)
                self.openFile.close()
                File_Process_Flag.value = 0
                return

            if (
                rxbuff[0] == 0x55
                and rxbuff[1] == 0xAA
                and rxbuff[2] == self.deviceID
                and rxbuff[3] == self.index.value
            ):
                crc16L, crc16H = list_to_crc16(rxbuff, len(rxbuff) - 2)
                if (
                    crc16L == rxbuff[len(rxbuff) - 2]
                    and crc16H == rxbuff[len(rxbuff) - 1]
                ):
                    if rxbuff[4] == 0x00:
                        self.send_process_count_update.update(1)
                        self.openFile.close()
                    else:
                        subPkg_timeout.value = 0
                        self.errCode = com_err_code.DEVICE_FLASH_WRITE_ERR
                        self.comErr.update(self.errCode)
                        self.send_process_show_start.update(0)
                        self.ChosedeviceID.setEnabled(True)
                        self.start_update_click.setEnabled(True)
                        self.Send_Data.setEnabled(True)
                        File_Process_Flag.value = 0
                        self.openFile.close()
                        return

                else:
                    subPkg_timeout.value = 0
                    self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                    self.comErr.update(self.errCode)
                    self.send_process_show_start.update(0)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    self.openFile.close()
                    return
            else:
                subPkg_timeout.value = 0
                self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                self.comErr.update(self.errCode)
                self.send_process_show_start.update(0)
                self.ChosedeviceID.setEnabled(True)
                self.start_update_click.setEnabled(True)
                self.Send_Data.setEnabled(True)
                File_Process_Flag.value = 0
                self.openFile.close()
                return

        try:
            for i in range(3):
                try:
                    self.Iap_Done()
                    self.check_uartSendFileSta()
                    # 更新软件已发送字节数
                    self.send_len += 7
                    self.send_count_update.update()
                    rxbuff = list()
                    rxbuff = cmdrxQueue.get(timeout=2)
                    break
                except:
                    if i == 2: 
                        subPkg_timeout.value = 0
                        self.errCode = com_err_code.NO_DEVICE_FOUND_ERR
                        self.comErr.update(self.errCode)
                        self.ChosedeviceID.setEnabled(True)
                        self.start_update_click.setEnabled(True)
                        self.Send_Data.setEnabled(True)
                        File_Process_Flag.value = 0
                        return
                    else:
                        continue
        except:
            subPkg_timeout.value = 0
            self.errCode = com_err_code.FILE_SEND_ERR
            self.comErr.update(self.errCode)
            self.ChosedeviceID.setEnabled(True)
            self.start_update_click.setEnabled(True)
            self.Send_Data.setEnabled(True)
            File_Process_Flag.value = 0
            return

        if (
            rxbuff[0] == ord("d")
            and rxbuff[1] == ord("o")
            and rxbuff[2] == ord("n")
            and rxbuff[3] == ord("e")
            and rxbuff[4] == self.deviceID
        ):
            crc16L, crc16H = list_to_crc16(rxbuff, len(rxbuff) - 2)
            if crc16L == rxbuff[len(rxbuff) - 2] and crc16H == rxbuff[len(rxbuff) - 1]:
                if rxbuff[5] == 0x00:
                    subPkg_timeout.value = 0
                    self.errCode = com_err_code.DEVICE_FLASH_CHECK_SUCCESS
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return

                else:
                    subPkg_timeout.value = 0
                    self.errCode = com_err_code.DEVICE_FLASH_CHECK_ERR
                    self.comErr.update(self.errCode)
                    self.ChosedeviceID.setEnabled(True)
                    self.start_update_click.setEnabled(True)
                    self.Send_Data.setEnabled(True)
                    File_Process_Flag.value = 0
                    return
            else:
                subPkg_timeout.value = 0
                self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
                self.comErr.update(self.errCode)
                self.ChosedeviceID.setEnabled(True)
                self.start_update_click.setEnabled(True)
                self.Send_Data.setEnabled(True)
                File_Process_Flag.value = 0
                return
        else:
            subPkg_timeout.value = 0
            self.errCode = com_err_code.DEVICE_NOT_CORRECT_RESPOND_ERR
            self.comErr.update(self.errCode)
            self.ChosedeviceID.setEnabled(True)
            self.start_update_click.setEnabled(True)
            self.Send_Data.setEnabled(True)
            File_Process_Flag.value = 0
            return

    # ui刷新槽函数
    def ui_show_refresh(self, data):
        self.Data_Display.append(data)

    # 发送数量刷新槽函数
    def send_cnt_reflash(self):
        self.sendLength.setText(str(self.send_len))

    # 接收数量刷新槽函数
    def recv_cnt_reflash(self):
        self.receiveLength.setText(str(self.recv_len))

    def send_show_clear(self):
        self.Send_Data_Display.clear()

    def recv_show_clear(self):
        self.recv_len = 0
        self.send_len = 0
        self.send_count_update.update()
        self.recv_count_update.update()
        self.Data_Display.clear()

    def switch_encodingFormat(self):
        if self.encodingFormat.text() == "UTF-8":
            self.now_enco_form = "GBK"
            self.encodingFormat.setText("GBK")
        else:
            self.now_enco_form = "UTF-8"
            self.encodingFormat.setText("UTF-8")

    def err_code_warning(self, index):
        match index:
            case com_err_code.AUTO_SEND_TIME_SET_ERR:
                QMessageBox.warning(
                    None, "警告", "发送时间间隔不能为零！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.AUTO_SEND_TIME_NONE_ERR:
                QMessageBox.warning(
                    None, "警告", "请设置发送时间间隔！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.AUTO_SEND_OPEN_ERR:
                QMessageBox.warning(
                    None, "警告", "只允许连接后开启！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.COM_OPEN_ERR:
                QMessageBox.warning(
                    None, "警告", "串口被占用或不存在等其他情况！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.SEND_DATA_FORMAT_ERR:
                QMessageBox.warning(
                    None, "警告", "待发送数据格式错误！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.DATA_LEN_OVERRANGE_ERR:
                QMessageBox.warning(
                    None, "警告", "数据超过1024Bytes！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.FILE_NOT_EXIST_ERR:
                QMessageBox.warning(
                    None, "警告", "文件不存在或路径错误！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.FILE_SIZE_OVERRANGE:
                QMessageBox.warning(
                    None, "警告", "文件大小超出限制！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.FILE_READ_ERR:
                QMessageBox.critical(
                    None, "错误", "文件读取出现错误！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.FILE_SEND_ERR:
                QMessageBox.critical(
                    None, "错误", "文件发送出现中断,发送失败！！！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.NO_DEVICE_FOUND_ERR:
                QMessageBox.critical(
                    None, "错误", "目标设备未响应,中断升级", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.DEVICE_RESPOND_TIMEOUT_ERR:
                QMessageBox.critical(
                    None, "错误", "目标设备响应超时,中断升级", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.DEVICE_FLASH_ERASE_ERR:
                QMessageBox.critical(None, "错误", "擦除失败,中断升级", QMessageBox.Ok)
                self.errCode = 0

            case com_err_code.DEVICE_FLASH_WRITE_ERR:
                QMessageBox.critical(None, "错误", "烧录错误,中断升级", QMessageBox.Ok)
                self.errCode = 0

            case com_err_code.DEVICE_FLASH_CHECK_ERR:
                QMessageBox.critical(None, "错误", "校验失败,升级失败", QMessageBox.Ok)
                self.errCode = 0

            case com_err_code.DEVICE_FLASH_CHECK_SUCCESS:
                QMessageBox.information(
                    None, "提示", "固件已完成升级！", QMessageBox.Ok
                )
                self.errCode = 0

            case com_err_code.DEVICE_FLASH_CHECK_ERR:
                QMessageBox.critical(
                    None, "错误", "设备回应错误,中断升级", QMessageBox.Ok
                )
                self.errCode = 0

    def closeEvent(
        self, event
    ):  # 重写closeevent，确保窗口关闭后子进程被销毁不会留下后台
        reply = QMessageBox.question(
            self,
            "串口助手beta版",
            "是否要退出程序？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if not usart_process == None:
                usart_process.terminate()  # 变成僵尸进程
                usart_process.join()  # 进程完全退出
            event.accept()
            os._exit(0)
        else:
            event.ignore()

    def com_reflash(self):
        working_com_check = 0
        global working_com
        self.combuf = Get_Com_List()  # 获取串口列表
        if self.combuf != self.COM_List:
            self.COM_List = self.combuf
            self.Com_Port.clear()  # 清除串口列表显示内容

            if len(self.COM_List) > 0:
                for i in range(0, len(self.COM_List)):  # 将列表导入到下拉框
                    self.Com_Port.addItem(self.COM_List[i].name)

                    if working_com != None:
                        if working_com == self.COM_List[i].name:
                            working_com_check = 1

                        if working_com_check == 0 and i == (len(self.COM_List) - 1):
                            self.close_com()
                            self.Open_Com.setEnabled(True)
                            # QMessageBox.warning(None, "警告", "选择的串口已不存在！！！", QMessageBox.Ok)
                            self.errCode = com_err_code.COM_OPEN_ERR
                            self.comErr.update(self.errCode)
            else:
                if working_com != None:
                    self.close_com()
                    self.Open_Com.setEnabled(True)
                    # QMessageBox.warning(None, "警告", "选择的串口已不存在！！！", QMessageBox.Ok)
                    self.errCode = com_err_code.COM_OPEN_ERR
                    self.comErr.update(self.errCode)

    def close_com(self):
        global Com_Open_Flag, working_com
        Com_Open_Flag = com_state.CLOSE
        working_com = None
        _1000msTimer.pause()
        clear(heartbeat)
        if self.send_auto.isChecked():
            auto_send_timer.pause()
            self.send_auto.setChecked(False)  # 取消勾选自动发送
            self.send_freq.setEnabled(True)  # 允许发送时间间隔设置

        self.start_update_click.setEnabled(False)
        self.send_auto.setCheckable(
            False
        )  # 不允许自动发送按钮勾选  每次关闭串口必须禁止
        self.Send_Data.setEnabled(False)  # 禁止发送按钮
        serial_cfg.put(com_state.CLOSE)
        self.Com_Band.setEnabled(True)  # 串口号和波特率变为可选择
        self.Com_Port.setEnabled(True)
        usart_process.join()  # 需加入.join(),等待串口发送和接收进程结束以及数据队列清空
        self.Open_Com.setText("打开串口")

    # 槽函数
    def send_auto_click(self):
        if self.send_auto.isChecked():
            print("定时发送打开")
            data = self.send_freq.text()
            if len(data) > 0:
                self.send_freq.setEnabled(False)  # 自动发送勾选后发送时间间隔不能修改
                autoSendTime = int(data)

                if autoSendTime == 0:
                    self.send_auto.setChecked(False)  # 取消勾选自动发送
                    self.send_freq.setEnabled(True)  # 解锁自动发送时间输入
                    # QMessageBox.warning(None, "警告", "发送时间间隔不能为零！！！", QMessageBox.Ok)
                    self.errCode = com_err_code.AUTO_SEND_TIME_SET_ERR
                    self.comErr.update(self.errCode)
                    return

                auto_send_timer.change(self.send_data_click, autoSendTime)
                auto_send_timer.start()
            else:
                self.send_auto.setChecked(False)  # 取消勾选自动发送
                print("定时发送关闭")
                # QMessageBox.warning(None, "警告", "请设置发送时间间隔！！！", QMessageBox.Ok)
                self.errCode = com_err_code.AUTO_SEND_TIME_NONE_ERR
                self.comErr.update(self.errCode)

        else:
            if Com_Open_Flag == com_state.CLOSE:
                # QMessageBox.warning(None, "警告", "只允许连接后开启！！！", QMessageBox.Ok)
                self.errCode = com_err_code.AUTO_SEND_OPEN_ERR
                self.comErr.update(self.errCode)
            try:
                auto_send_timer.pause()
            except:
                {}

            self.send_freq.setEnabled(True)  # 解锁自动发送时间输入
            print("定时发送关闭")

    # 串口按钮点击槽函数
    def open_com_click(self):
        if not self.com_thread.is_alive():
            self.Open_Com.setEnabled(False)
            self.com_thread = Thread(target=self.com_conctrl)
            self.com_thread.start()

    def com_conctrl(self):
        global custom_serial  # 全局变量，需要加global
        global Com_Open_Flag, working_com
        global usart_process, serial_cfg, rx_data, tx_data

        if self.Open_Com.text() == "打开串口":
            print("点击了打开串口按钮")
            comPort = self.Com_Port.currentText()
            comBand = int(self.Com_Band.currentText())
            cfg_list = [comPort, comBand]
            # serial_cfg = Manager().list(range(2))
            serial_cfg.put(cfg_list)
            usart_process = Process(
                target=usart_setting,
                args=(
                    serial_cfg,
                    usart_workState,
                    rx_data,
                    tx_data,
                    heartbeat,
                    subPkg_timeout,
                    cmdrxQueue,
                    File_Process_Flag,
                ),
            )
            usart_process.daemon = True
            usart_process.start()
            Com_Open_Flag = usart_workState.get(block=True, timeout=10)
            if Com_Open_Flag == com_state.OPEN:
                working_com = comPort
                self.send_auto.setCheckable(True)  # 允许自动发送按钮勾选
                self.Open_Com.setText("关闭串口")
                self.Send_Data.setEnabled(True)
                self.start_update_click.setEnabled(True)
                self.Com_Band.setEnabled(False)  # 串口号和波特率变为不可选择
                self.Com_Port.setEnabled(False)
                deal_rec_thread = Thread(target=self.recieve_data)
                check_subprocess_thread = Thread(target=self.check_subprocess)
                deal_rec_thread.daemon = True
                deal_rec_thread.start()
                _1000msTimer.start()
                check_subprocess_thread.start()
            else:
                # QMessageBox.warning(None, "警告", "串口被占用或不存在！！！", QMessageBox.Ok)
                self.errCode = com_err_code.COM_OPEN_ERR
                self.comErr.update(self.errCode)

        else:
            print("点击了关闭串口按钮")
            self.close_com()

        self.Open_Com.setEnabled(True)

    def check_subprocess(self):
        global Com_Open_Flag, working_com
        while True:
            if Com_Open_Flag == com_state.OPEN and usart_process.is_alive() == False:
                Com_Open_Flag = com_state.CLOSE
                working_com = None
                _1000msTimer.pause()
                clear(heartbeat)
                if self.send_auto.isChecked():
                    auto_send_timer.pause()
                    self.send_auto.setChecked(False)  # 取消勾选自动发送
                    self.send_freq.setEnabled(True)  # 允许发送时间间隔设置

                self.start_update_click.setEnabled(False)
                self.send_auto.setCheckable(
                    False
                )  # 不允许自动发送按钮勾选  每次关闭串口必须禁止
                self.Send_Data.setEnabled(False)  # 禁止发送按钮
                self.Com_Band.setEnabled(True)  # 串口号和波特率变为可选择
                self.Com_Port.setEnabled(True)
                self.Open_Com.setText("打开串口")
                break
            elif Com_Open_Flag == com_state.CLOSE:
                break

            time.sleep(0.001)

    def recieve_data(self):
        global rx_data

        while not Com_Open_Flag == com_state.CLOSE:
            if rx_data.empty() == False:
                data = rx_data.get()
                self.recv_len += len(data)-1
                self.recv_count_update.update()
                self.Set_Display_DataRcv(data)
            else:
                time.sleep(0.001)  # 降低cpu占用

    # 槽函数
    def send_data_click(self):
        if Com_Open_Flag == com_state.OPEN:
            if not self.send_thread.is_alive():
                self.send_thread = Thread(target=self.send_data_process)
                self.send_thread.start()


    def send_data_process(self):
        if (
            Com_Open_Flag == com_state.OPEN
            and not self.send_file_thread.is_alive() == True
        ):
            Data_Need_Send = self.Send_Data_Display.toPlainText()
            if len(Data_Need_Send) > 0:
                if self.sendHex.isChecked():
                    Data_Need_Send = Data_Need_Send.replace(" ", "")  # 删除空格
                    if len(Data_Need_Send) / 2 > 1024:
                        if self.send_auto.isChecked():
                            auto_send_timer.pause()
                            self.send_auto.setChecked(False)  # 取消勾选自动发送
                            self.send_freq.setEnabled(True)  # 允许发送时间间隔设置

                        if self.errCode == 0:
                            self.errCode = com_err_code.DATA_LEN_OVERRANGE_ERR
                            self.comErr.update(self.errCode)

                        return

                    try:
                        Data_Need_Send = bytes.fromhex(Data_Need_Send)
                        tx_data.put(Data_Need_Send)
                        timeStr = Time_get.get_strTime()

                        send_fail = 0
                        try:
                            if (
                                usart_process.is_alive() == False
                                or Com_Open_Flag == com_state.CLOSE
                                or send_fail == usart_workState.get(timeout=3)
                            ):  # 等待一帧发送完毕，超时一秒
                                print("发送失败")
                                return
                        except:
                            print("发送超时")
                            return

                        self.send_len += len(Data_Need_Send)
                        self.send_count_update.update()

                        if self.recHexShow.isChecked():
                            show_str = (
                                " ".join([hex(x)[2:].zfill(2) for x in Data_Need_Send])
                            ).upper()
                        else:
                            show_str = Data_Need_Send.decode(
                                encoding=self.now_enco_form, errors="replace"
                            )

                        show_str = "[" + timeStr + "]" + "发→◇" + show_str + "\n"
                        self.ui_update.update(show_str)

                        if self.SaveDataCheck.isChecked() and self.savedatafile != None:
                            self.savedatafile.write(show_str + "\n")

                    except:
                        if self.send_auto.isChecked():
                            auto_send_timer.pause()  # 自动发送定时器关闭
                            self.send_auto.setChecked(False)  # 取消勾选自动发送
                            self.send_freq.setEnabled(True)  # 允许发送时间间隔设置

                        # QMessageBox.warning(None, "警告", "待发送数据格式错误！！！", QMessageBox.Ok)
                        self.errCode = com_err_code.SEND_DATA_FORMAT_ERR
                        self.comErr.update(self.errCode)

                else:
                    show_str = Data_Need_Send.encode(self.now_enco_form).hex()
                    if len(show_str) / 2 > 1024:
                        if self.send_auto.isChecked():
                            auto_send_timer.pause()
                            self.send_auto.setChecked(False)  # 取消勾选自动发送
                            self.send_freq.setEnabled(True)  # 允许发送时间间隔设置

                        if self.errCode == 0:
                            self.errCode = com_err_code.DATA_LEN_OVERRANGE_ERR
                            self.comErr.update(self.errCode)

                        return

                    tx_data.put(Data_Need_Send.encode(self.now_enco_form))  # 发送
                    timeStr = Time_get.get_strTime()

                    send_fail = 0
                    try:
                        if (
                            usart_process.is_alive() == False
                            or Com_Open_Flag == com_state.CLOSE
                            or send_fail == usart_workState.get(timeout=3)
                        ):  # 等待一帧发送完毕
                            print("发送失败")
                            return
                    except:
                        print("发送超时")
                        return

                    self.send_len += len(Data_Need_Send.encode(self.now_enco_form))
                    self.send_count_update.update()

                    if self.recHexShow.isChecked():
                        show_str = (
                            " ".join(
                                [
                                    show_str[i : i + 2]
                                    for i in range(0, len(show_str), 2)
                                ]
                            )
                        ).upper()
                    else:
                        show_str = Data_Need_Send

                    show_str = "[" + timeStr + "]" + "发→◇" + show_str + "\n"
                    self.ui_update.update(show_str)

                    if self.SaveDataCheck.isChecked() and self.savedatafile != None:
                        self.savedatafile.write(show_str + "\n")

    def Set_Display_DataRcv(self, Data):
        timeStr = Data[0]
        Data.pop(0)
        if self.recHexShow.isChecked():
            show_str = (" ".join([hex(x)[2:].zfill(2) for x in Data])).upper()
        else:
            show_str = bytes(Data).decode(encoding=self.now_enco_form, errors="replace")

        show_str = "[" + timeStr + "]" + "收←◆" + show_str + "\n"
        self.ui_update.update(show_str)

        if self.SaveDataCheck.isChecked() and self.savedatafile != None:
            self.savedatafile.write(show_str + "\n")



