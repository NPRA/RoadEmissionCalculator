# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RoadEmissionCalculator
                                 A QGIS plugin
 The plugin calculate emissons for selected roads.
                             -------------------
        begin                : 2017-08-08
        copyright            : (C) 2017 by Statens Vegvesen
        email                : tomas.levin@vegvesen.no
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load RoadEmissionCalculator class from file RoadEmissionCalculator.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .road_emission_calculator import RoadEmissionCalculator
    return RoadEmissionCalculator(iface)
