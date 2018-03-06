from builtins import range
import math
# from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QPalette, QPainter, QBrush, QColor, QPen
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtCore import Qt


class Overlay(QWidget):
    '''Overlay is a class which show loading gif.'''

    def __init__(self, parent=None):

        QWidget.__init__(self, parent)
        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(event.rect(), QBrush(QColor(255, 255, 255, 127)))
        painter.setPen(QPen(Qt.NoPen))

        for i in range(6):
            if (self.counter / 5) % 6 == i:
                painter.setBrush(QBrush(QColor(127 + (self.counter % 5) * 32, 127, 127)))
            else:
                painter.setBrush(QBrush(QColor(127, 127, 127)))
            painter.drawEllipse(
                self.width() / 2 + 30 * math.cos(2 * math.pi * i / 6.0) - 10,
                self.height() / 2 + 30 * math.sin(2 * math.pi * i / 6.0) - 10,
                20, 20)

        painter.end()

    def showEvent(self, event):
        self.timer = self.startTimer(50)
        self.counter = 0

    def timerEvent(self, event):

        self.counter += 1
        self.update()
        # if self.counter == 60:
        #     self.killTimer(self.timer)
        #     self.hide()

    def hideEvent(self, event):
        self.killTimer(self.timer)
        self.hide()

    def resizeEvent(self, event):
        self.resize(event.size())
        event.accept()
