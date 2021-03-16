import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .htmlExpansionAlgorithm import HTMLExpansionAlgorithm
from .importKml import ImportKmlAlgorithm
from .exportKmz import ExportKmzAlgorithm
from .convertGroundOverlays import ConvertGroundOverlayAlgorithm
from .createGroundOverlayGeoTiff import CreateGroundOverlayGeoTiffAlgorithm

class KmlToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(HTMLExpansionAlgorithm())
        self.addAlgorithm(ImportKmlAlgorithm())
        self.addAlgorithm(ExportKmzAlgorithm())
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
