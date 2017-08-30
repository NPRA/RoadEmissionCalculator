from PyQt4.QtCore import *
import time
from EmissionCalculatorLib import EmissionCalculatorLib

class EmissionsThread(QThread):
    calculationFinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

        self.emission_calculator = EmissionCalculatorLib()

    def set_calculator_lib(self, calculatorLib):
        self.emission_calculator = calculatorLib

    def __get_emissions(self):
        self.emission_calculator.calculate_emissions()

    def run(self):
        self.__get_emissions()
        self.calculationFinished.emit()
