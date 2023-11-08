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
import os
from qgis.core import QgsProcessingProvider, Qgis
from qgis.PyQt.QtGui import QIcon
from .htmlExpansionAlgorithm import HTMLExpansionAlgorithm
from .importKml import ImportKmlAlgorithm
from .exportKmz import ExportKmzAlgorithm
if Qgis.QGIS_VERSION_INT >= 31400:
    from .convertGroundOverlays import ConvertGroundOverlayAlgorithm
    from .createGroundOverlayGeoTiff import CreateGroundOverlayGeoTiffAlgorithm

class KmlToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(HTMLExpansionAlgorithm())
        self.addAlgorithm(ImportKmlAlgorithm())
        self.addAlgorithm(ExportKmzAlgorithm())
        if Qgis.QGIS_VERSION_INT >= 31400:
            self.addAlgorithm(ConvertGroundOverlayAlgorithm())
            self.addAlgorithm(CreateGroundOverlayGeoTiffAlgorithm())
        
    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/import.svg')
        
    def id(self):
        return 'kmltools'

    def name(self):
        return 'KML tools'

    def longName(self):
        return self.name()
