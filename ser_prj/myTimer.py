from ctypes import *
from typing import Callable
#高精度定时器，调用外部动态库
#使用此类需要在程序线程开启前初始化好，之后start就可以开启，在线程内初始化无效，可能因为调用外部动态库
    
#msTimer不需要定义回调函数，直接传目标函数地址
class msTimer():
    def __init__(self,func,msec):
        self.func = func 
        self.msec = msec
        self._winmm = windll.LoadLibrary('winmm.dll')
        try:
          self._cb = CFUNCTYPE(c_void_p)(self.func)
        except:
          self._cb = CFUNCTYPE(c_void_p)(self.err_callback)
          
    def err_callback(self):
        print("函数地址无效")  
        
    def change(self,func,msec):  #start之前改变func,msec
        self.func = func
        self.msec = msec
        self._cb = CFUNCTYPE(c_void_p)(self.func)
               
    def start(self):
        self._timerId = self._winmm.timeSetEvent(self.msec,1,self._cb,0,1)
        
    def pause(self):
        self._winmm.timeKillEvent(self._timerId)
       
    def resume(self):
        self._winmm.timeSetEvent(self.msec,1,self._cb,0,1)
        
#msTimer_Call需要重写回调函数 
#使用举例:
# _200msTimer = msTimer_Call(200)
# @_200msTimer.msTimer_callback()
# def mcallback():
#     print("测试回调")


      
class msTimer_Call(msTimer):
    def __init__(self, msec):
        super().__init__(None,msec)  #继承父类，注意__init__需要传入父类的参数
        self._callbacks:Callable
        self._cb = CFUNCTYPE(c_void_p)(self._invoke_callbacks)
               
    def _invoke_callbacks(self):
        # for callback in self._callbacks:
        #     callback()
        self._callbacks()
              
    def msTimer_callback(self):     
        # def decorator(func: Callable):
        #     self._callbacks.append(func)
        #     return func 
        # return decorator
        def decorator(func: Callable):
            self._callbacks = func
            return func 
        return decorator
        
        
