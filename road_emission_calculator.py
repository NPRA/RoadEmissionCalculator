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
from PyQt4.QtGui import QAction, QIcon, QColor, QWidget, QListWidget, QListWidgetItem
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
from thewidgetitem import TheWidgetItem
import json

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
        self.color_list = {0:[0, 0, 255], 1:[0, 255, 0], 2:[255, 0, 0], 3:[0, 255, 255],
                           4:[255, 0, 255], 5:[255, 255, 0], 6:[0, 0, 0], 7:[255, 255, 255]}

        self.pollutants_checkboxes = {emission.PollutantTypes.CO: self.dlg.checkBoxCo,
                                      emission.PollutantTypes.NOx: self.dlg.checkBoxNox,
                                      emission.PollutantTypes.VOC: self.dlg.checkBoxVoc,
                                      emission.PollutantTypes.EC: self.dlg.checkBoxEc,
                                      emission.PollutantTypes.PM_EXHAUST: self.dlg.checkBoxPmExhaust,
                                      emission.PollutantTypes.CH4: self.dlg.checkBoxCh4}

        self.selected_route_id = -1

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
        self.dlg.cmbBoxSegment.currentIndexChanged.connect(self.set_euro_std)
        self.dlg.cmbBoxEuroStd.currentIndexChanged.connect(self.set_mode)
        self.dlg.cmbBoxMode.currentIndexChanged.connect(self.set_pollutants)
        self.dlg.listWidget.itemClicked.connect(self.select_route)
        self.dlg.cmbBoxSortBy.currentIndexChanged.connect(self.sort_routes_by)

        self.dlg.checkBoxShowInGraph.clicked.connect(self.activate_cumulative)

        self.dlg.btnSaveSettings.clicked.connect(self.save_settings)
        self.dlg.btnLoadSettings.clicked.connect(self.load_settings)

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
        # self.dlg.textEditSummary.setReadOnly(True)
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

    # def set_vehicle_subsegment(self):
    #     self.dlg.cmbBoxSubsegment.clear()
    #     if self.dlg.cmbBoxVehicleType.currentText() == 'CAR':
    #         segments = emission.vehicles.Car.type
    #         self.dlg.cmbBoxSubsegment.addItems([list(d)[0] for d in segments])

    # def set_vehicle_euro_std(self):
    #
    #     self.dlg.cmbBoxEuroStd.clear()
    #     if self.dlg.cmbBoxVehicleType.currentText() == 'CAR':
    #         segments = emission.vehicles.Car.type
    #         self.dlg.cmbBoxEuroStd.addItems(list(filter(lambda y: y != None, [x.get(self.dlg.cmbBoxSubsegment.currentText()) for x in segments]))[0])

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

        self.overlay.show()
        self.roadEmissionPlanner.set_planner(self.planner)
        self.roadEmissionPlanner.start()

    def on_road_emission_planner_finished(self):
        self.overlay.hide()
        self.remove_layer("Route")
        self.road_emission_planner_finished()
        self.dlg.widgetLoading.setShown(False)

    def road_emission_planner_finished(self):
        # self.dlg.textEditSummary.clear()
        self.dlg.cmbBoxSortBy.clear()
        # self.dlg.listWidget.clear()
        routes = self.planner.routes
        pollutant_types = self.planner.pollutants.keys()
        if len(routes) > 0:
            self.dlg.cmbBoxSortBy.addItem("Distance")
            self.dlg.cmbBoxSortBy.addItem("Time")
            self.dlg.cmbBoxSortBy.addItems(pollutant_types)
            # self.dlg.cmbBoxSortBy.append
            # self.sort_routes_by()
            for route in routes:
                # self.dlg.textEditSummary.append("Route" + str(idx + 1) + ":")

                # self.dlg.textEditSummary.append(
                #     "Length: " + str(distance) + " km, driving time: " + str(hours) + " hours and " + str(
                #         minutes) + " minutes.")
                # self.dlg.textEditSummary.append("")
                # for pt in pollutant_types:
                #     self.dlg.textEditSummary.append(("    {} = {}".format(pt, route.total_emission(pt))))
                #
                # self.dlg.textEditSummary.append("")
                # self.dlg.textEditSummary.append("")

                # distance = route.distance / 1000
                # hours, minutes = divmod(route.minutes, 60)
                # hours = int(hours)
                # minutes = int(minutes)
                #
                # myQCustomQWidget = TheWidgetItem()
                # myQCustomQWidget.set_route_name("Route" + str(idx + 1))
                # myQCustomQWidget.set_distance_time(str(distance) + " km", str(hours) + " hours and " + str(
                #         minutes) + " minutes.")
                # myQCustomQWidget.hide_all_lbl_pollutants()
                # for idxPlt, pt in enumerate(pollutant_types):
                #     myQCustomQWidget.set_pollutants(idxPlt, pt, round(route.total_emission(pt),2))
                # myQListWidgetItem = QListWidgetItem(self.dlg.listWidget)
                # myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
                # self.dlg.listWidget.addItem(myQListWidgetItem)
                # self.dlg.listWidget.setItemWidget(myQListWidgetItem, myQCustomQWidget)


                ## create an empty memory layer
                vl = QgsVectorLayer("LineString", "Route" + str(route.id + 1), "memory")
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
                # if idx < (len(self.color_list) - 1):
                # print ("Route id: {}".format(route.id))
                # print ("Route color: {}".format(self.color_list[route.id]))
                # print ("Route color: {}".format(self.color_list[route.id]))

                color = self.color_list[route.id]
                # print ("Color: {}.{}.{}".format(color[0], color[1], color[2]))
                sym.setColor(QColor.fromRgb(color[0], color[1], color[2]))
                sym.setWidth(2)

                ## add layer to the registry and over the map canvas
                QgsMapLayerRegistry.instance().addMapLayer(vl)

            self.sort_routes_by()

            ## Show pollutant results in graph
            if self.dlg.checkBoxShowInGraph.isChecked():
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

                # print("Fig length: {}".format(len(figs)))

                ax = figs[-1]
                labels = ["Route " + str(i + 1) for i in range(len(routes))]
                pos = (len(figs) / 10.0) * (-1)
                ax.legend(labels, loc=(0, pos), ncol=len(routes))
                plt.show()


    def select_route(self):
        if self.dlg.listWidget.currentItem():
            route_item = self.dlg.listWidget.itemWidget(self.dlg.listWidget.currentItem())
            if (route_item.route_id == self.selected_route_id):
                self.clear_selection()
                return
            self.remove_layer("Selected")
            self.selected_route_id = route_item.route_id
            route = self.planner.routes[route_item.route_id]
            ## create an empty memory layer
            vl = QgsVectorLayer("LineString", "Selected route" + str(route.id + 1), "memory")
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
            # if selected_idx < (len(self.color_list) - 1):
            color = self.color_list[route.id]
            sym.setColor(QColor.fromRgb(color[0], color[1], color[2]))
            sym.setWidth(4)

            ## add layer to the registry and over the map canvas
            QgsMapLayerRegistry.instance().addMapLayer(vl)

    def clear_selection(self):
        self.remove_layer("Selected")
        self.dlg.listWidget.clearSelection()
        self.selected_route_id = -1

    def sort_routes_by(self):
        # pass
        routes = self.planner.routes
        print ("Sort by items count: {} and current name: {}".format(self.dlg.cmbBoxSortBy.count(), self.dlg.cmbBoxSortBy.currentText()))
        self.dlg.listWidget.clear()
        self.clear_selection()
        if len(routes) > 0 and self.dlg.cmbBoxSortBy.count() > 0:
            print ("Current text: {}".format(self.dlg.cmbBoxSortBy.currentText()))
            if self.dlg.cmbBoxSortBy.currentText() == "Distance":
                sorted_after_distance = sorted(routes, key=lambda x: x.distance)
                for r in sorted_after_distance:
                    self.add_route_item_to_list_widget(r)
            elif self.dlg.cmbBoxSortBy.currentText() == "Time":
                routes.sort()
                for r in routes:
                    self.add_route_item_to_list_widget(r)
            else:
                sorted_after_pollutant = sorted(routes, key=lambda x: x.total_emission(self.dlg.cmbBoxSortBy.currentText()))
                for r in sorted_after_pollutant:
                    self.add_route_item_to_list_widget(r)

    def add_route_item_to_list_widget(self, route):
        pollutant_types = self.planner.pollutants.keys()
        distance = route.distance / 1000
        hours, minutes = divmod(route.minutes, 60)
        hours = int(hours)
        minutes = int(minutes)

        myQCustomQWidget = TheWidgetItem()
        myQCustomQWidget.set_route_name("Route" + str(route.id + 1))
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

    def set_categories(self):
        self.categories = emission.session.query(emission.models.Category).all()
        list_categories = list(map(lambda category: category.name, self.categories))
        list_categories.sort()
        self.dlg.cmbBoxVehicleType.addItems(list_categories)
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())

    def set_fuels(self):
        self.dlg.cmbBoxFuelType.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        if len(self.selected_category) > 0:
            filtred_fuels = emission.models.filter_parms(cat=self.selected_category[0])
            self.fuels = set(x.fuel for x in filtred_fuels)
            list_fuels = list(map(lambda fuel: fuel.name, self.fuels))
            list_fuels.sort()
            self.dlg.cmbBoxFuelType.addItems(list_fuels)

    def set_segments(self):
        self.dlg.cmbBoxSegment.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0:
            filtred_segments = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0])
            self.segments = set(x.segment for x in filtred_segments)
            list_segments = list(map(lambda segment: str(segment.name), self.segments))
            list_segments.sort()
            self.dlg.cmbBoxSegment.addItems(list_segments)
            self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                       self.dlg.cmbBoxSegment.currentText())

    def set_euro_std(self):
        self.dlg.cmbBoxEuroStd.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments, self.dlg.cmbBoxSegment.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0:
            filtred_euro_stds = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0],segment=self.selected_segment[0])
            self.euro_stds = set(x.eurostd for x in filtred_euro_stds)
            list_euro_stds = list(map(lambda eurostd: eurostd.name, self.euro_stds))
            list_euro_stds.sort()
            self.dlg.cmbBoxEuroStd.addItems(list_euro_stds)

    def set_mode(self):
        self.dlg.cmbBoxMode.clear()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                   self.dlg.cmbBoxSegment.currentText())
        self.selected_euro_std = self.get_object_from_array_by_name(self.euro_stds, self.dlg.cmbBoxEuroStd.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0 and len(self.selected_euro_std) > 0:
            filtred_modes = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0], segment=self.selected_segment[0],
                                                             eurostd=self.selected_euro_std[0])
            self.modes = set(x.mode for x in filtred_modes)
            list_modes = list(map(lambda mode: mode.name, self.modes))
            list_modes.sort()
            self.dlg.cmbBoxMode.addItems(list_modes)

    def set_pollutants(self):
        self.disable_all_pollutants()
        self.selected_category = self.get_object_from_array_by_name(self.categories,
                                                                    self.dlg.cmbBoxVehicleType.currentText())
        self.selected_fuel = self.get_object_from_array_by_name(self.fuels, self.dlg.cmbBoxFuelType.currentText())
        self.selected_segment = self.get_object_from_array_by_name(self.segments,
                                                                   self.dlg.cmbBoxSegment.currentText())
        self.selected_euro_std = self.get_object_from_array_by_name(self.euro_stds,
                                                                    self.dlg.cmbBoxEuroStd.currentText())
        self.selected_mode = self.get_object_from_array_by_name(self.modes, self.dlg.cmbBoxMode.currentText())
        if len(self.selected_category) > 0 and len(self.selected_fuel) > 0 and len(self.selected_segment) > 0 and len(self.selected_euro_std) > 0 and len(self.selected_mode):
            filtred_pollutants = emission.models.filter_parms(cat=self.selected_category[0], fuel=self.selected_fuel[0],
                                                              segment=self.selected_segment[0],
                                                         eurostd=self.selected_euro_std[0], mode=self.selected_mode[0])
            pollutants = list(map(lambda pollutant: pollutant.name, set(x.pollutant for x in filtred_pollutants)))
            self.enable_pollutants(pollutants)

    def enable_pollutants(self, pollutants):
        for x in pollutants:
            self.pollutants_checkboxes[x].setEnabled(True)

    def disable_all_pollutants(self):
        for x in self.pollutants_checkboxes.values():
            x.setEnabled(False)

    def save_settings(self):
        print("Plugin directory: {}".format(os.path.dirname(__file__)))

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
        settings_json_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        settings_data = {}
        if os.path.isfile(settings_json_file):
            # with gzip.open(gzip_json, "rb") as data_file:
            #     data = json.loads(data_file.read().decode("ascii"))
            # return data
            settings_data = json.load(open(settings_json_file))

            print ("load coordinates: {}".format(settings_data["startPoint"]))
            self.dlg.lineEditStartX.setText(settings_data["startPoint"][0])
            self.dlg.lineEditStartY.setText(settings_data["startPoint"][1])
            self.dlg.lineEditEndX.setText(settings_data["endPoint"][0])
            self.dlg.lineEditEndY.setText(settings_data["endPoint"][1])
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


    def run(self):
        """Run method that performs all the real work"""
        # set input parameters to default when the dialog has been closed and open again
        self.dlg.cmbBoxVehicleType.clear()
        self.dlg.cmbBoxFuelType.clear()
        self.dlg.cmbBoxSegment.clear()
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
        # self.dlg.textEditSummary.clear()

        # Create QCustomQWidget
        # self.myQCustomQWidget = TheWidgetItem()

        # Create QListWidgetItem
        # myQCustomQWidget = TheWidgetItem()
        # myQCustomQWidget.set_route_name("Route1")
        # myQCustomQWidget.set_distance_time("35 km", "0 hours 20 minutes")
        # myQListWidgetItem = QListWidgetItem(self.dlg.listWidget)
        # myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
        # self.dlg.listWidget.addItem(myQListWidgetItem)
        # self.dlg.listWidget.setItemWidget(myQListWidgetItem, myQCustomQWidget)
        #
        # myQCustomQWidget = TheWidgetItem()
        # myQCustomQWidget.set_route_name("Route2")
        # myQCustomQWidget.set_distance_time("45 km", "0 hours 49 minutes")
        # myQListWidgetItem = QListWidgetItem(self.dlg.listWidget)
        # myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
        # self.dlg.listWidget.addItem(myQListWidgetItem)
        # self.dlg.listWidget.setItemWidget(myQListWidgetItem, myQCustomQWidget)


        # for index, name, icon in [
        #     ('No.1', 'Meyoko', 'icon.png'),
        #     ('No.2', 'Nyaruko', 'icon.png'),
        #     ('No.3', 'Louise', 'icon.png')]:
        #     # Create QCustomQWidget
        #     myQCustomQWidget = TheWidgetItem()
        #     myQCustomQWidget.setTextUp(index)
        #     myQCustomQWidget.setTextDown(name)
        #     myQCustomQWidget.setIcon(icon)
        #     # Create QListWidgetItem
        #     myQListWidgetItem = QListWidgetItem(self.dlg.listWidget)
        #     # Set size hint
        #     myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
        #     # Add QListWidgetItem into QListWidget
        #     self.dlg.listWidget.addItem(myQListWidgetItem)
        #     self.dlg.listWidget.setItemWidget(myQListWidgetItem, myQCustomQWidget)


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