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
from PyQt4.QtGui import QAction, QIcon, QColor, QWidget, QListWidget, QListWidgetItem, QDialogButtonBox
from qgis.core import QGis, QgsCoordinateTransform, QgsRectangle, QgsPoint, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.gui import QgsRubberBand
from Overlay import Overlay

from copyLatLonTool import CopyLatLonTool
from settings import SettingsWidget
import pip
import os.path

from thewidgetitem import TheWidgetItem
import json
import sys


plugin_dir = os.path.dirname(__file__)
emissionCalculator_dir = os.path.join(plugin_dir, 'emission')
matplotlib_dir = os.path.join(plugin_dir, 'matplotlib')
try:
    import emission
except:
    if "win" in sys.platform:
        # pip.main(['-m', 'install', '--target=%s' % emissionCalculator_dir, 'emission'])
        pass
    else:
        pip.main(['install', '--target=%s' % emissionCalculator_dir, 'emission'])
    if emissionCalculator_dir not in sys.path:
        sys.path.append(emissionCalculator_dir)
    import emission
try:
    from RoadEmissionPlannerThread import RoadEmissionPlannerThread
except:
    from RoadEmissionPlannerThread import RoadEmissionPlannerThread
try:
    import matplotlib.pyplot as plt
except:
    pip.main(['install', '--target=%s' % matplotlib_dir, 'matplolib'])
    if matplotlib_dir not in sys.path:
        sys.path.append(matplotlib_dir)
    import matplotlib.pyplot as plt

