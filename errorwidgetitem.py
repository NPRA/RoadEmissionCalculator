# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ErrorWidgetItem
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
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtWidgets import QWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'errorwidgetitem.ui'))


class ErrorWidgetItem(QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ErrorWidgetItem, self).__init__(parent)

        self.setupUi(self)

        self.textQVBoxLayout = QtGui.QVBoxLayout()
        self.allQHBoxLayout = QtGui.QHBoxLayout()
        verticalSpacer = QtGui.QSpacerItem(0, 70, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.textQVBoxLayout.addItem(verticalSpacer)
        self.allQHBoxLayout.addLayout(self.textQVBoxLayout)
        self.route_id = -1
        self.setLayout(self.allQHBoxLayout)

    def set_error_msg(self, text):
        self.lblErrorMsg.setText(text)
