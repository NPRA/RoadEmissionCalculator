from PyQt4.QtCore import *
import time
from EmissionCalculatorLib import EmissionCalculatorLib

class RoadThread(QThread):
    urlFinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        # self.coord = ""
        # self.length = ""
        # self.height = ""
        # self.load = "0"

        self.emission_calculator = EmissionCalculatorLib()

    def set_calculator_lib(self, calculatorLib):
        self.emission_calculator = calculatorLib

    def __get_json_data(self):
        # emission_calculator = EmissionCalculatorLib()
        # emission_calculator.height = self.height
        # emission_calculator.length = self.length
        # emission_calculator.coordinates = self.coord
        # emission_calculator.emissionJson.load = self.load
        #
        # emission_calculator.get_json_from_url()
        #
        # return emission_calculator.get_json_data()
        self.emission_calculator.get_json_from_url()

    def run(self):
        self.__get_json_data()
        # res = paths + self.coord
        self.urlFinished.emit()
        # time.sleep(2)