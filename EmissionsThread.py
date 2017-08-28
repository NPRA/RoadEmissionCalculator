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
        # emission_calculator = EmissionCalculatorLib()
        # emission_calculator.emissionJson.set_type(self.vehicle_type)
        # emission_calculator.emissionJson.set_ssc_name(self.vehicle_ssc_name)
        # emission_calculator.emissionJson.set_subsegment(self.vehicle_subsegment)
        # emission_calculator.emissionJson.set_tec_name(self.vehicle_tec_name)
        # emission_calculator.emissionJson.set_load(self.vehicle_load)

        # emission_calculator.set_data(self.data_json)
        # print self.a
        self.emission_calculator.calculate_emissions()
        # return self.emission_calculator.get_emissions_for_pollutant()

    def run(self):
        self.__get_emissions()
        self.calculationFinished.emit()
