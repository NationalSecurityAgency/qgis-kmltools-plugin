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

import os
from qgis.PyQt.QtCore import QObject, QVariant, QCoreApplication, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QIcon

from qgis import processing

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsPointXY, QgsRasterLayer, QgsProject,
    QgsLineString, QgsMultiLineString, QgsPolygon, QgsMultiPolygon,
    QgsFeature, QgsGeometry, QgsFields, QgsField, QgsWkbTypes)

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber,
    QgsProcessingException,
    QgsProcessingParameterFileDestination)

from zipfile import ZipFile
import xml.sax
import xml.sax.handler
import traceback

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")

def tr(string):
    return QCoreApplication.translate('Processing', string)

class CreateGroundOverlayGeoTiffAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to import KML and KMZ files.
    """
    PrmInput = 'Input'
    PrmOutputRaster  = 'OutputRaster'
    PrmNorthLatitude = 'NorthLatitude'
    PrmSouthLatitude = 'SouthLatitude'
    PrmEastLongitude = 'EastLongitude'
    PrmWestLongitude = 'WestLongitude'
    PrmRotation      = 'Rotation'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.PrmInput,
                tr('Input image'))
        )
        param = QgsProcessingParameterNumber(
            self.PrmNorthLatitude,
            tr('North latitude'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setMetadata({'widget_wrapper': { 'decimals': 14 }})
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmSouthLatitude,
            tr('South latitude'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setMetadata({'widget_wrapper': { 'decimals': 14 }})
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmEastLongitude,
            tr('East longitude'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setMetadata({'widget_wrapper': { 'decimals': 14 }})
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmWestLongitude,
            tr('West longitude'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setMetadata({'widget_wrapper': { 'decimals': 14 }})
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmRotation,
            tr('Rotation'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setMetadata({'widget_wrapper': { 'decimals': 14 }})
        self.addParameter(param)

        param=QgsProcessingParameterFileDestination(
            self.PrmOutputRaster,
            tr('Output GeoTIFF Image'),
            optional=False)
        param.setFileFilter('*.tif')
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, feedback):
        raster =  self.parameterAsRasterLayer(parameters, self.PrmInput, context)
        out_path = self.parameterAsOutputLayer(parameters, self.PrmOutputRaster, context)
        north = self.parameterAsDouble(parameters, self.PrmNorthLatitude, context)
        south = self.parameterAsDouble(parameters, self.PrmSouthLatitude, context)
        east = self.parameterAsDouble(parameters, self.PrmEastLongitude, context)
        west = self.parameterAsDouble(parameters, self.PrmWestLongitude, context)
        rotation = self.parameterAsDouble(parameters, self.PrmRotation, context)

        if rotation == 0:
            status = processing.run("gdal:translate", {'INPUT': raster,
                    'EXTRA': '-a_srs EPSG:4326 -a_ullr {} {} {} {}'.format(west, north, east, south),
                    'DATA_TYPE': 0,
                    'OUTPUT': out_path})
        else:
            rwidth = raster.width()
            rheight = raster.height()
            center_x = (east + west) / 2.0
            center_y = (north + south)/ 2.0
            center_pt = QgsPointXY(center_x, center_y)
            ul_pt = QgsPointXY(west, north)
            ur_pt = QgsPointXY(east, north)
            lr_pt = QgsPointXY(east, south)
            ll_pt = QgsPointXY(west, south)
            distance = center_pt.distance(ul_pt)
            az = center_pt.azimuth(ul_pt) - rotation
            pt1 = center_pt.project(distance, az)
            az = center_pt.azimuth(ur_pt) - rotation
            pt2 = center_pt.project(distance, az)
            az = center_pt.azimuth(lr_pt) - rotation
            pt3 = center_pt.project(distance, az)
            az = center_pt.azimuth(ll_pt) - rotation
            pt4 = center_pt.project(distance, az)
            gcp1= '-gcp {} {} {} {}'.format(0,0, pt1.x(), pt1.y())
            gcp2= '-gcp {} {} {} {}'.format(rwidth,0, pt2.x(), pt2.y())
            gcp3= '-gcp {} {} {} {}'.format(rwidth, rheight, pt3.x(), pt3.y())
            gcp4= '-gcp {} {} {} {}'.format(0, rheight, pt4.x(), pt4.y())
            

            status = processing.run("gdal:translate", {'INPUT': raster,
                    'EXTRA': '-a_srs EPSG:4326 -a_nodata 0,0,0 {} {} {} {}'.format(gcp1, gcp2, gcp3, gcp4),
                    'DATA_TYPE': 0,
                    'OUTPUT': out_path})
        feedback.pushInfo('{}'.format(status))
        results = {}
        results[self.PrmOutputRaster] = out_path
        return (results)

    def name(self):
        return 'groundoverlay2geotiff'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/gnd_overlay.svg')

    def displayName(self):
        return tr('Ground Overlay to GeoTIFF Image')

    def group(self):
        return tr('Raster conversion')

    def groupId(self):
        return 'rasterconversion'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def shortHelpString(self):
        file = os.path.dirname(__file__) + '/doc/gndoverlay2tiff.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return CreateGroundOverlayGeoTiffAlgorithm()
