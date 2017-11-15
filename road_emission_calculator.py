# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RoadEmissionCalculator
                                 A QGIS plugin
 The plugin calculate emissons for selected roads.
                              -------------------
        begin                : 2017-08-08
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Statens Vegvesen
        email                : tomas.levin@vegvesen.no
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QVariant, QObject
from PyQt4.QtGui import QAction, QIcon, QColor, QWidget
from qgis.core import QGis, QgsCoordinateTransform, QgsRectangle, QgsPoint, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.gui import QgsRubberBand
from Overlay import Overlay

from qgis.core import QgsVectorLayer, QgsField, QgsMapLayerRegistry, QgsFeature, QgsGeometry

from copyLatLonTool import CopyLatLonTool
from settings import SettingsWidget
import sys
import pip
import os.path
import matplotlib.pyplot as plt

plugin_dir = os.path.dirname(__file__)
emissionCalculator_dir = os.path.join(plugin_dir, 'emission')
try:
    import emission
    from RoadEmissionPlannerThread import RoadEmissionPlannerThread
except:
    pip.main(['install', '--target=%s' % emissionCalculator_dir, 'emission'])
    if emissionCalculator_dir not in sys.path:
        sys.path.append(emissionCalculator_dir)
    import emission
    from RoadEmissionPlannerThread import RoadEmissionPlannerThread

# from PyQt4.QtCore import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from road_emission_calculator_dialog import RoadEmissionCalculatorDialog



