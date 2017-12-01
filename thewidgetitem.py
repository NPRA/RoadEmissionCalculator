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

from PyQt4 import QtGui, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'thewidgetitem.ui'))


class TheWidgetItem(QtGui.QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(TheWidgetItem, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        #widgets-and-dialogs-with-auto-connect

        self.setupUi(self)

        self.labels = [self.lblPlt1, self.lblPlt2, self.lblPlt3, self.lblPlt4, self.lblPlt5, self.lblPlt6]

        self.textQVBoxLayout = QtGui.QVBoxLayout()
        # self.textQVBoxLayout.addWidget(self.label)
        # self.textQVBoxLayout.addWidget(self.label_2)
        self.allQHBoxLayout = QtGui.QHBoxLayout()
        # self.textDownQLabel = QtGui.QLabel()
        # self.textDownQLabel.setMinimumHeight(90)

        # self.textQVBoxLayout.addWidget(self.textDownQLabel)
        # self.allQHBoxLayout.addWidget(self.label)
        # self.allQHBoxLayout.addWidget(self.label_2, 2)
        verticalSpacer = QtGui.QSpacerItem(0, 60, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.textQVBoxLayout.addItem(verticalSpacer)
        self.allQHBoxLayout.addLayout(self.textQVBoxLayout)
        # self.itemClicked.connect(self.item_click)
        self.route_id = -1
        self.setLayout(self.allQHBoxLayout)
        self.lblErrorMsg.hide()

    def set_route_name(self, text, color):
        self.lblErrorMsg.hide()
        self.lblRouteName.setText(text)
        self.lblRouteName.setStyleSheet('color: rgb('+str(color[0])+','+str(color[1])+','+str(color[2])+')')

    def set_route_id(self, id):
        self.route_id = id

    def set_distance_time(self, distance, time):
        self.lblDistanceTime.show()
        self.lblDistanceTime.setText("Distance: {}, driving time: {}".format(distance, time))

    def set_error_msg(self, msg):
        self.lblRouteName.hide()
        self.lblDistanceTime.hide()
        self.hide_all_lbl_pollutants()
        self.lblErrorMsg.show()
        self.lblErrorMsg.setText(msg)

    def hide_all_lbl_pollutants(self):
        for label in self.labels:
            label.setText("")
            label.hide()

    def set_pollutants(self, idx, plt, value):
        label = self.labels[idx]
        label.setText("{}: {}".format(plt, value))
        label.show()
