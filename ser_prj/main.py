import sys,os
from serial import Serial
from serial.tools import list_ports
from threading import Thread,Event
from PyQt5.QtWidgets import QApplication,QMainWindow,QMessageBox,QFileDialog
from untitled_ui import Ui_MainWindow
from PyQt5.QtCore import Qt,pyqtSignal,QObject,QThread
import multiprocessing
from multiprocessing import Pool,Process,Value,Array,Manager,Queue
from enum import IntEnum
import time
from datetime import datetime
from PyQt5.QtGui import QTextCursor,QIntValidator
from myTimer import msTimer

#自定义信号量       
class ui_show(QObject):
  update_signal = pyqtSignal(str)
 
  def __init__(self):
    QObject.__init__(self)
 
  def update(self,data):
    self.update_signal.emit(data)


class err_code_check(QObject):
  update_signal = pyqtSignal(int)
 
  def __init__(self):
    QObject.__init__(self)
 
  def update(self,index):
    self.update_signal.emit(index)

 
class state_check(QObject):
  update_signal = pyqtSignal()
 
  def __init__(self):
    QObject.__init__(self)
 
  def update(self):
    self.update_signal.emit()



class WorkThread(QThread):

    def __int__(self):
        # 初始化函数
        super().__init__()\

    def run(self):
      {}


class com_err_code(IntEnum):
  AUTO_SEND_TIME_SET_ERR = 0
  AUTO_SEND_TIME_NONE_ERR = 1
  AUTO_SEND_OPEN_ERR = 2
  COM_OPEN_ERR = 3
  SEND_DATA_FORMAT_ERR = 4

    
 

class com_state(IntEnum):
  CLOSE = 0
  OPEN = 1


#父进程全局变量
Com_Open_Flag = com_state.CLOSE  # 串口打开标志
custom_serial = Serial
usart_process = None
usart_workState =Queue()
serial_cfg = Queue()
usart_data = Queue()
rx_data = Queue()
tx_data = Queue()
comState = Value('i',com_state.CLOSE) 
comListTimer = msTimer(None,0)
auto_send_timer = msTimer(None,0)
working_com = None


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
  while not recClose_event.is_set(): 

    data = sSerial.read_all()
    if len(data)>0:
      rx_data.put(data)
    else:
      time.sleep(0.001)
      


def send_deal(sendClose_event,usart_workState,tx_data):
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
      time.sleep(0.001)  #降低cpu占用率



# 进行串口配置
def usart_setting(serial_cfg,usart_workState,rx_data,tx_data):
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
    send_thread = Thread(target=send_deal,args=(sendClose_event,usart_workState,tx_data))
    rec_thread.start()
    send_thread.start()
    usart_workState.put(com_state.OPEN)
    while True:
      if serial_cfg.get() == com_state.CLOSE:
        print("串口关闭")
        recClose_event.set()
        sendClose_event.set()
        rec_thread.join()
        send_thread.join()
        clear(rx_data)
        clear(tx_data)
        sSerial.close()
        break  
         

        
 # 获取串口列表
def Get_Com_List():
  return list(list_ports.comports()) 
  
  
  
def get_strTime():
  curr_time = datetime.now()
  hour = curr_time.hour
  minute = curr_time.minute
  second = curr_time.second
  
  if hour < 10:
    strHour = '0' + str(hour)
  else:
    strHour = str(hour)
      
  if minute < 10:
    strMinute = '0' + str(minute)
  else:
    strMinute = str(minute)
    
  if second < 10:
    strSecond = '0' + str(second)
  else:
    strSecond = str(second)
    
  microsecond = str(curr_time.microsecond)
  
  if len(microsecond) == 3:
    microsecond = "000"
  elif len(microsecond) == 4:
    microsecond = '00' + microsecond[:1]
  elif len(microsecond) == 5:
    microsecond = "0" + microsecond[:2]
  else:
    microsecond = microsecond[:3]
    
  timestr = strHour + ':' + strMinute + ':' + strSecond + '.' + microsecond
  
  return timestr


 #字节串转整形列表
def bytesrialtoarray(msg):
    data = []
    buf = [hex(x) for x in bytes(msg)]
    for i in range(len(buf)):
        data.append(int(buf[i],16))
        
    return data 
  

