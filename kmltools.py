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
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication, Qgis
import processing

import os
from .settings import settings
from .provider import KmlToolsProvider

class KMLTools(object):
    def __init__(self, iface):
        self.iface = iface
        self.htmlDialog = None
        self.provider = KmlToolsProvider()
        settings.canvas = iface.mapCanvas()

    def initGui(self):
        """Create the menu & tool bar items within QGIS"""
        self.toolbar = self.iface.addToolBar('KML Tools Toolbar')
        self.toolbar.setObjectName('KMLToolsToolbar')
        self.toolbar.setToolTip('KML Tools Toolbar')

        icon = QIcon(os.path.dirname(__file__) + "/icons/import.svg")
        self.kmlAction = QAction(icon, "Import KML/KMZ", self.iface.mainWindow())
        self.kmlAction.triggered.connect(self.showDialog)
        self.kmlAction.setCheckable(False)
        self.toolbar.addAction(self.kmlAction)
        self.iface.addPluginToVectorMenu("KML Tools", self.kmlAction)
        # Export KML Menu
        icon = QIcon(os.path.dirname(__file__) + "/icons/export.svg")
        self.kmlExportAction = QAction(icon, "Export KMZ", self.iface.mainWindow())
        self.kmlExportAction.triggered.connect(self.exportKMZ)
        self.kmlExportAction.setCheckable(False)
        self.toolbar.addAction(self.kmlExportAction)
        self.iface.addPluginToVectorMenu("KML Tools", self.kmlExportAction)
        # Expansion of HTML description field
        icon = QIcon(os.path.dirname(__file__) + "/icons/html.svg")
        self.htmlDescAction = QAction(icon, "Expand HTML description field", self.iface.mainWindow())
        self.htmlDescAction.triggered.connect(self.htmlDescDialog)
        self.htmlDescAction.setCheckable(False)
        self.toolbar.addAction(self.htmlDescAction)
        self.iface.addPluginToVectorMenu("KML Tools", self.htmlDescAction)
        if Qgis.QGIS_VERSION_INT >= 31400:
            # Extract KML/KMZ Ground Overlays
            icon = QIcon(os.path.dirname(__file__) + "/icons/gnd_overlay_import.svg")
            self.extractGndAction = QAction(icon, "Extract KML/KMZ Ground Overlays", self.iface.mainWindow())
            self.extractGndAction.triggered.connect(self.extractGroundOverlays)
            self.extractGndAction.setCheckable(False)
            self.iface.addPluginToRasterMenu("KML Tools", self.extractGndAction)
            self.toolbar.addAction(self.extractGndAction)

            icon = QIcon(os.path.dirname(__file__) + "/icons/gnd_overlay.svg")
            self.createGndAction = QAction(icon, "Create Ground Overlay GeoTIFF Image", self.iface.mainWindow())
            self.createGndAction.triggered.connect(self.createGroundOverlayGeoTIFF)
            self.createGndAction.setCheckable(False)
            self.iface.addPluginToRasterMenu("KML Tools", self.createGndAction)
            self.toolbar.addAction(self.createGndAction)
        # Help
        icon = QIcon(os.path.dirname(__file__) + '/icons/help.svg')
        self.helpAction = QAction(icon, "Help", self.iface.mainWindow())
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu('KML Tools', self.helpAction)
        if Qgis.QGIS_VERSION_INT >= 31400:
            self.iface.addPluginToRasterMenu('KML Tools', self.helpAction)

        # Add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginVectorMenu("KML Tools", self.kmlAction)
        self.iface.removePluginVectorMenu("KML Tools", self.kmlExportAction)
        self.iface.removePluginVectorMenu("KML Tools", self.htmlDescAction)
        self.iface.removePluginVectorMenu("KML Tools", self.helpAction)
        self.kmlAction.deleteLater()
        self.kmlAction = None
        self.kmlExportAction.deleteLater()
        self.kmlExportAction = None
        self.htmlDescAction.deleteLater()
        self.htmlDescAction = None
        if Qgis.QGIS_VERSION_INT >= 31400:
            self.iface.removePluginRasterMenu("KML Tools", self.extractGndAction)
            self.iface.removePluginRasterMenu("KML Tools", self.createGndAction)
            self.iface.removePluginRasterMenu("KML Tools", self.helpAction)
            self.extractGndAction.deleteLater()
            self.extractGndAction = None
            self.createGndAction.deleteLater()
            self.createGndAction = None
        self.toolbar.deleteLater()
        self.toolbar = None
        QgsApplication.processingRegistry().removeProvider(self.provider)

    def showDialog(self):
        """Display the KML Dialog window."""
        processing.execAlgorithmDialog('kmltools:importkml', {})

    def exportKMZ(self):
        """Display the KML Dialog window."""
        processing.execAlgorithmDialog('kmltools:exportkmz', {})

    def extractGroundOverlays(self):
        """Display the KML Dialog window."""
        processing.execAlgorithmDialog('kmltools:extractgroundoverlays', {})

    def createGroundOverlayGeoTIFF(self):
        """Display the KML Dialog window."""
        processing.execAlgorithmDialog('kmltools:groundoverlay2geotiff', {})

    def htmlDescDialog(self):
        """Display the KML Dialog window."""
        if not self.htmlDialog:
            from .htmlExpansionDialog import HTMLExpansionDialog
            self.htmlDialog = HTMLExpansionDialog(self.iface)
        self.htmlDialog.show()

    def help(self):
        '''Display a help page'''
        import webbrowser
        url = QUrl.fromLocalFile(os.path.dirname(__file__) + "/index.html").toString()
        webbrowser.open(url, new=2)
