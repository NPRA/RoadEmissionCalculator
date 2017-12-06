# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TheWidgetItem
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

import os
import sys

from PyQt4 import QtGui, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'thewidgetitem.ui'))


class TheWidgetItem(QtGui.QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(TheWidgetItem, self).__init__(parent)

        self.setupUi(self)

        self.labels = [self.lblPlt1, self.lblPlt2, self.lblPlt3, self.lblPlt4, self.lblPlt5, self.lblPlt6]

        self.textQVBoxLayout = QtGui.QVBoxLayout()
        self.allQHBoxLayout = QtGui.QHBoxLayout()
        verticalSpacer = QtGui.QSpacerItem(0, 70, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.textQVBoxLayout.addItem(verticalSpacer)
        self.allQHBoxLayout.addLayout(self.textQVBoxLayout)
        self.route_id = -1
        self.setLayout(self.allQHBoxLayout)
        # self.lblErrorMsg.hide()
        if sys.platform == "linux2":
            for label in self.labels:
                label.setFont(QtGui.QFont('SansSerif', 10))

    def set_route_name(self, text, color):
        # self.lblErrorMsg.hide()
        self.lblRouteName.setText(text)
        self.lblRouteName.setStyleSheet('color: rgb('+str(color[0])+','+str(color[1])+','+str(color[2])+')')

    def set_route_id(self, id):
        self.route_id = id

    def set_distance_time(self, distance, time):
        self.lblDistanceTime.show()
        self.lblDistanceTime.setText("Distance: {}, time: {}".format(distance, time))

    def set_error_msg(self, msg):
        self.lblRouteName.hide()
        self.lblDistanceTime.hide()
        self.hide_all_lbl_pollutants()
        # self.lblErrorMsg.show()
        # self.lblErrorMsg.setText(msg)

    def hide_all_lbl_pollutants(self):
        for label in self.labels:
            label.setText("")
            label.hide()

    def set_pollutants(self, idx, plt, value):
        label = self.labels[idx]
        label.setText("{}: {}".format(plt, value))
        label.show()
