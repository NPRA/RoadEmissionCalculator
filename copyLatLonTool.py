from PyQt4.QtCore import Qt, pyqtSignal, QVariant, QSettings
from PyQt4.QtGui import QApplication, QAction
from qgis.core import QgsCoordinateTransform, QgsPoint
from qgis.gui import QgsMapTool, QgsMessageBar
from qgis.core import QgsVectorLayer, QgsField, QgsMapLayerRegistry, QgsFeature, QgsGeometry
from qgis.gui import QgsMapToolPan

from LatLon import LatLon
from layer_mng import LayerMng
import mgrs

class CopyLatLonTool(QgsMapTool):
    '''Class to interact with the map canvas to capture the coordinate
    when the mouse button is pressed and to display the coordinate in
    in the status bar.'''
    capturesig = pyqtSignal(QgsPoint)
    
    def __init__(self, settings, iface, dlg):
        QgsMapTool.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settings = settings
        self.latlon = LatLon()
        self.capture4326 = False
        self.dlg = dlg
        self.point_name = ""
        self.layer_mng = LayerMng(self.iface)
        
    def activate(self):
        '''When activated set the cursor to a crosshair.'''
        self.canvas.setCursor(Qt.CrossCursor)
        
    def formatCoord(self, pt, delimiter):
        '''Format the coordinate string according to the settings from
        the settings dialog.'''
        if self.settings.captureProjIsWgs84(): # ProjectionTypeWgs84
            # Make sure the coordinate is transformed to EPSG:4326
            canvasCRS = self.canvas.mapSettings().destinationCrs()
            if canvasCRS == self.settings.epsg4326:
                pt4326 = pt
            else:
                transform = QgsCoordinateTransform(canvasCRS, self.settings.epsg4326)
                pt4326 = transform.transform(pt.x(), pt.y())
            self.latlon.setCoord(pt4326.y(), pt4326.x())
            self.latlon.setPrecision(self.settings.dmsPrecision)
            if self.latlon.isValid():
                if self.settings.wgs84NumberFormat == self.settings.Wgs84TypeDMS: # DMS
                    if self.settings.coordOrder == self.settings.OrderYX:
                        msg = self.latlon.getDMS(delimiter)
                    else:
                        msg = self.latlon.getDMSLonLatOrder(delimiter)
                elif self.settings.wgs84NumberFormat == self.settings.Wgs84TypeDDMMSS: # DDMMSS
                    if self.settings.coordOrder == self.settings.OrderYX:
                        msg = self.latlon.getDDMMSS(delimiter)
                    else:
                        msg = self.latlon.getDDMMSSLonLatOrder(delimiter)
                elif self.settings.wgs84NumberFormat == self.settings.Wgs84TypeWKT: # WKT
                    msg = 'POINT({} {})'.format(self.latlon.lon, self.latlon.lat)
                else: # decimal degrees
                    if self.settings.coordOrder == self.settings.OrderYX:
                        msg = '{}{}{}'.format(self.latlon.lat,delimiter,self.latlon.lon)
                    else:
                        msg = '{}{}{}'.format(self.latlon.lon,delimiter,self.latlon.lat)
            else:
                msg = None
        elif self.settings.captureProjIsProjectCRS():
            # Projection in the project CRS
            if self.settings.otherNumberFormat == 0: # Numerical
                if self.settings.coordOrder == self.settings.OrderYX:
                    msg = '{}{}{}'.format(pt.y(),delimiter,pt.x())
                else:
                    msg = '{}{}{}'.format(pt.x(),delimiter,pt.y())
            else:
                msg = 'POINT({} {})'.format(pt.x(), pt.y())
        elif self.settings.captureProjIsCustomCRS():
            # Projection is a custom CRS
            canvasCRS = self.canvas.mapSettings().destinationCrs()
            customCRS = self.settings.captureCustomCRS()
            transform = QgsCoordinateTransform(canvasCRS, customCRS)
            pt = transform.transform(pt.x(), pt.y())
            if self.settings.otherNumberFormat == 0: # Numerical
                if self.settings.coordOrder == self.settings.OrderYX:
                    msg = '{}{}{}'.format(pt.y(),delimiter,pt.x())
                else:
                    msg = '{}{}{}'.format(pt.x(),delimiter,pt.y())
            else:
                msg = 'POINT({} {})'.format(pt.x(), pt.y())
        elif self.settings.captureProjIsMGRS():
            # Make sure the coordinate is transformed to EPSG:4326
            canvasCRS = self.canvas.mapSettings().destinationCrs()
            if canvasCRS == self.settings.epsg4326:
                pt4326 = pt
            else:
                transform = QgsCoordinateTransform(canvasCRS, self.settings.epsg4326)
                pt4326 = transform.transform(pt.x(), pt.y())
            try:
                msg = mgrs.toMgrs(pt4326.y(), pt4326.x())
            except:
                msg = None

        return msg
        
    def canvasMoveEvent(self, event):
        '''Capture the coordinate as the user moves the mouse over
        the canvas. Show it in the status bar.'''
        try:
            pt = self.toMapCoordinates(event.pos())
            msg = self.formatCoord(pt, ', ')
            formatString = self.coordFormatString()
            if msg == None:
                self.iface.mainWindow().statusBar().showMessage("")
            else:
                self.iface.mainWindow().statusBar().showMessage("{} - {}".format(msg,formatString))
        except:
            self.iface.mainWindow().statusBar().showMessage("")

    def coordFormatString(self):
        if self.settings.captureProjIsWgs84():
            if self.settings.wgs84NumberFormat == self.settings.Wgs84TypeDecimal:
                if self.settings.coordOrder == self.settings.OrderYX:
                    s = 'Lat Lon'
                else:
                    s = 'Lon Lat'
            elif self.settings.wgs84NumberFormat == self.settings.Wgs84TypeWKT:
                s = 'WKT'
            else:
                s = 'DMS'
        elif self.settings.captureProjIsProjectCRS():
            crsID = self.canvas.mapSettings().destinationCrs().authid()
            if self.settings.otherNumberFormat == 0: # Numerical
                if self.settings.coordOrder == self.settings.OrderYX:
                    s = '{} - Y,X'.format(crsID)
                else:
                    s = '{} - X,Y'.format(crsID)
            else: # WKT
                s = 'WKT'
        elif self.settings.captureProjIsMGRS():
            s = 'MGRS'
        elif self.settings.captureProjIsCustomCRS():
            if self.settings.otherNumberFormat == 0: # Numerical
                if self.settings.coordOrder == self.settings.OrderYX:
                    s = '{} - Y,X'.format(self.settings.captureCustomCRSID())
                else:
                    s = '{} - X,Y'.format(self.settings.captureCustomCRSID())
            else: # WKT
                s = 'WKT'
        else: # Should never happen
            s = ''
        return s
    
    def canvasReleaseEvent(self, event):
        '''Capture the coordinate when the mouse button has been released,
        format it, and copy it to the clipboard.'''
        try:
            result = None
            pt = self.toMapCoordinates(event.pos())
            if self.point_name == "Start_point":
                # self.dlg.lblStartPoint.setText(str(round(pt.x(),2)) + "," + str(round(pt.y(),2)))
                self.dlg.lineEditStartX.setText(str(round(pt.x(),2)))
                self.dlg.lineEditStartY.setText(str(round(pt.y(),2)))

            if self.point_name == "End_point":
                # self.dlg.lblEndPoint.setText(str(round(pt.x(),2)) + "," + str(round(pt.y(),2)))
                self.dlg.lineEditEndX.setText(str(round(pt.x(), 2)))
                self.dlg.lineEditEndY.setText(str(round(pt.y(), 2)))

            self.layer_mng.create_layer([pt.x(), pt.y()], self.point_name,"Point",None, None, None)
            self.canvas.unsetMapTool(self)
            # self.canvas.setCursor(Qt.ArrowCursor)
            self.iface.actionPan().trigger()
            # self.dlg.exec_()

        except Exception as e:
            self.iface.messageBar().pushMessage("", "Invalid coordinate: {}".format(e), level=QgsMessageBar.WARNING, duration=4)