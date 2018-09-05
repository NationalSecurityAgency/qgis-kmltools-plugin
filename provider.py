import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .htmlExpansionDialog import HTMLExpansionAlgorithm
from .importKml import ImportKmlAlgorithm

class KmlToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(HTMLExpansionAlgorithm())
        self.addAlgorithm(ImportKmlAlgorithm())
        
    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icon.png')
        
    def id(self):
        return 'kmltools'

    def name(self):
        return 'KML tools'

    def longName(self):
        return self.name()
