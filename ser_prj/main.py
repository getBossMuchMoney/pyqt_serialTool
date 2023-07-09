import sys
from serial import Serial
from serial.tools import list_ports
from threading import Thread,Event
from PyQt5.QtWidgets import QApplication,QMainWindow
from untitled_ui import Ui_MainWindow
from PyQt5.QtCore import Qt,pyqtSignal,QObject
import multiprocessing
from multiprocessing import Pool,Process,Value,Array,Manager,Queue
from enum import IntEnum
import time


#自定义信号量
class UsartRec_UpdateLog(QObject):
    update_signal = pyqtSignal(bytes)
 
    def __init__(self):
        QObject.__init__(self)
 
    def update(self,data):
        self.update_signal.emit(data)
        


class com_state(IntEnum):
    CLOSE = 0
    OPEN = 1


#父进程全局变量
Com_Open_Flag = com_state.CLOSE  # 串口打开标志
custom_serial = Serial
usart_process = 0
usart_workState =Queue()
serial_cfg = Queue()
serial_ctr = Queue()
usart_data = Queue()
rx_data = Queue()
tx_data = Queue()
usart_recieve_check = UsartRec_UpdateLog()
comState = Value('i',com_state.CLOSE) 





#子进程全局变量
sSerial = 0
recClose_event = Event()
sendClose_event = Event()



def clear(q):
  while q.empty() == False:
    q.get_nowait()
 


#串口接收数据处理线程
def rec_deal(recClose_event,rx_data):
  global sSerial
  while True:
    if recClose_event.is_set():
      break
    data = sSerial.read_all()
    if len(data)>0:
      print("已收到数据：",data)
      rx_data.put(data)

    time.sleep(0.001)  #降低cpu占用率


def send_deal(sendClose_event,tx_data):
  global sSerial
  while True:
    if sendClose_event.is_set():
      break

    if tx_data.empty() == False:
      data = tx_data.get()
      sSerial.write(data)

    time.sleep(0.001)  #降低cpu占用率



# 进行串口配置
def usart_setting(serial_cfg,serial_ctr,usart_workState,rx_data,tx_data):
  global sSerial,recClose_event
  try:
    seriConf = serial_cfg.get(block=True)
    sSerial = Serial(seriConf[0],seriConf[1])
  except:
    usart_workState.put(com_state.CLOSE)
    print("串口配置失败")
    return
     
  if sSerial.isOpen() == True:
    print("串口打开成功")
    rec_thread = Thread(target=rec_deal,args=(recClose_event,rx_data))
    send_thread = Thread(target=send_deal,args=(sendClose_event,tx_data))
    rec_thread.start()
    send_thread.start()
    usart_workState.put(com_state.OPEN)
    while True:
      if serial_cfg.empty() == False:
        if serial_cfg.get(block = False) == com_state.CLOSE:
          print("串口关闭")
          recClose_event.set()
          sendClose_event.set()
          rec_thread.join()
          send_thread.join()
          clear(rx_data)
          clear(tx_data)
          sSerial.close()
          break  
      time.sleep(0.001)               

         

 # 获取串口列表
def Get_Com_List():
    return list(list_ports.comports()) 



class Mywindow(QMainWindow, Ui_MainWindow):
  def __init__(self):
    band = ["9600","19200","115200"]
    super().__init__()
    usart_recieve_check.update_signal.connect(self.Set_Display_Data)
    self.setupUi(self)
    self.Send_Data.setEnabled(False)
    COM_List = Get_Com_List()  # 获取串口列表
    for i in range(0, len(COM_List)):  # 将列表导入到下拉框
      self.Com_Port.addItem(COM_List[i].name)

    for i in range(0,len(band)):
      self.Com_Band.addItem(band[i])


  #槽函数
  def open_com_click(self):
    global custom_serial  # 全局变量，需要加global
    global Com_Open_Flag
    global usart_process,serial_cfg,serial_ctr,rx_data,tx_data
  
    if self.Open_Com.text() == "打开串口":
      print("点击了打开串口按钮")
      comPort = self.Com_Port.currentText()
      comBand = int(self.Com_Band.currentText())
      cfg_list = [comPort,comBand]
      # serial_cfg = Manager().list(range(2))
      serial_cfg.put(cfg_list)
      usart_process = Process(target=usart_setting,args=(serial_cfg,serial_ctr,usart_workState,rx_data,tx_data))
      usart_process.start()
      Com_Open_Flag = usart_workState.get(block=True,timeout=3)
      if Com_Open_Flag == com_state.OPEN:     
        self.Open_Com.setText("关闭串口")
        self.Send_Data.setEnabled(True)
        self.Com_Band.setEnabled(False)  # 串口号和波特率变为不可选择
        self.Com_Port.setEnabled(False)
        Thread(target = self.recieve_data).start()  
    else:
      print("点击了关闭串口按钮")
      self.Send_Data.setEnabled(False)
      serial_cfg.put(com_state.CLOSE)
      Com_Open_Flag = com_state.CLOSE
      self.Open_Com.setText("打开串口")
      self.Com_Band.setEnabled(True)  # 串口号和波特率变为可选择
      self.Com_Port.setEnabled(True)
      usart_process.join()  #需加入.join(),等待串口发送和接收进程结束以及数据队列清空


  def recieve_data(self):
    global rx_data
    while True:
      if Com_Open_Flag == com_state.CLOSE:
          break;
      if rx_data.empty() == False:
        data = rx_data.get()
        usart_recieve_check.update(data)

      time.sleep(0.001)


  #槽函数
  def send_data_click(self):
     print("点击了发送数据按钮")
     Data_Need_Send = self.Send_Data_Display.toPlainText()
     dlen = len(Data_Need_Send)
     if dlen>0:      
      tx_data.put(Data_Need_Send.encode("gbk"))


  def Set_Display_Data(self, Data):
    
    show_str = (' '.join([hex(x)[2:].zfill(2) for x in Data]))
    # show_str = str(Data, encoding="utf-8")
    print("数据类型：",type(show_str))
    show_str = show_str + "\n"
    
    self.Data_Display.insertPlainText(show_str)




def ui_process():
  QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)  #解决比例问题
  app = QApplication(sys.argv)
  window = Mywindow()
  window.show()
  sys.exit(app.exec_())
   



if __name__ == '__main__':
  
  ui_process()
  


