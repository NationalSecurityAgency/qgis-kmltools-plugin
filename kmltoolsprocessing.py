# -*- coding: utf-8 -*-
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
