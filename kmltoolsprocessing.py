# -*- coding: utf-8 -*-
"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import QgsApplication
from .provider import KmlToolsProvider

class KMLTools(object):
    def __init__(self):
        self.provider = None

    def initProcessing(self):
        self.provider = KmlToolsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
