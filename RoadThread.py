from PyQt4.QtCore import *
import time
# from EmissionCalculatorLib import EmissionCalculatorLib

class RoadThread(QThread):
    urlFinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        # self.emission_calculator = EmissionCalculatorLib()

    def set_calculator_lib(self, calculatorLib):
        self.emission_calculator = calculatorLib

    def __get_json_data(self):
        self.emission_calculator.get_json_from_url()

    def run(self):
        self.__get_json_data()
        self.urlFinished.emit()