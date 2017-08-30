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
# from qgis.core import QgsVectorLayer, QgsField, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint
from qgis.core import QGis, QgsCoordinateTransform, QgsRectangle, QgsPoint, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.gui import QgsRubberBand
from Overlay import Overlay
from RoadThread import RoadThread
from EmissionsThread import EmissionsThread
from qgis.core import QgsVectorLayer, QgsField, QgsMapLayerRegistry, QgsFeature, QgsGeometry

from copyLatLonTool import CopyLatLonTool
from settings import SettingsWidget
from EmissionCalculatorLib import EmissionCalculatorLib

import time

# from PyQt4.QtCore import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from road_emission_calculator_dialog import RoadEmissionCalculatorDialog
import os.path


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
        self.emission_calculator = EmissionCalculatorLib()
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
        self.menu = self.tr(u'&Road Emission Calculator')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RoadEmissionCalculator')
        self.toolbar.setObjectName(u'RoadEmissionCalculator')

        # matplolib generate lines in color sequence: blue, green, red, cyan, magenta, yellow, black, white
        # same color schema will be use for proposal roads

        self.color_list = [(0,0,255), (0,255,0), (255, 0, 0), (0,255,255), (255, 0, 255), (255, 255, 0), (0, 0, 0), (255, 255, 255)]

        self.dlg.checkBoxNox.setChecked(True)
        self.dlg.checkBoxCo.setChecked(True)
        self.dlg.checkBoxHc.setChecked(True)
        self.dlg.checkBoxPm.setChecked(True)
        self.dlg.checkBoxFc.setChecked(True)

        # self.dlg.checkBoxCumulative.setChecked(True)

        self.dlg.btnAddStartPoint.clicked.connect(self.add_start_point)
        self.dlg.btnAddEndPoint.clicked.connect(self.add_end_point)
        self.dlg.btnRemoveStartPoint.clicked.connect(self.remove_start_point)
        self.dlg.btnRemoveEndPoint.clicked.connect(self.remove_end_point)

        self.dlg.widgetLoading.setShown(False)
        self.overlay = Overlay(self.dlg.widgetLoading)
        self.overlay.resize(700,445)
        self.overlay.hide()

        # self.dlg.btnGetRoads.clicked.connect(self.get_roads)
        self.dlg.btnGetRoads.clicked.connect(self.onRoadStart)
        self.roadTask = RoadThread()
        self.roadTask.urlFinished.connect(self.onRoadFinished)

        self.emissionTask = EmissionsThread()
        self.emissionTask.calculationFinished.connect(self.onEmissionFinished)

        # self.dlg.btnGetEmissions.clicked.connect(self.get_emissions)
        self.dlg.btnGetEmissions.clicked.connect(self.onEmissionStart)
        self.dlg.cmbBoxType.currentIndexChanged.connect(self.set_vehicle_type)
        self.dlg.cmbBoxSscName.currentIndexChanged.connect(self.set_vehicle_ssc)
        self.dlg.cmbBoxSubsegment.currentIndexChanged.connect(self.set_vehicle_subsegment)
        self.dlg.cmbBoxTecName.currentIndexChanged.connect(self.set_vehicle_tec)
        self.dlg.cmbBoxLoad.currentIndexChanged.connect(self.set_vehicle_load)
        self.dlg.checkBoxShowInGraph.clicked.connect(self.activate_cumulative)
        # self.clickTool.canvasClicked.connect(self.handleMouseDown)

        # init with default values
        self.dlg.lineEditLength.setText(self.emission_calculator.length)
        self.dlg.lineEditHeight.setText(self.emission_calculator.height)

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
        self.activate_group_box_calculator(False)

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

    def set_vehicle_type(self):
        self.emission_calculator.emissionJson.set_type(self.dlg.cmbBoxType.currentText())
        self.dlg.cmbBoxSscName.clear()
        self.dlg.cmbBoxSscName.addItems(self.emission_calculator.emissionJson.get_ssc_names())

    def set_vehicle_ssc(self):
        self.emission_calculator.emissionJson.set_ssc_name(self.dlg.cmbBoxSscName.currentText())
        self.dlg.cmbBoxSubsegment.clear()
        self.dlg.cmbBoxSubsegment.addItems(self.emission_calculator.emissionJson.get_subsegment())

    def set_vehicle_subsegment(self):
        self.emission_calculator.emissionJson.set_subsegment(self.dlg.cmbBoxSubsegment.currentText())
        self.dlg.cmbBoxTecName.clear()
        self.dlg.cmbBoxTecName.addItems(self.emission_calculator.emissionJson.get_tec_names())
        if self.dlg.cmbBoxTecName.count() == 0 or self.dlg.cmbBoxTecName.count() == 1:
            self.dlg.cmbBoxTecName.setEnabled(False)
        else:
            self.dlg.cmbBoxTecName.setEnabled(True)

    def set_vehicle_tec(self):
        self.emission_calculator.emissionJson.set_tec_name(self.dlg.cmbBoxTecName.currentText())

    def set_vehicle_load(self):
        self.emission_calculator.emissionJson.set_load(self.dlg.cmbBoxLoad.currentText())

    def activate_cumulative(self):
        self.dlg.checkBoxCumulative.setEnabled(self.dlg.checkBoxShowInGraph.isChecked())

    def activate_group_box_calculator(self, value):
        self.dlg.groupBoxCalculator.setEnabled(value)

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
        # self.dlg.lblStartPoint.setText("0,0")
        self.dlg.lineEditStartX.setText("")
        self.dlg.lineEditStartY.setText("")
        self.remove_layer("Start_point")
        self.activate_group_box_calculator(False)

    def remove_end_point(self):
        # self.dlg.lblEndPoint.setText("0,0")
        self.dlg.lineEditEndX.setText("")
        self.dlg.lineEditEndY.setText("")
        self.remove_layer("End_point")
        self.activate_group_box_calculator(False)

    'set new Layers to use the Project-CRS'

    def enableUseOfGlobalCrs(self):
        self.s = QSettings()
        self.oldValidation = str(self.s.value("/Projections/defaultBehaviour"))
        self.s.setValue("/Projections/defaultBehaviour", "useProject")

    'enable old settings again'

    def disableUseOfGlobalCrs(self):
        self.s.setValue("/Projections/defaultBehaviour", self.oldValidation)

    def onRoadStart(self):
        if self.dlg.lineEditStartX.text() == "" or self.dlg.lineEditStartY.text() == "" \
                or self.dlg.lineEditEndX.text() == "" or self.dlg.lineEditEndY.text() == "":
            return
        else:
            self.dlg.widgetLoading.setShown(True)
            self.emission_calculator.coordinates = self.dlg.lineEditStartX.text() + "," + self.dlg.lineEditStartY.text() + \
                                                   ";" + self.dlg.lineEditEndX.text() + "," + self.dlg.lineEditEndY.text()
            self.emission_calculator.length = self.dlg.lineEditLength.text()
            self.emission_calculator.height = self.dlg.lineEditHeight.text()

            self.overlay.show()

            # self.roadTask.coord = self.emission_calculator.coordinates
            # self.roadTask.length = self.emission_calculator.length
            # self.roadTask.height = self.emission_calculator.height
            # self.roadTask.load = self.dlg.cmbBoxLoad.currentText()
            self.roadTask.set_calculator_lib(self.emission_calculator)
            self.roadTask.start()

    def onRoadFinished(self):
        self.overlay.hide()
        # self.emission_calculator.set_data(data)
        self.get_roads()
        self.dlg.widgetLoading.setShown(False)

    def get_roads(self):
        # print self.dlg.lblStartPoint.text()+";"+self.dlg.lblEndPoint.text()
        self.remove_layer("Route")
        self.dlg.textEditSummary.clear()
        # self.dlg.textEditSummary.append("Test")

        # self.emission_calculator.coordinates = self.dlg.lblStartPoint.text() + ";" + self.dlg.lblEndPoint.text()
        # self.emission_calculator.coordinates = self.dlg.lineEditStartX.text() + "," + self.dlg.lineEditStartY.text() + \
        #                                        ";" + self.dlg.lineEditEndX.text() + "," + self.dlg.lineEditEndY.text()
        # self.emission_calculator.length = self.dlg.lineEditLength.text()
        # self.emission_calculator.height = self.dlg.lineEditHeight.text()
        # self.emission_calculator.get_json_from_url()

        paths = self.emission_calculator.paths
        if len(paths) > 0:
            for j in range(len(paths)):

                self.dlg.textEditSummary.append("Route" + str(j + 1) + ":")
                distance = self.emission_calculator.atr_distances[j]/1000
                hours, minutes = divmod(self.emission_calculator.atr_times[j], 60)
                hours = int(hours)
                minutes = int(minutes)
                self.dlg.textEditSummary.append("Length: " + str(distance) + " km, driving time: " + str(hours) + " hours and " + str(minutes) + " minutes." )
                self.dlg.textEditSummary.append("")

                ## create an empty memory layer
                vl = QgsVectorLayer("LineString", "Route" + str(j + 1), "memory")
                ## define and add a field ID to memory layer "Route"
                provider = vl.dataProvider()
                provider.addAttributes([QgsField("ID", QVariant.Int)])
                ## create a new feature for the layer "Route"
                ft = QgsFeature()
                ## set the value 1 to the new field "ID"
                ft.setAttributes([1])
                line_points = []
                for i in range(len(paths[j])):
                    # if j == 0:
                    if (i + 1) < len(paths[j]):
                        line_points.append(QgsPoint(paths[j][i][0], paths[j][i][1]))
                ## set the geometry defined from the point X: 50, Y: 100
                ft.setGeometry(QgsGeometry.fromPolyline(line_points))
                ## finally insert the feature
                provider.addFeatures([ft])

                ## set color
                symbols = vl.rendererV2().symbols()
                sym = symbols[0]
                if j < (len(self.color_list) - 1):
                    color = self.color_list[j]
                    sym.setColor(QColor.fromRgb(color[0], color[1], color[2]))
                sym.setWidth(2)

                ## add layer to the registry and over the map canvas
                QgsMapLayerRegistry.instance().addMapLayer(vl)

            self.activate_group_box_calculator(True)
        else:
            self.dlg.textEditSummary.append("Sorry, for defined parameters no road is available.")
            self.dlg.textEditSummary.append("")
            self.activate_group_box_calculator(False)

    def onEmissionStart(self):
        self.dlg.widgetLoading.setShown(True)
        self.overlay.show()

        self.emission_calculator.calculate_nox = self.dlg.checkBoxNox.isChecked()
        self.emission_calculator.calculate_co = self.dlg.checkBoxCo.isChecked()
        self.emission_calculator.calculate_hc = self.dlg.checkBoxHc.isChecked()
        self.emission_calculator.calculate_pm = self.dlg.checkBoxPm.isChecked()
        self.emission_calculator.calculate_fc = self.dlg.checkBoxFc.isChecked()

        self.emission_calculator.show_in_graph = self.dlg.checkBoxShowInGraph.isChecked()
        self.emission_calculator.cumulative = self.dlg.checkBoxCumulative.isChecked()

        self.emissionTask.set_calculator_lib(self.emission_calculator)


        self.emissionTask.start()

    def onEmissionFinished(self):
        # self.emission_calculator.set_emissions_for_pollutant(data)
        # print self.emission_calculator.get_emissions_for_pollutant()
        self.overlay.hide()
        self.dlg.widgetLoading.setShown(False)
        self.get_emissions()

    def get_emissions(self):

        # self.emission_calculator.calculate_nox = self.dlg.checkBoxNox.isChecked()
        # self.emission_calculator.calculate_co = self.dlg.checkBoxCo.isChecked()
        # self.emission_calculator.calculate_hc = self.dlg.checkBoxHc.isChecked()
        # self.emission_calculator.calculate_pm = self.dlg.checkBoxPm.isChecked()
        # self.emission_calculator.calculate_fc = self.dlg.checkBoxFc.isChecked()
        #
        # self.emission_calculator.show_in_graph = self.dlg.checkBoxShowInGraph.isChecked()
        # self.emission_calculator.cumulative = self.dlg.checkBoxCumulative.isChecked()
        # self.emission_calculator.calculate_emissions()
        self.emission_calculator.show_emissions()
        # update summary tab with data

        statistics = self.emission_calculator.statistics
        self.dlg.textEditSummary.append("------------------------------------------")
        self.dlg.textEditSummary.append("Emission results:")
        self.dlg.textEditSummary.append("")
        for i in range(len(statistics)):
            self.dlg.textEditSummary.append("Route" + str(i + 1) + ":")
            if "NOx" in statistics[i]:
                self.dlg.textEditSummary.append("NOx: " + str(statistics[i]['NOx']))
            if "CO" in statistics[i]:
                self.dlg.textEditSummary.append("CO: " + str(statistics[i]['CO']))
            if "HC" in statistics[i]:
                self.dlg.textEditSummary.append("HC: " + str(statistics[i]['HC']))
            if "PM" in statistics[i]:
                self.dlg.textEditSummary.append("PM: " + str(statistics[i]['PM']))
            if "FC" in statistics[i]:
                self.dlg.textEditSummary.append("FC: " + str(statistics[i]['FC']))
            self.dlg.textEditSummary.append("")

    def run(self):
        """Run method that performs all the real work"""
        # set input parameters to default when the dialog has been closed and open again
        self.dlg.cmbBoxType.clear()
        self.dlg.cmbBoxType.addItems(self.emission_calculator.emissionJson.get_types())
        self.dlg.cmbBoxLoad.clear()
        self.dlg.cmbBoxLoad.addItems(["0", "50", "100"])
        self.dlg.lineEditStartX.setText("")
        self.dlg.lineEditStartY.setText("")
        self.dlg.lineEditEndX.setText("")
        self.dlg.lineEditEndY.setText("")
        self.dlg.lineEditHeight.setText(self.emission_calculator.height)
        self.dlg.lineEditLength.setText(self.emission_calculator.length)
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
            pass
