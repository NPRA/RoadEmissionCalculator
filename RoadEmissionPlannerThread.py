from __future__ import print_function
# from PyQt4.QtCore import *
from qgis.PyQt.QtCore import QThread, pyqtSignal
from emission.exceptions import RouteError


class RoadEmissionPlannerThread(QThread):
    plannerFinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        self.emission_planner = None

    def set_planner(self, planner):
        self.emission_planner = planner

    def _run_planner(self):
        try:
            self.emission_planner._get_routes()
        except RouteError as err:
            print ("ioerror: {}".format(err))
            self._json_data = {}
            raise RouteError("IOError: {}".format(err))
        # except Exception:
        #     print

    def run(self):
        try:
            self._run_planner()
            self.plannerFinished.emit()
        except:
            print ("Caught an exception in thread ")
            self.plannerFinished.emit()