# from PyQt4.QtCore import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from road_emission_calculator_dialog import RoadEmissionCalculatorDialog
from layer_mng import LayerMng
import layer_mng

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
        self.planner = None
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

        self.layer_mng = LayerMng(self.iface)
        # Declare instance attributes
        self.actions = []
        self.vehicle_categories = []
        self.selected_category = []
        self.selected_fuel = []
        self.selected_segment = []
        self.selected_euro_std = []
        self.selected_mode = []
        self.menu = self.tr(u'&Road Emission Calculator')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RoadEmissionCalculator')
        self.toolbar.setObjectName(u'RoadEmissionCalculator')

        # matplolib generate lines in color sequence: blue, green, red, cyan, magenta, yellow, black, white
        # same color schema will be use for proposal roads
        self.color_list = {0:[0, 0, 255], 1:[0, 255, 0], 2:[255, 0, 0], 3:[0, 255, 255],
                           4:[255, 0, 255], 5:[255, 255, 0], 6:[0, 0, 0], 7:[255, 255, 255]}

        self.pollutants_checkboxes = {emission.PollutantTypes.CO: self.dlg.checkBoxCo,
                                      emission.PollutantTypes.NOx: self.dlg.checkBoxNox,
                                      emission.PollutantTypes.VOC: self.dlg.checkBoxVoc,
                                      emission.PollutantTypes.EC: self.dlg.checkBoxEc,
                                      emission.PollutantTypes.PM_EXHAUST: self.dlg.checkBoxPmExhaust,
                                      emission.PollutantTypes.CH4: self.dlg.checkBoxCh4}

        self.selected_route_id = -1

        # Signals: Route parameters
        self.dlg.btnAddStartPoint.clicked.connect(self.add_start_point)
        self.dlg.btnAddEndPoint.clicked.connect(self.add_end_point)
        self.dlg.btnRemoveStartPoint.clicked.connect(self.remove_start_point)
        self.dlg.btnRemoveEndPoint.clicked.connect(self.remove_end_point)
        self.dlg.cmbBoxLoad.currentIndexChanged.connect(self.remove_route_layers)
        self.dlg.lineEditHeight.textChanged.connect(self.remove_route_layers)
        self.dlg.lineEditLength.textChanged.connect(self.remove_route_layers)

        # Widget loading overlay
        self.dlg.widgetLoading.setShown(False)
        self.overlay = Overlay(self.dlg.widgetLoading)
        self.overlay.resize(785,455)
        self.overlay.hide()

        # Road Emission Planner Thread
        self.road_emission_planner_thread = RoadEmissionPlannerThread()
        self.road_emission_planner_thread.plannerFinished.connect(self.on_road_emission_planner_finished)

        # Signals: Set vehicle
        self.dlg.cmbBoxVehicleType.currentIndexChanged.connect(self.set_fuels)
        self.dlg.cmbBoxFuelType.currentIndexChanged.connect(self.set_segments)
        self.dlg.cmbBoxSegment.currentIndexChanged.connect(self.set_euro_std)
        self.dlg.cmbBoxEuroStd.currentIndexChanged.connect(self.set_mode)
        self.dlg.cmbBoxMode.currentIndexChanged.connect(self.set_pollutants)

        # Signals: Summary and show layer in the map
        self.dlg.listWidget.itemClicked.connect(self.select_route)
        self.dlg.cmbBoxSortBy.currentIndexChanged.connect(self.sort_routes_by_selection)

        # Signals: Show results in graph
        self.dlg.checkBoxShowInGraph.clicked.connect(self.activate_graph_cumulative_curve_chckbox)

        # Buttons: Load and save settings
        self.dlg.btnSaveSettings.clicked.connect(self.save_settings)
        self.dlg.btnLoadSettings.clicked.connect(self.load_settings)

        # Button: Start calculate emission/show result in graph when isChecked
        self.dlg.btnGetEmissions.clicked.connect(self.on_road_emission_planner_start)

        # init with default values
        self.dlg.lineEditLength.setText('12')
        self.dlg.lineEditHeight.setText('4.4')

        buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        buttonBox.button(QDialogButtonBox.Close).clicked.connect(self.closeEvent)
        # buttonBox.accepted.connect(self.closeEvent)
        # self.dlg.closeButton.connect(self.closeEvent)

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
        self.dlg.lineEditStartX.setReadOnly(True)
        self.dlg.lineEditStartY.setReadOnly(True)
        self.dlg.lineEditEndX.setReadOnly(True)
        self.dlg.lineEditEndY.setReadOnly(True)
        self.activate_graph_cumulative_curve_chckbox()

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

    def activate_graph_cumulative_curve_chckbox(self):
        self.dlg.checkBoxCumulative.setEnabled(self.dlg.checkBoxShowInGraph.isChecked())

    def set_new_point(self, point_name):
        self.mapTool.point_name = point_name
        self.canvas.setMapTool(self.mapTool)

    def add_start_point(self):
        # only one start point can be in canvas/legend
        self.remove_route_layers()
        self.remove_start_point()
        self.set_new_point(layer_mng.LayerNames.STARTPOINT)
        # self.dlg.hide()

    def add_end_point(self):
        # only one end point can be in canvas/legend
        self.remove_route_layers()
        self.remove_end_point()
        self.set_new_point(layer_mng.LayerNames.ENDPOINT)
        # self.dlg.hide()

    def remove_start_point(self):
        self.set_planner_none()
        self.dlg.lineEditStartX.setText("")
        self.dlg.lineEditStartY.setText("")
        self.layer_mng.remove_layer(layer_mng.LayerNames.STARTPOINT)

    def remove_end_point(self):
        self.set_planner_none()
        self.dlg.lineEditEndX.setText("")
        self.dlg.lineEditEndY.setText("")
        self.layer_mng.remove_layer(layer_mng.LayerNames.ENDPOINT)

    def set_planner_none(self):
        self.planner = None
        self.dlg.listWidget.clear()

    'set new Layers to use the Project-CRS'

    def enableUseOfGlobalCrs(self):
        self.s = QSettings()
        self.oldValidation = str(self.s.value("/Projections/defaultBehaviour"))
        self.s.setValue("/Projections/defaultBehaviour", "useProject")

    'enable old settings again'

    def disableUseOfGlobalCrs(self):
        self.s.setValue("/Projections/defaultBehaviour", self.oldValidation)

    def on_road_emission_planner_start(self):
        if self.planner:
            self.show_pollutants_in_graph()
        else:
            if (self.dlg.lineEditStartX.text() == "" or self.dlg.lineEditStartY.text() == "" or
                    self.dlg.lineEditEndX.text() == "" or self.dlg.lineEditEndY.text() == ""):
                return
            start = [float(self.dlg.lineEditStartX.text()), float(self.dlg.lineEditStartY.text())]
            stop = [float(self.dlg.lineEditEndX.text()), float(self.dlg.lineEditEndY.text())]
            vehicle = emission.vehicles.Vehicle

            type_category = emission.vehicles.Vehicle.get_type_for_category(self.dlg.cmbBoxVehicleType.currentText())
            if type_category == emission.vehicles.VehicleTypes.CAR:
                vehicle = emission.vehicles.Car()
            if type_category == emission.vehicles.VehicleTypes.BUS or type_category == emission.vehicles.VehicleTypes.TRUCK:
                if type_category == emission.vehicles.VehicleTypes.BUS:
                    vehicle = emission.vehicles.Bus()
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
            vehicle.segment = self.dlg.cmbBoxSegment.currentText()
            vehicle.euro_std = self.dlg.cmbBoxEuroStd.currentText()
            vehicle.mode = self.dlg.cmbBoxMode.currentText()

            self.planner = emission.Planner(start, stop, vehicle)

            for x in self.pollutants_checkboxes:
                if self.pollutants_checkboxes[x].isEnabled():
                    self.planner.add_pollutant(x)

            self.dlg.listWidget.clear()
            self.dlg.widgetLoading.setShown(True)
            self.overlay.show()
            self.road_emission_planner_thread.set_planner(self.planner)
            self.road_emission_planner_thread.start()

    def on_road_emission_planner_finished(self):
        self.overlay.hide()
        self.layer_mng.remove_layer(layer_mng.LayerNames.ROUTE)
        self.dlg.widgetLoading.setShown(False)
        if 'routes' in self.planner._json_data:
            self.road_emission_planner_finished()
        else:
            self.add_error_to_list_widget("Unable to get a good response from web service.")

    def road_emission_planner_finished(self):
        self.planner._calculate_emissions()
        self.dlg.cmbBoxSortBy.clear()
        routes = self.planner.routes
        pollutant_types = self.planner.pollutants.keys()
        if len(routes) > 0:
            self.dlg.cmbBoxSortBy.addItem("Distance")
            self.dlg.cmbBoxSortBy.addItem("Time")
            self.dlg.cmbBoxSortBy.addItems(pollutant_types)
            for route in routes:
                self.layer_mng.create_layer(route.path, layer_mng.LayerNames.ROUTE, layer_mng.GeometryTypes.LINE, 2, route.id, self.color_list)
            self.sort_routes_by_selection()
            self.show_pollutants_in_graph()

    def show_pollutants_in_graph(self):
        if self.planner:
            routes = self.planner.routes
            pollutant_types = self.planner.pollutants.keys()
            if self.dlg.checkBoxShowInGraph.isChecked() and self.any_pollutant_checked(pollutant_types):
                fig = plt.figure()
                figs = []

                grafIdx = 0
                active_graphs = 0

                for pt in pollutant_types:
                    if self.pollutants_checkboxes[pt].isEnabled() and self.pollutants_checkboxes[pt].isChecked():
                        active_graphs += 1

                for pt in pollutant_types:
                    if self.pollutants_checkboxes[pt].isEnabled() and self.pollutants_checkboxes[pt].isChecked():
                        num_plots = 100 * active_graphs + 10 + grafIdx + 1
                        ax = fig.add_subplot(num_plots)
                        ax.set_title(pt)
                        if self.dlg.checkBoxCumulative.isChecked():
                            cumulative_route_pollutants = []
                            for route in routes:
                                cumulative_values = []
                                cumulative_value = 0
                                for plt_value in route.pollutants[pt]:
                                    cumulative_value += plt_value
                                    cumulative_values.append(cumulative_value)
                                cumulative_route_pollutants.append(cumulative_values)
                            ax.set_ylim(0, max(max(cumulative_route_pollutants)) + 0.2)
                        else:
                            ax.set_ylim(0, max(max(x.pollutants[pt] for x in routes)) + 0.2)
                        figs.append(ax)
                        grafIdx += 1

                for r in routes:
                    grafIdx = 0
                    for pt in pollutant_types:
                        if self.pollutants_checkboxes[pt].isEnabled() and self.pollutants_checkboxes[pt].isChecked():
                            ax = figs[grafIdx]
                            if self.dlg.checkBoxCumulative.isChecked():
                                cumulative_values = []
                                cumulative_value = 0
                                for x in r.pollutants[pt]:
                                    cumulative_value += x
                                    cumulative_values.append(cumulative_value)
                                ax.plot(r.distances[0], cumulative_values)
                            else:
                                ax.plot(r.distances[0], r.pollutants[pt])
                            grafIdx += 1

                ax = figs[-1]
                labels = ["Route " + str(i + 1) for i in range(len(routes))]
                pos = (len(figs) / 10.0) * (-1)
                ax.legend(labels, loc=(0, pos), ncol=len(routes))
                plt.show()

    def any_pollutant_checked(self, pollutant_types):
        for pt in pollutant_types:
            if self.pollutants_checkboxes[pt].isChecked():
                return True
        return False

    def select_route(self):
        if self.dlg.listWidget.currentItem():
            route_item = self.dlg.listWidget.itemWidget(self.dlg.listWidget.currentItem())
            if (route_item.route_id == self.selected_route_id):
                self.clear_selection()
                return
            self.layer_mng.remove_layer(layer_mng.LayerNames.SELECTED)
            self.selected_route_id = route_item.route_id
            route = self.planner.routes[route_item.route_id]
            self.layer_mng.create_layer(route.path, layer_mng.LayerNames.SELECTED, layer_mng.GeometryTypes.LINE, 4, route.id, self.color_list)

    def clear_selection(self):
        self.layer_mng.remove_layer(layer_mng.LayerNames.SELECTED)
        self.dlg.listWidget.clearSelection()
        self.selected_route_id = -1

    def sort_routes_by_selection(self):
        routes = self.planner.routes
        self.dlg.listWidget.clear()
        self.clear_selection()
        if len(routes) > 0 and self.dlg.cmbBoxSortBy.count() > 0:
            if self.dlg.cmbBoxSortBy.currentText() == "Distance":
                sorted_by = sorted(routes, key=lambda x: x.distance)
            elif self.dlg.cmbBoxSortBy.currentText() == "Time":
                sorted_by = sorted(routes, key=lambda x: x.minutes)
            else:
                sorted_by = sorted(routes, key=lambda x: x.total_emission(self.dlg.cmbBoxSortBy.currentText()))
            for r in sorted_by:
                self.add_route_item_to_list_widget(r)

    def add_route_item_to_list_widget(self, route):
        pollutant_types = self.planner.pollutants.keys()
        distance = route.distance / 1000
        hours, minutes = divmod(route.minutes, 60)
        hours = int(hours)
        minutes = int(minutes)

        myQCustomQWidget = TheWidgetItem()
        myQCustomQWidget.set_route_name("Route" + str(route.id + 1), self.color_list[route.id])
        myQCustomQWidget.set_route_id(route.id)
        myQCustomQWidget.set_distance_time(str(distance) + " km", str(hours) + " hours and " + str(
            minutes) + " minutes.")
        myQCustomQWidget.hide_all_lbl_pollutants()
        for idxPlt, pt in enumerate(pollutant_types):
            myQCustomQWidget.set_pollutants(idxPlt, pt, round(route.total_emission(pt), 2))
        myQListWidgetItem = QListWidgetItem(self.dlg.listWidget)
        myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
        self.dlg.listWidget.addItem(myQListWidgetItem)
        self.dlg.listWidget.setItemWidget(myQListWidgetItem, myQCustomQWidget)
        self.dlg.listWidget.setStyleSheet("""
                                        QListWidget:item:selected:active {
                                             background-color:rgb(230, 230, 230);
                                        }
                                        """)

    def add_error_to_list_widget(self, error_msg):
        myQCustomQWidget = TheWidgetItem()
        myQCustomQWidget.set_error_msg("Error: {}".format(error_msg))
        myQCustomQWidget.hide_all_lbl_pollutants()
        myQListWidgetItem = QListWidgetItem(self.dlg.listWidget)
        myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
        self.dlg.listWidget.addItem(myQListWidgetItem)
        self.dlg.listWidget.setItemWidget(myQListWidgetItem, myQCustomQWidget)

    def set_categories(self):
        self.vehicle_categories = list(emission.session.query(emission.models.Category).all())
        list_categories = list(map(lambda category: category.name, self.vehicle_categories))
        list_categories.sort()
        self.dlg.cmbBoxVehicleType.addItems(list_categories)
        self.selected_category = self.get_object_from_array_by_name(self.vehicle_categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())

    def set_fuels(self):
        self.dlg.cmbBoxFuelType.clear()
        self.selected_category = self.get_object_from_array_by_name(self.vehicle_categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        if len(self.selected_category) > 0:
            filtred_fuels = list(emission.models.filter_parms(cat=self.selected_category[0]))
            self.fuels = set(x.fuel for x in filtred_fuels)
            list_fuels = list(map(lambda fuel: fuel.name, self.fuels))
            list_fuels.sort()
            self.dlg.cmbBoxFuelType.addItems(list_fuels)

    def set_segments(self):
        self.dlg.cmbBoxSegment.clear()
        self.selected_category = self.get_object_from_array_by_name(self.vehicle_categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0:
            filtred_segments = list(emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0]))
            self.segments = set(x.segment for x in filtred_segments)
            list_segments = list(map(lambda segment: str(segment.name), self.segments))
            list_segments.sort()
            self.dlg.cmbBoxSegment.addItems(list_segments)
            self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                       self.dlg.cmbBoxSegment.currentText())

    def set_euro_std(self):
        self.dlg.cmbBoxEuroStd.clear()
        self.selected_category = self.get_object_from_array_by_name(self.vehicle_categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments, self.dlg.cmbBoxSegment.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0:
            filtred_euro_stds = list(emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0],segment=self.selected_segment[0]))
            self.euro_stds = set(x.eurostd for x in filtred_euro_stds)
            list_euro_stds = list(map(lambda eurostd: eurostd.name, self.euro_stds))
            list_euro_stds.sort()
            self.dlg.cmbBoxEuroStd.addItems(list_euro_stds)

    def set_mode(self):
        self.dlg.cmbBoxMode.clear()
        self.selected_category = self.get_object_from_array_by_name(self.vehicle_categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                   self.dlg.cmbBoxSegment.currentText())
        self.selected_euro_std = self.get_object_from_array_by_name(self.euro_stds, self.dlg.cmbBoxEuroStd.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0 and len(self.selected_euro_std) > 0:
            filtred_modes = list(emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0], segment=self.selected_segment[0],
                                                             eurostd=self.selected_euro_std[0]))
            self.modes = set(x.mode for x in filtred_modes)
            list_modes = list(map(lambda mode: mode.name, self.modes))
            list_modes.sort()
            self.dlg.cmbBoxMode.addItems(list_modes)

    def set_pollutants(self):
        self.disable_all_pollutants()
        self.selected_category = self.get_object_from_array_by_name(self.vehicle_categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                   self.dlg.cmbBoxSegment.currentText())
        self.selected_euro_std = self.get_object_from_array_by_name(self.euro_stds,
                                                                    self.dlg.cmbBoxEuroStd.currentText())
        self.selected_mode = self.get_object_from_array_by_name(self.modes, self.dlg.cmbBoxMode.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0 and len(self.selected_euro_std) > 0 and len(self.selected_mode):
            filtred_pollutants = list(emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0],
                                                              segment=self.selected_segment[0],
                                                         eurostd=self.selected_euro_std[0], mode=self.selected_mode[0]))
            pollutants = list(map(lambda pollutant: pollutant.name, set(x.pollutant for x in filtred_pollutants)))
            self.enable_pollutants(pollutants)
            if self.planner:
                type_category = emission.vehicles.Vehicle.get_type_for_category(
                    self.dlg.cmbBoxVehicleType.currentText())
                if type_category == emission.vehicles.VehicleTypes.CAR:
                    self.planner._vehicle = emission.vehicles.Car()
                if type_category == emission.vehicles.VehicleTypes.BUS or type_category == emission.vehicles.VehicleTypes.TRUCK:
                    if type_category == emission.vehicles.VehicleTypes.BUS:
                        self.planner._vehicle = emission.vehicles.Bus()
                    if type_category == emission.vehicles.VehicleTypes.TRUCK:
                        self.planner._vehicle = emission.vehicles.Truck()
                if type_category == emission.vehicles.VehicleTypes.LCATEGORY:
                    self.planner._vehicle = emission.vehicles.LCategory()
                if type_category == emission.vehicles.VehicleTypes.VAN:
                    self.planner._vehicle = emission.vehicles.Van()
                self.planner._vehicle.fuel_type = self.dlg.cmbBoxFuelType.currentText()
                self.planner._vehicle.segment = self.dlg.cmbBoxSegment.currentText()
                self.planner._vehicle.euro_std = self.dlg.cmbBoxEuroStd.currentText()
                self.planner._vehicle.mode = self.dlg.cmbBoxMode.currentText()
                self.planner._pollutants = {}
                for x in self.pollutants_checkboxes:
                    if self.pollutants_checkboxes[x].isEnabled():
                        self.planner.add_pollutant(x)
                self.planner._calculate_emissions()
                self.sort_routes_by_selection()

    def enable_pollutants(self, pollutants):
        for x in pollutants:
            self.pollutants_checkboxes[x].setEnabled(True)

    def disable_all_pollutants(self):
        for x in self.pollutants_checkboxes.values():
            x.setEnabled(False)

    def uncheck_all_pollutants(self):
        for x in self.pollutants_checkboxes.values():
            x.setChecked(False)

    def save_settings(self):
        settings = {
            "startPoint": [self.dlg.lineEditStartX.text(), self.dlg.lineEditStartY.text()],
            "endPoint": [self.dlg.lineEditEndX.text(), self.dlg.lineEditEndY.text()],
            "load": self.dlg.cmbBoxLoad.currentText(),
            "height": self.dlg.lineEditHeight.text(),
            "length": self.dlg.lineEditLength.text(),
            "vehicleType": self.dlg.cmbBoxVehicleType.currentText(),
            "fuelType": self.dlg.cmbBoxFuelType.currentText(),
            "segment": self.dlg.cmbBoxSegment.currentText(),
            "euroStd": self.dlg.cmbBoxEuroStd.currentText(),
            "mode": self.dlg.cmbBoxMode.currentText(),
            "showResultInGraph": self.dlg.checkBoxShowInGraph.isChecked(),
            "cumulativeCurve": self.dlg.checkBoxCumulative.isChecked(),
            "nox": self.dlg.checkBoxNox.isChecked(),
            "co": self.dlg.checkBoxCo.isChecked(),
            "ec": self.dlg.checkBoxEc.isChecked(),
            "voc": self.dlg.checkBoxVoc.isChecked(),
            "ch4": self.dlg.checkBoxCh4.isChecked(),
            "pm": self.dlg.checkBoxPmExhaust.isChecked()

        }
        plugin_path = os.path.dirname(__file__)
        with open(plugin_path + "/settings.json", "w") as outfile:
            json.dump(settings, outfile)

    def load_settings(self):
        self.remove_all_memory_layers()
        self.dlg.listWidget.clear()
        settings_json_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        if os.path.isfile(settings_json_file):
            settings_data = json.load(open(settings_json_file))

            self.dlg.lineEditStartX.setText(settings_data["startPoint"][0])
            self.dlg.lineEditStartY.setText(settings_data["startPoint"][1])
            if self.dlg.lineEditStartX.text() != "" and self.dlg.lineEditStartY.text() != "":
                self.layer_mng.create_layer([float(self.dlg.lineEditStartX.text()), float(self.dlg.lineEditStartY.text())],
                                            layer_mng.LayerNames.STARTPOINT, layer_mng.GeometryTypes.POINT,None, None,None)
            self.dlg.lineEditEndX.setText(settings_data["endPoint"][0])
            self.dlg.lineEditEndY.setText(settings_data["endPoint"][1])
            if self.dlg.lineEditEndX.text() != "" and self.dlg.lineEditEndY.text() != "":
                self.layer_mng.create_layer([float(self.dlg.lineEditEndX.text()), float(self.dlg.lineEditEndY.text())],
                                            layer_mng.LayerNames.ENDPOINT, layer_mng.GeometryTypes.POINT, None, None,None)
            load_index = self.dlg.cmbBoxLoad.findText(settings_data["load"], Qt.MatchFixedString)
            if load_index >= 0:
                self.dlg.cmbBoxLoad.setCurrentIndex(load_index)
            self.dlg.lineEditHeight.setText(settings_data["height"])
            self.dlg.lineEditLength.setText(settings_data["length"])
            vehicle_type_index = self.dlg.cmbBoxVehicleType.findText(settings_data["vehicleType"], Qt.MatchFixedString)
            if vehicle_type_index >= 0:
                self.dlg.cmbBoxVehicleType.setCurrentIndex(vehicle_type_index)
            fuel_type_index = self.dlg.cmbBoxFuelType.findText(settings_data["fuelType"], Qt.MatchFixedString)
            if fuel_type_index >= 0:
                self.dlg.cmbBoxFuelType.setCurrentIndex(fuel_type_index)
            segment_index = self.dlg.cmbBoxSegment.findText(settings_data["segment"], Qt.MatchFixedString)
            if segment_index >= 0:
                self.dlg.cmbBoxSegment.setCurrentIndex(segment_index)
            euro_std_index = self.dlg.cmbBoxEuroStd.findText(settings_data["euroStd"], Qt.MatchFixedString)
            if euro_std_index >= 0:
                self.dlg.cmbBoxEuroStd.setCurrentIndex(euro_std_index)
            mode_index = self.dlg.cmbBoxMode.findText(settings_data["mode"], Qt.MatchFixedString)
            if mode_index >= 0:
                self.dlg.cmbBoxMode.setCurrentIndex(mode_index)
            self.dlg.checkBoxShowInGraph.setChecked(settings_data["showResultInGraph"])
            self.dlg.checkBoxCumulative.setChecked(settings_data["cumulativeCurve"])
            self.dlg.checkBoxNox.setChecked(settings_data["nox"])
            self.dlg.checkBoxCo.setChecked(settings_data["co"])
            self.dlg.checkBoxEc.setChecked(settings_data["ec"])
            self.dlg.checkBoxVoc.setChecked(settings_data["voc"])
            self.dlg.checkBoxCh4.setChecked(settings_data["ch4"])
            self.dlg.checkBoxPmExhaust.setChecked(settings_data["pm"])


    def get_object_from_array_by_name(self, array, name):
        if len(array) == 0:
            return []
        else:
            return list(filter(lambda obj: obj.name == name, array))

    def closeEvent(self):
        print("Close event clicked")

    def remove_all_memory_layers(self):
        self.remove_start_point()
        self.remove_end_point()
        self.layer_mng.remove_layer(layer_mng.LayerNames.SELECTED)
        self.layer_mng.remove_layer(layer_mng.LayerNames.ROUTE)
        self.set_planner_none()

    def remove_route_layers(self):
        self.layer_mng.remove_layer(layer_mng.LayerNames.SELECTED)
        self.layer_mng.remove_layer(layer_mng.LayerNames.ROUTE)
        self.set_planner_none()

    def run(self):
        """Run method that performs all the real work"""

        # set input parameters to default when dialog is open
        self.dlg.cmbBoxVehicleType.clear()
        self.dlg.cmbBoxFuelType.clear()
        self.dlg.cmbBoxSegment.clear()
        self.dlg.cmbBoxEuroStd.clear()
        self.dlg.cmbBoxMode.clear()

        self.set_categories()

        self.dlg.cmbBoxLoad.clear()
        self.dlg.cmbBoxLoad.addItems(["0", "0.5", "1"])
        self.dlg.lineEditStartX.setText("")
        self.dlg.lineEditStartY.setText("")
        self.dlg.lineEditEndX.setText("")
        self.dlg.lineEditEndY.setText("")
        self.dlg.listWidget.clear()
        self.dlg.checkBoxShowInGraph.setChecked(False)
        self.dlg.checkBoxCumulative.setChecked(False)
        self.uncheck_all_pollutants()

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
            self.remove_all_memory_layers()
