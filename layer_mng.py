from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsPointXY, QgsPoint
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from qgis.core import QgsProject
from qgis.core import QgsRenderContext


def enum(**named_values):
    return type('Enum', (), named_values)


GeometryTypes = enum(POINT="Point", LINE="LineString")
LayerNames = enum(ROUTE="Route", SELECTED="Selected_route", STARTPOINT="Start_point", ENDPOINT="End_point")


class LayerMng(object):
    '''Layer manager is a class for creating and removing point and polyline layers. Created layers are presented
    in a map and legend.'''

    def __init__(self, iface):
        self.iface = iface

    def create_layer(self, points, layer_name, type_geometry, style_width, layer_id, color_list):
        # get default CRS
        canvas = self.iface.mapCanvas()
        map_settings = canvas.mapSettings()
        srs = map_settings.destinationCrs()

        # create an empty memory layer
        if layer_id is not None:
            vl = QgsVectorLayer(type_geometry + "?crs=" + srs.authid(), layer_name + str(layer_id + 1), "memory")
        else:
            vl = QgsVectorLayer(type_geometry + "?crs=" + srs.authid(), layer_name, "memory")

        # define and add a field ID to memory layer "Route"
        provider = vl.dataProvider()
        provider.addAttributes([QgsField("ID", QVariant.Int)])

        # create a new feature for the layer "Route"
        ft = QgsFeature()
        # set the value 1 to the new field "ID"
        ft.setAttributes([1])
        if type_geometry == GeometryTypes.LINE:
            line_points = []

            for i in range(len(points)):
                if (i + 1) < len(points):
                    line_points.append(QgsPoint(points[i][0], points[i][1]))
            # set the geometry defined from the point
            ft.setGeometry(QgsGeometry.fromPolyline(line_points))
        else:
            ft.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(points[0], points[1])))
        # finally insert the feature
        provider.addFeatures([ft])

        if type_geometry == GeometryTypes.LINE:
            # set color
            render_ctx = QgsRenderContext()
            renderer = vl.renderer()
            symbols = renderer.symbols(render_ctx)
            sym = symbols[0]

            if layer_id and color_list:
                color = color_list[layer_id]
                sym.setColor(QColor.fromRgb(color[0], color[1], color[2]))

            sym.setWidth(style_width)

        # add layer to the registry and over the map canvas
        # QgsMapLayerRegistry.instance().addMapLayer(vl)
        QgsProject.instance().addMapLayer(vl)

    @staticmethod
    def remove_layer(layer_name):
        lrs = QgsProject.instance().mapLayers()
        for i in range(len(list(lrs.keys()))):
            if layer_name in list(lrs.keys())[i]:
                QgsProject.instance().removeMapLayer(list(lrs.keys())[i])
