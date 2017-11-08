from PyQt4.QtCore import *
import emission


class RoadEmissionPlannerThread(QThread):
    plannerFinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        start = [271809.847394, 7039133.17755]
        stop = [265385.432115, 7031118.13344]
        # fuel_petrol = emission.vehicles.FuelTypes.PETROL
        # vehicle = emission.vehicles.Car(fuel_petrol)
        fuel_diesel = emission.vehicles.FuelTypes.DIESEL
        vehicle = emission.vehicles.Truck(fuel_diesel)

        self.emission_planner = emission.Planner(start, stop, vehicle)

    def set_planner(self, planner):
        self.emission_planner = planner

    def _run_planner(self):
        self.emission_planner.run()

    def run(self):
        self._run_planner()
        self.plannerFinished.emit()
