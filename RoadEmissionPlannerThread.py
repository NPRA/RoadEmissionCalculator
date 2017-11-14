from PyQt4.QtCore import *


class RoadEmissionPlannerThread(QThread):
    plannerFinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        self.emission_planner = None

    def set_planner(self, planner):
        self.emission_planner = planner

    def _run_planner(self):
        self.emission_planner.run()

    def run(self):
        self._run_planner()
        self.plannerFinished.emit()