class RoadEmissionCalculator:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.crossRb = QgsRubberBand(self.canvas, QGis.Line)
        self.crossRb.setColor(Qt.red)
        self.planner = emission
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        self.s = QSettings()
        self.enableUseOfGlobalCrs()
        self.oldValidation = ""
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'RoadEmissionCalculator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = RoadEmissionCalculatorDialog()

        # Declare instance attributes
        self.actions = []
        self.categories = []
        self.selected_category = []
        self.selected_fuel = []
        self.selected_segment = []
        self.selected_euro_std = []
        self.selected_mode = []
        # self.fuels = []
        # self.segments = []
        self.menu = self.tr(u'&Road Emission Calculator')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RoadEmissionCalculator')
        self.toolbar.setObjectName(u'RoadEmissionCalculator')

        # matplolib generate lines in color sequence: blue, green, red, cyan, magenta, yellow, black, white
        # same color schema will be use for proposal roads
        self.color_list = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255),
                           (255, 0, 255), (255, 255, 0), (0, 0, 0), (255, 255, 255)]

        self.dlg.btnAddStartPoint.clicked.connect(self.add_start_point)
        self.dlg.btnAddEndPoint.clicked.connect(self.add_end_point)
        self.dlg.btnRemoveStartPoint.clicked.connect(self.remove_start_point)
        self.dlg.btnRemoveEndPoint.clicked.connect(self.remove_end_point)

        self.dlg.widgetLoading.setShown(False)
        self.overlay = Overlay(self.dlg.widgetLoading)
        self.overlay.resize(700,445)
        self.overlay.hide()

        self.roadEmissionPlanner = RoadEmissionPlannerThread()
        self.roadEmissionPlanner.plannerFinished.connect(self.on_road_emission_planner_finished)

        self.dlg.btnGetEmissions.clicked.connect(self.on_road_emission_planner_start)
        self.dlg.cmbBoxVehicleType.currentIndexChanged.connect(self.set_fuels)
        self.dlg.cmbBoxFuelType.currentIndexChanged.connect(self.set_segments)
        self.dlg.cmbBoxSubsegment.currentIndexChanged.connect(self.set_euro_std)
        self.dlg.cmbBoxEuroStd.currentIndexChanged.connect(self.set_mode)
        self.dlg.cmbBoxMode.currentIndexChanged.connect(self.set_pollutants)

        self.dlg.checkBoxShowInGraph.clicked.connect(self.activate_cumulative)

        # init with default values
        self.dlg.lineEditLength.setText('12')
        self.dlg.lineEditHeight.setText('4.4')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('RoadEmissionCalculator', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        # self.dlg = RoadEmissionCalculatorDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/RoadEmissionCalculator/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.settingsDialog = SettingsWidget(self, self.iface, self.iface.mainWindow())
        self.mapTool = CopyLatLonTool(self.settingsDialog, self.iface, self.dlg)
        self.dlg.btnAddStartPoint.setIcon(QIcon(os.path.dirname(__file__) + "/images/pencil_64.png"))
        self.dlg.btnAddEndPoint.setIcon(QIcon(os.path.dirname(__file__) + "/images/pencil_64.png"))
        self.dlg.btnRemoveStartPoint.setIcon(QIcon(os.path.dirname(__file__) + "/images/trash_64.png"))
        self.dlg.btnRemoveEndPoint.setIcon(QIcon(os.path.dirname(__file__) + "/images/trash_64.png"))
        self.dlg.textEditSummary.setReadOnly(True)
        self.dlg.lineEditStartX.setReadOnly(True)
        self.dlg.lineEditStartY.setReadOnly(True)
        self.dlg.lineEditEndX.setReadOnly(True)
        self.dlg.lineEditEndY.setReadOnly(True)
        self.activate_cumulative()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Road Emission Calculator'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        self.canvas.unsetMapTool(self.mapTool)

    def set_vehicle_subsegment(self):
        self.dlg.cmbBoxSubsegment.clear()
        if self.dlg.cmbBoxVehicleType.currentText() == 'CAR':
            segments = emission.vehicles.Car.type
            self.dlg.cmbBoxSubsegment.addItems([list(d)[0] for d in segments])

    def set_vehicle_euro_std(self):

        self.dlg.cmbBoxEuroStd.clear()
        if self.dlg.cmbBoxVehicleType.currentText() == 'CAR':
            segments = emission.vehicles.Car.type
            self.dlg.cmbBoxEuroStd.addItems(list(filter(lambda y: y != None, [x.get(self.dlg.cmbBoxSubsegment.currentText()) for x in segments]))[0])

    def activate_cumulative(self):
        self.dlg.checkBoxCumulative.setEnabled(self.dlg.checkBoxShowInGraph.isChecked())

    def set_new_point(self, point_name):
        self.mapTool.point_name = point_name
        self.canvas.setMapTool(self.mapTool)

    def add_start_point(self):
        # only one start point can be in canvas/legend
        self.remove_start_point()
        self.set_new_point("Start_point")

    def add_end_point(self):
        # only one end point can be in canvas/legend
        self.remove_end_point()
        self.set_new_point("End_point")

    @staticmethod
    def remove_layer(id_name):
        lrs = QgsMapLayerRegistry.instance().mapLayers()
        for i in range(len(lrs.keys())):
            if id_name in lrs.keys()[i]:
                print (lrs.keys()[i])
                QgsMapLayerRegistry.instance().removeMapLayer(lrs.keys()[i])

    def remove_start_point(self):
        self.dlg.lineEditStartX.setText("")
        self.dlg.lineEditStartY.setText("")
        self.remove_layer("Start_point")

    def remove_end_point(self):
        self.dlg.lineEditEndX.setText("")
        self.dlg.lineEditEndY.setText("")
        self.remove_layer("End_point")

    'set new Layers to use the Project-CRS'

    def enableUseOfGlobalCrs(self):
        self.s = QSettings()
        self.oldValidation = str(self.s.value("/Projections/defaultBehaviour"))
        self.s.setValue("/Projections/defaultBehaviour", "useProject")

    'enable old settings again'

    def disableUseOfGlobalCrs(self):
        self.s.setValue("/Projections/defaultBehaviour", self.oldValidation)

    def on_road_emission_planner_start(self):
        self.dlg.widgetLoading.setShown(True)
        start = [float(self.dlg.lineEditStartX.text()), float(self.dlg.lineEditStartY.text())]
        stop = [float(self.dlg.lineEditEndX.text()), float(self.dlg.lineEditEndY.text())]
        fuel_diesel = emission.vehicles.FuelTypes.DIESEL

        # print ("Fuel diesel {}". format(fuel_diesel))
        # print ("Selected fuel {}").format(self.dlg.cmbBoxFuelType.currentText())
        vehicle = emission.vehicles.Vehicle

        type_category = emission.vehicles.Vehicle.get_type_for_category(self.dlg.cmbBoxVehicleType.currentText())
        if type_category == emission.vehicles.VehicleTypes.CAR:
            vehicle = emission.vehicles.Car()
        if type_category == emission.vehicles.VehicleTypes.BUS:
            vehicle = emission.vehicles.Bus()
            vehicle.length = self.dlg.lineEditLength.text()
            vehicle.height = self.dlg.lineEditHeight.text()
            vehicle.load = self.dlg.cmbBoxLoad.currentText()
        if type_category == emission.vehicles.VehicleTypes.TRUCK:
            vehicle = emission.vehicles.Truck()
            vehicle.length = self.dlg.lineEditLength.text()
            vehicle.height = self.dlg.lineEditHeight.text()
            vehicle.load = self.dlg.cmbBoxLoad.currentText()
        if type_category == emission.vehicles.VehicleTypes.LCATEGORY:
            vehicle = emission.vehicles.LCategory()
        if type_category == emission.vehicles.VehicleTypes.VAN:
            vehicle = emission.vehicles.Van()

        vehicle.fuel_type = self.dlg.cmbBoxFuelType.currentText()
        vehicle.segment = self.dlg.cmbBoxSubsegment.currentText()
        vehicle.euro_std = self.dlg.cmbBoxEuroStd.currentText()
        vehicle.mode = self.dlg.cmbBoxMode.currentText()

        self.planner = emission.Planner(start, stop, vehicle)

        if self.dlg.checkBoxCo.isEnabled() and self.dlg.checkBoxCo.isChecked():
            self.planner.add_pollutant(emission.PollutantTypes.CO)
        if self.dlg.checkBoxNox.isEnabled() and self.dlg.checkBoxNox.isChecked():
            self.planner.add_pollutant(emission.PollutantTypes.NOx)
        if self.dlg.checkBoxVoc.isEnabled() and self.dlg.checkBoxVoc.isChecked():
            self.planner.add_pollutant(emission.PollutantTypes.VOC)
        if self.dlg.checkBoxEc.isEnabled() and self.dlg.checkBoxEc.isChecked():
            self.planner.add_pollutant(emission.PollutantTypes.EC)
        if self.dlg.checkBoxPmExhaust.isEnabled() and self.dlg.checkBoxPmExhaust.isChecked():
            self.planner.add_pollutant(emission.PollutantTypes.PM_EXHAUST)
        if self.dlg.checkBoxCh4.isEnabled() and self.dlg.checkBoxCh4.isChecked():
            self.planner.add_pollutant(emission.PollutantTypes.CH4)

        self.overlay.show()
        self.roadEmissionPlanner.set_planner(self.planner)
        self.roadEmissionPlanner.start()

    def on_road_emission_planner_finished(self):
        self.overlay.hide()
        self.remove_layer("Route")
        self.road_emission_planner_finished()
        self.dlg.widgetLoading.setShown(False)

    def road_emission_planner_finished(self):
        self.dlg.textEditSummary.clear()
        routes = self.planner.routes
        pollutant_types = self.planner.pollutants.keys()
        if len(routes) > 0:
            for idx, route in enumerate(routes):
                self.dlg.textEditSummary.append("Route" + str(idx + 1) + ":")
                distance = route.distance / 1000
                hours, minutes = divmod(route.minutes, 60)
                hours = int(hours)
                minutes = int(minutes)
                self.dlg.textEditSummary.append(
                    "Length: " + str(distance) + " km, driving time: " + str(hours) + " hours and " + str(
                        minutes) + " minutes.")
                self.dlg.textEditSummary.append("")
                for pt in pollutant_types:
                    self.dlg.textEditSummary.append(("    {} = {}".format(pt, route.total_emission(pt))))

                self.dlg.textEditSummary.append("")
                self.dlg.textEditSummary.append("")

                ## create an empty memory layer
                vl = QgsVectorLayer("LineString", "Route" + str(idx + 1), "memory")
                ## define and add a field ID to memory layer "Route"
                provider = vl.dataProvider()
                provider.addAttributes([QgsField("ID", QVariant.Int)])
                ## create a new feature for the layer "Route"
                ft = QgsFeature()
                ## set the value 1 to the new field "ID"
                ft.setAttributes([1])
                line_points = []
                for i in range(len(route.path)):
                    # if j == 0:
                    if (i + 1) < len(route.path):
                        line_points.append(QgsPoint(route.path[i][0], route.path[i][1]))
                ## set the geometry defined from the point X: 50, Y: 100
                ft.setGeometry(QgsGeometry.fromPolyline(line_points))
                ## finally insert the feature
                provider.addFeatures([ft])

                ## set color
                symbols = vl.rendererV2().symbols()
                sym = symbols[0]
                if idx < (len(self.color_list) - 1):
                    color = self.color_list[idx]
                    sym.setColor(QColor.fromRgb(color[0], color[1], color[2]))
                sym.setWidth(2)

                ## add layer to the registry and over the map canvas
                QgsMapLayerRegistry.instance().addMapLayer(vl)

            ## Show pollutant results in graph
            if self.dlg.checkBoxShowInGraph.isChecked():
                fig = plt.figure()
                figs = []

                for idx, pt in enumerate(pollutant_types):
                    num_plots = 100 * len(routes[0].pollutants) + 10 + idx + 1
                    ax = fig.add_subplot(num_plots)
                    ax.set_title(pt)
                    ax.set_ylim(0, max(routes[0].pollutants[pt]) + 1)
                    figs.append(ax)

                for r in routes:
                    for idx, pt in enumerate(pollutant_types):
                        ax = figs[idx]
                        ax.plot(r.distances[0], r.pollutants[pt])

                ax = figs[-1]
                labels = ["Route " + str(i + 1) for i in range(len(routes))]
                pos = (len(figs) / 10.0) * (-1)
                ax.legend(labels, loc=(0, pos), ncol=len(routes))
                plt.show()


        else:
            # if "Fail" in self.emission_calculator.emission_summary:
            #     self.dlg.textEditSummary.append(self.emission_calculator.emission_summary["Fail"])
            #     self.dlg.textEditSummary.append("")
            # # self.dlg.textEditSummary.append("Sorry, for defined parameters no road is available.")
            # # self.dlg.textEditSummary.append("")
            pass

    def set_categories(self):
        self.categories = emission.session.query(emission.models.Category).all()
        self.dlg.cmbBoxVehicleType.addItems(list(map(lambda category: category.name, self.categories)))
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())

    def set_fuels(self):
        self.dlg.cmbBoxFuelType.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        if len(self.selected_category) > 0:
            filtred_fuels = emission.models.filter_parms(cat=self.selected_category[0])
            self.fuels = set(x.fuel for x in filtred_fuels)
            self.dlg.cmbBoxFuelType.addItems(list(map(lambda fuel: fuel.name, self.fuels)))

    def set_segments(self):
        self.dlg.cmbBoxSubsegment.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0:
            filtred_segments = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0])
            self.segments = set(x.segment for x in filtred_segments)
            self.dlg.cmbBoxSubsegment.addItems(list(map(lambda segment: str(segment.name), self.segments)))
            self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                       self.dlg.cmbBoxSubsegment.currentText())

    def set_euro_std(self):
        self.dlg.cmbBoxEuroStd.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments, self.dlg.cmbBoxSubsegment.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0:
            filtred_euro_stds = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0],segment=self.selected_segment[0])
            self.euro_stds = set(x.eurostd for x in filtred_euro_stds)
            self.dlg.cmbBoxEuroStd.addItems(list(map(lambda eurostd: eurostd.name, self.euro_stds)))

    def set_mode(self):
        self.dlg.cmbBoxMode.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                   self.dlg.cmbBoxSubsegment.currentText())
        self.selected_euro_std = self.get_object_from_array_by_name(self.euro_stds, self.dlg.cmbBoxEuroStd.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0 and len(self.selected_euro_std) > 0:
            filtred_modes = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0], segment=self.selected_segment[0],
                                                             eurostd=self.selected_euro_std[0])
            self.modes = set(x.mode for x in filtred_modes)
            self.dlg.cmbBoxMode.addItems(list(map(lambda mode: mode.name, self.modes)))

    def set_pollutants(self):
        self.disable_all_pollutants()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                   self.dlg.cmbBoxSubsegment.currentText())
        self.selected_euro_std = self.get_object_from_array_by_name(self.euro_stds,
                                                                    self.dlg.cmbBoxEuroStd.currentText())
        self.selected_mode = self.get_object_from_array_by_name(self.modes, self.dlg.cmbBoxMode.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0 and len(self.selected_euro_std) > 0 and len(self.selected_mode):
            filtred_pollutants = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0],
                                                              segment=self.selected_segment[0],
                                                         eurostd=self.selected_euro_std[0], mode=self.selected_mode[0])
            pollutants = list(map(lambda pollutant: pollutant.name, set(x.pollutant for x in filtred_pollutants)))
            self.activate_pollutants(pollutants)

    def activate_pollutants(self, pollutants):
        if emission.PollutantTypes.CO in pollutants:
            self.dlg.checkBoxCo.setEnabled(True)
        if emission.PollutantTypes.NOx in pollutants:
            self.dlg.checkBoxNox.setEnabled(True)
        if emission.PollutantTypes.VOC in pollutants:
            self.dlg.checkBoxVoc.setEnabled(True)
        if emission.PollutantTypes.EC in pollutants:
            self.dlg.checkBoxEc.setEnabled(True)
        if emission.PollutantTypes.PM_EXHAUST in pollutants:
            self.dlg.checkBoxPmExhaust.setEnabled(True)
        if emission.PollutantTypes.CH4 in pollutants:
            self.dlg.checkBoxCh4.setEnabled(True)

    def disable_all_pollutants(self):
        self.dlg.checkBoxCo.setEnabled(False)
        self.dlg.checkBoxNox.setEnabled(False)
        self.dlg.checkBoxVoc.setEnabled(False)
        self.dlg.checkBoxEc.setEnabled(False)
        self.dlg.checkBoxPmExhaust.setEnabled(False)
        self.dlg.checkBoxCh4.setEnabled(False)


    def get_object_from_array_by_name(self, array, name):
        if len(array) == 0:
            return []
        else:
            return list(filter(lambda obj: obj.name == name, array))


    def run(self):
        """Run method that performs all the real work"""
        # set input parameters to default when the dialog has been closed and open again
        self.dlg.cmbBoxVehicleType.clear()
        self.dlg.cmbBoxFuelType.clear()
        self.dlg.cmbBoxSubsegment.clear()
        self.dlg.cmbBoxEuroStd.clear()
        self.dlg.cmbBoxMode.clear()

        self.set_categories()
        self.set_fuels()
        self.set_segments()
        self.set_euro_std()
        self.set_mode()
        self.set_pollutants()

        self.dlg.cmbBoxLoad.clear()
        self.dlg.cmbBoxLoad.addItems(["0", "50", "100"])
        self.dlg.lineEditStartX.setText("")
        self.dlg.lineEditStartY.setText("")
        self.dlg.lineEditEndX.setText("")
        self.dlg.lineEditEndY.setText("")
        self.dlg.textEditSummary.clear()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.canvas.unsetMapTool(self.mapTool)
        else:
            self.dlg.widgetLoading.setShown(False)
            # pass