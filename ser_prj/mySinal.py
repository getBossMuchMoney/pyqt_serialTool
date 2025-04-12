from PyQt5.QtCore import  pyqtSignal, QObject



# 自定义信号量
class ui_show(QObject):
    update_signal = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)

    def update(self, data):
        self.update_signal.emit(data)


class number_check(QObject):
    update_signal = pyqtSignal(int)

    def __init__(self):
        QObject.__init__(self)

    def update(self, index):
        self.update_signal.emit(index)


class state_check(QObject):
    update_signal = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)

    def update(self):
        self.update_signal.emit()