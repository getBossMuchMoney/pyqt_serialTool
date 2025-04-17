from PyQt5.QtWidgets import *
from UartDebug import UartWindow,usart_process
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

    def closeEvent(
        self, event
    ):  # 重写closeevent，确保窗口关闭后子进程被销毁不会留下后台
        reply = QMessageBox.question(
            self,
            "调试助手beta版",
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