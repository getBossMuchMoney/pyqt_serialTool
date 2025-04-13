from PyQt5.QtWidgets import *
from UartDebug import UartWindow
import multiprocessing
from PyQt5.QtCore import Qt, QThread, QCoreApplication
import sys, os
from CanDebug import CanWindow
from Ui_untitled import Ui_MainWindow

class Mywindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.MainUI = Ui_MainWindow()  # 创建 Ui_MainWindow 实例
        self.MainUI.setupUi(self)      # 设置 UI
        
         # 创建 UartWindow 实例
        self.uartDebug = UartWindow(self.MainUI)

        # 创建 CanWindow 实例
        self.canDebug = CanWindow(self.MainUI)



def ui_process():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)  # 解决比例问题
    app = QApplication(sys.argv)
    window = Mywindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    multiprocessing.freeze_support()  # 多进程加这句，不然程序打包后不能正常运行
    ui_process()