class Mywindow(QMainWindow, Ui_MainWindow):
  def __init__(self):
    band = ["9600","19200","115200"]
    super().__init__()
    
    self.send_thread = Thread(target=self.send_data_process)

    self.now_enco_form = "UTF-8"
    self.file_data_buf = list()
    
    self.ui_update = ui_show()
    self.ui_update.update_signal.connect(self.ui_show_refresh)

    self.comErr = err_code_check()
    self.comErr.update_signal.connect(self.err_code_warning)

    self.setupUi(self)

    
    # 创建一个整数验证器
    validator = QIntValidator()
    # 设置验证器的范围，这里可以设置允许的最小值和最大值
    validator.setRange(0, 999999)  #定时发送范围 单位毫秒
    # 设置验证器到 send_freq 中
    self.send_freq.setValidator(validator)
 
    self.ComReflash.clicked.connect(self.com_reflash)
    self.combuf = 0
    self.COM_List = 0
    
    self.com_thread = Thread(target=self.com_conctrl)


    self.com_reflash()
    comListTimer.change(self.com_reflash,3000)
    comListTimer.start()

    for i in range(0,len(band)):
      self.Com_Band.addItem(band[i])

  def open_file(self):
    fname = QFileDialog.getOpenFileName(self, '打开文件', '/')  # filter='*.txt'
    if fname[0]:
      with  open(fname[0], 'r') as f:
        self.file_selected.clear()
        self.file_selected.insertPlainText(fname[0])
        self.file_data_buf = f.read()
        print("转化前数据类型：",type(self.file_data_buf))
        self.file_data_buf = self.file_data_buf.encode(self.now_enco_form)
        print("数据类型：",type(self.file_data_buf))
        # print("数据：",self.file_data_buf)
  

  def send_file(self):
    if len(self.file_data_buf) > 0:
      tx_data.put(self.file_data_buf)
      send_fail = 0
      try:
        if send_fail == usart_workState.get(timeout = 5):  #等待一帧发送完毕，超时一秒 
          print("发送失败")
          return      
      except:
        print("发送超时")
        return
      self.file_selected.clear()
      self.file_data_buf = list()
      

  #ui刷新槽函数
  def ui_show_refresh(self,data):
    self.Data_Display.insertPlainText(data)
    


  def switch_encodingFormat(self):
    if self.encodingFormat.text() == "UTF-8":
      self.now_enco_form = "GBK"
      self.encodingFormat.setText("GBK")
    else:
      self.now_enco_form = "UTF-8"
      self.encodingFormat.setText("UTF-8")


  def err_code_warning(self,index):
    match index:
      case com_err_code.AUTO_SEND_TIME_SET_ERR:
        QMessageBox.warning(None, "警告", "发送时间间隔不能为零！！！", QMessageBox.Ok)

      case com_err_code.AUTO_SEND_TIME_NONE_ERR:
        QMessageBox.warning(None, "警告", "请设置发送时间间隔！！！", QMessageBox.Ok)

      case com_err_code.AUTO_SEND_OPEN_ERR:
        QMessageBox.warning(None, "警告", "只允许连接后开启！！！", QMessageBox.Ok)

      case com_err_code.COM_OPEN_ERR:
        QMessageBox.warning(None, "警告", "串口被占用或不存在等其他情况！！！", QMessageBox.Ok)
   
      case com_err_code.SEND_DATA_FORMAT_ERR:
        QMessageBox.warning(None, "警告", "待发送数据格式错误！！！", QMessageBox.Ok)

      
  
  def closeEvent(self,event):   #重写closeevent，确保窗口关闭后子进程被销毁不会留下后台         
    reply = QMessageBox.question(self,'串口助手beta版',"是否要退出程序？",QMessageBox.Yes | QMessageBox.No,QMessageBox.No)
    if reply == QMessageBox.Yes:
      if not usart_process == None:
        usart_process.terminate()  #变成僵尸进程
        usart_process.join()       #进程完全退出
      event.accept()
      os._exit(0)
    else:
      event.ignore()

  
  def com_reflash(self):
    working_com_check = 0
    global Com_Open_Flag,working_com
    self.combuf = Get_Com_List()  # 获取串口列表
    if not  self.combuf == self.COM_List:
      self.COM_List = self.combuf
      self.Com_Port.clear()           #清除串口列表显示内容
      for i in range(0, len(self.COM_List)):  # 将列表导入到下拉框
        self.Com_Port.addItem(self.COM_List[i].name)

        if not working_com == None:
        
          if working_com == self.COM_List[i].name:
             working_com_check = 1

          if working_com_check == 0 and i == (len(self.COM_List) - 1):
            self.close_com()
            self.Open_Com.setEnabled(True)
            # QMessageBox.warning(None, "警告", "选择的串口已不存在！！！", QMessageBox.Ok)
            self.comErr.update(com_err_code.COM_OPEN_ERR)

  
  def close_com(self):
    global Com_Open_Flag,working_com
    Com_Open_Flag = com_state.CLOSE
    working_com = None
    if self.send_auto.isChecked():
      auto_send_timer.pause()
      self.send_auto.setChecked(False)  #取消勾选自动发送
      self.send_freq.setEnabled(True)   #允许发送时间间隔设置
        
    self.send_file_click.setEnabled(False)    
    self.send_auto.setCheckable(False) #不允许自动发送按钮勾选  每次关闭串口必须禁止  
    self.Send_Data.setEnabled(False)  #禁止发送按钮
    serial_cfg.put(com_state.CLOSE)
    self.Com_Band.setEnabled(True)  # 串口号和波特率变为可选择
    self.Com_Port.setEnabled(True)
    usart_process.join()  #需加入.join(),等待串口发送和接收进程结束以及数据队列清空
    self.Open_Com.setText("打开串口")

    
  
  #槽函数
  def send_auto_click(self):
    if self.send_auto.isChecked():
      print("定时发送打开")
      data = self.send_freq.text()
      if len(data) > 0:
        self.send_freq.setEnabled(False) #自动发送勾选后发送时间间隔不能修改
        autoSendTime = int(data)
        
        if autoSendTime == 0:
          self.send_auto.setChecked(False)  #取消勾选自动发送
          self.send_freq.setEnabled(True) #解锁自动发送时间输入
          # QMessageBox.warning(None, "警告", "发送时间间隔不能为零！！！", QMessageBox.Ok)
          self.comErr.update(com_err_code.AUTO_SEND_TIME_SET_ERR)
          return
        
        auto_send_timer.change(self.send_data_click,autoSendTime)
        auto_send_timer.start()
      else:
        self.send_auto.setChecked(False)  #取消勾选自动发送
        print("定时发送关闭")
        # QMessageBox.warning(None, "警告", "请设置发送时间间隔！！！", QMessageBox.Ok)
        self.comErr.update(com_err_code.AUTO_SEND_TIME_NONE_ERR)
      
    else:
      if Com_Open_Flag == com_state.CLOSE:
        # QMessageBox.warning(None, "警告", "只允许连接后开启！！！", QMessageBox.Ok)
        self.comErr.update(com_err_code.AUTO_SEND_OPEN_ERR)
      try:
        auto_send_timer.pause()
      except:
        {}
          
      self.send_freq.setEnabled(True) #解锁自动发送时间输入
      print("定时发送关闭")
     
  
  #串口按钮点击槽函数
  def open_com_click(self):    
    if not self.com_thread.is_alive():
      self.Open_Com.setEnabled(False)
      self.com_thread = Thread(target=self.com_conctrl)
      self.com_thread.start()
      
  
  def com_conctrl(self):
    global custom_serial  # 全局变量，需要加global
    global Com_Open_Flag,working_com
    global usart_process,serial_cfg,rx_data,tx_data
    
    if self.Open_Com.text() == "打开串口":
      print("点击了打开串口按钮")
      comPort = self.Com_Port.currentText()
      comBand = int(self.Com_Band.currentText())
      cfg_list = [comPort,comBand]
      # serial_cfg = Manager().list(range(2))
      serial_cfg.put(cfg_list)
      usart_process = Process(target=usart_setting,args=(serial_cfg,usart_workState,rx_data,tx_data))
      usart_process.daemon = True
      usart_process.start()
      Com_Open_Flag = usart_workState.get(block=True,timeout=3)
      if Com_Open_Flag == com_state.OPEN:
        working_com = comPort
        self.send_auto.setCheckable(True)   #允许自动发送按钮勾选
        self.Open_Com.setText("关闭串口")
        self.Send_Data.setEnabled(True)
        self.send_file_click.setEnabled(True)
        self.Com_Band.setEnabled(False)  # 串口号和波特率变为不可选择
        self.Com_Port.setEnabled(False)
        deal_rec_thread =  Thread(target = self.recieve_data)
        deal_rec_thread.daemon = True
        deal_rec_thread.start()
      else:
        # QMessageBox.warning(None, "警告", "串口被占用或不存在！！！", QMessageBox.Ok)
        self.comErr.update(com_err_code.COM_OPEN_ERR)
        
    else:
      print("点击了关闭串口按钮")
      self.close_com()
       
    self.Open_Com.setEnabled(True)
   

  def recieve_data(self):
    global rx_data

    while not Com_Open_Flag == com_state.CLOSE:
  
      if rx_data.empty() == False:
        data = rx_data.get()
        self.Set_Display_Data(data)
        
      else:
        time.sleep(0.001)  #降低cpu占用


  #槽函数
  def drag_scroll(self):
    self.Data_Display.moveCursor(QTextCursor.End)  #数据刷新滚动条自动向下滚动


  #槽函数
  def send_data_click(self):
    if Com_Open_Flag == com_state.OPEN:
      if not self.send_thread.is_alive():
        self.send_thread = Thread(target=self.send_data_process)
        self.send_thread.start()


  def send_data_process(self):
    if Com_Open_Flag == com_state.OPEN:
      Data_Need_Send = self.Send_Data_Display.toPlainText()
      dlen = len(Data_Need_Send)
      if dlen>0:    
        if self.sendHex.isChecked():        
          Data_Need_Send = Data_Need_Send.replace(" ", "")  # 删除空格           
          try:
            Data_Need_Send = bytes.fromhex(Data_Need_Send)
            Data_T =  bytesrialtoarray(Data_Need_Send)
            tx_data.put(Data_T)
            timeStr = get_strTime()

            send_fail = 0
            try:
              if send_fail == usart_workState.get(timeout = 1):  #等待一帧发送完毕，超时一秒 
                print("发送失败")
                return      
            except:
              print("发送超时")
              return
                 
            if self.recHexShow.isChecked():
              show_str = (' '.join([hex(x)[2:].zfill(2) for x in Data_Need_Send])).upper()
            else:
              try:
                show_str = str(Data_Need_Send, encoding=self.now_enco_form)
              except:
                show_str = (''.join('?' for x in Data_Need_Send))
              
            show_str = '[' + timeStr + ']' + "发→◇" + show_str + '\n'
            self.ui_update.update(show_str)
            
          except:
            if self.send_auto.isChecked():
              auto_send_timer.pause()           #自动发送定时器关闭
              self.send_auto.setChecked(False)  #取消勾选自动发送 
              self.send_freq.setEnabled(True)   #允许发送时间间隔设置
               
            # QMessageBox.warning(None, "警告", "待发送数据格式错误！！！", QMessageBox.Ok)
            self.comErr.update(com_err_code.SEND_DATA_FORMAT_ERR)
                       
        else:
          tx_data.put(Data_Need_Send.encode(self.now_enco_form))  #发送
          timeStr = get_strTime()

          send_fail = 0
          try:
            if send_fail == usart_workState.get(timeout = 1):  #等待一帧发送完毕 
              print("发送失败")
              return      
          except:
            print("发送超时")
            return
        
          if self.recHexShow.isChecked():
            show_str = Data_Need_Send.encode(self.now_enco_form).hex()
            show_str = bytes.fromhex(show_str)
            show_str = (' '.join([hex(x)[2:].zfill(2) for x in show_str])).upper()
          else:
            show_str = Data_Need_Send
                         
          show_str = '[' + timeStr + ']' + "发→◇" + show_str + '\n'       
          self.ui_update.update(show_str)
            
        
          
  def Set_Display_Data(self, Data):
    if self.recHexShow.isChecked():
      show_str = (' '.join([hex(x)[2:].zfill(2) for x in Data])).upper()
    else:
      try:
        show_str = str(Data, encoding=self.now_enco_form)
      except:
        show_str = (''.join('?' for x in Data))
    
    timeStr = get_strTime()
    show_str = '[' + timeStr + ']' + "收←◆" + show_str + '\n'
    self.ui_update.update(show_str)


def ui_process():
  QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)  #解决比例问题
  app = QApplication(sys.argv)
  window = Mywindow()
  window.show()
  sys.exit(app.exec_())
  


 
if __name__ == '__main__':
  multiprocessing.freeze_support()  #多进程加这句，不然程序打包后不能正常运行
  ui_process()
  


