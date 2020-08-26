import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .htmlExpansionAlgorithm import HTMLExpansionAlgorithm
from .importKml import ImportKmlAlgorithm
from .exportKmz import ExportKmzAlgorithm

class KmlToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(HTMLExpansionAlgorithm())
        self.addAlgorithm(ImportKmlAlgorithm())
        self.addAlgorithm(ExportKmzAlgorithm())
        
    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/icon.png')
        
    def id(self):
        return 'kmltools'

    def name(self):
        return 'KML tools'

    def longName(self):
        return self.name()
