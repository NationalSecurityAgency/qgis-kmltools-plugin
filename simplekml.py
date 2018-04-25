# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SimpleKML
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
from PyQt4.QtGui import QIcon, QAction

import os
from .simpleKMLDialog import SimpleKMLDialog
from .htmlExpansionDialog import HTMLExpansionDialog

class SimpleKML:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.htmlDialog = None

    def initGui(self):
        """Create the menu & tool bar items within QGIS"""
        icon = QIcon(os.path.dirname(__file__) + "/icon.png")
        self.kmlAction = QAction(icon, u"Simple KML Importer", self.iface.mainWindow())
        self.kmlAction.triggered.connect(self.showDialog)
        self.kmlAction.setCheckable(False)
        self.iface.addToolBarIcon(self.kmlAction)
        self.iface.addPluginToVectorMenu(u"KML Tools", self.kmlAction)
        # Expansion of HTML description field
        icon = QIcon(os.path.dirname(__file__) + "/html.png")
        self.htmlDescAction = QAction(icon, u"Expand HTML Description Field", self.iface.mainWindow())
        self.htmlDescAction.triggered.connect(self.htmlDescDialog)
        self.htmlDescAction.setCheckable(False)
        self.iface.addToolBarIcon(self.htmlDescAction)
        self.iface.addPluginToVectorMenu(u"KML Tools", self.htmlDescAction)

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginVectorMenu(u"KML Tools", self.kmlAction)
        self.iface.removePluginVectorMenu(u"KML Tools", self.htmlDescAction)
        self.iface.removeToolBarIcon(self.kmlAction)
        self.iface.removeToolBarIcon(self.htmlDescAction)
    
    def showDialog(self):
        """Display the KML Dialog window."""
        if not self.dialog:
            self.dialog = SimpleKMLDialog(self.iface)
        self.dialog.show()
    
    def htmlDescDialog(self):
        """Display the KML Dialog window."""
        if not self.htmlDialog:
            self.htmlDialog = HTMLExpansionDialog(self.iface)
        self.htmlDialog.show()
        
        
