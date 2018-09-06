# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KMLTools
    A QGIS plugin for importing KML into simple points, lines, and polygons.
    It ignores KML styling.
                              -------------------
        begin                : 2018-03-16
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
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication
import processing

import os
from .provider import KmlToolsProvider
from .htmlExpansionDialog import HTMLExpansionDialog

class KMLTools(object):
    def __init__(self, iface):
        self.iface = iface
        self.htmlDialog = None
        self.provider = KmlToolsProvider()        

    def initGui(self):
        """Create the menu & tool bar items within QGIS"""
        icon = QIcon(os.path.dirname(__file__) + "/icon.png")
        self.kmlAction = QAction(icon, "Simple KML Importer", self.iface.mainWindow())
        self.kmlAction.triggered.connect(self.showDialog)
        self.kmlAction.setCheckable(False)
        self.iface.addToolBarIcon(self.kmlAction)
        self.iface.addPluginToVectorMenu("KML Tools", self.kmlAction)
        # Expansion of HTML description field
        icon = QIcon(os.path.dirname(__file__) + "/html.png")
        self.htmlDescAction = QAction(icon, "Expand HTML Description Field", self.iface.mainWindow())
        self.htmlDescAction.triggered.connect(self.htmlDescDialog)
        self.htmlDescAction.setCheckable(False)
        self.iface.addToolBarIcon(self.htmlDescAction)
        self.iface.addPluginToVectorMenu("KML Tools", self.htmlDescAction)
        
        # Add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginVectorMenu("KML Tools", self.kmlAction)
        self.iface.removePluginVectorMenu("KML Tools", self.htmlDescAction)
        self.iface.removeToolBarIcon(self.kmlAction)
        self.iface.removeToolBarIcon(self.htmlDescAction)
        QgsApplication.processingRegistry().removeProvider(self.provider)
    
    def showDialog(self):
        """Display the KML Dialog window."""
        results = processing.execAlgorithmDialog('kmltools:importkml', {})
    
    def htmlDescDialog(self):
        """Display the KML Dialog window."""
        if not self.htmlDialog:
            self.htmlDialog = HTMLExpansionDialog(self.iface)
        self.htmlDialog.show()
        
        