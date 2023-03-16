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
    QgsProcessingParameterFile,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
    QgsProcessingParameterFolderDestination)

from zipfile import ZipFile
import xml.sax
import xml.sax.handler
import traceback

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")

def tr(string):
    return QCoreApplication.translate('Processing', string)

class ConvertGroundOverlayAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to import KML and KMZ files.
    """
    PrmInput = 'Input'
    PrmGroundOverlayFolder = 'GroundOverlayFolder'
    PrmLoadGeoTiffs = 'LoadGeoTiffs'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PrmInput,
                tr('Input KML/KMZ file'))
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.PrmGroundOverlayFolder,
                tr('Output folder for KML/KMZ Ground Overlay Images'),
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmLoadGeoTiffs,
                'Automatically load converted GeoTIFFs into QGIS',
                True,
                optional=True)
        )

    def processAlgorithm(self, parameters, context, feedback):
        self.parameters = parameters
        self.context = context
        self.feedback = feedback
        load_geotiffs = self.parameterAsInt(parameters, self.PrmLoadGeoTiffs, context)
        out_folder = self.parameterAsFile(parameters, self.PrmGroundOverlayFolder, context)
        input_file = self.parameterAsFile(parameters, self.PrmInput, context)
        f, extension = os.path.splitext(input_file)
        dirname = os.path.dirname(input_file)
        extension = extension.lower()
        try:
            if extension == '.kmz':
                kmz = ZipFile(input_file, 'r')
                kml = kmz.open('doc.kml', 'r')
            elif extension == '.kml':
                kml = open(input_file, encoding="utf-8", errors="backslashreplace")
            else:
                msg = "Invalid extension: Should be kml or kmz"
                raise QgsProcessingException(msg)
        except Exception:
            msg = "Failed to open file"
            raise QgsProcessingException(msg)

        parser = xml.sax.make_parser()

        self.overlays = []
        # Set up the handler for doing the main processing
        handler = GroundOverlayHandler(feedback)
        handler.groundoverlay.connect(self.groundoverlay)
        parser.setContentHandler(handler)
        try:
            input_source = xml.sax.xmlreader.InputSource()
            input_source.setByteStream(kml)
            input_source.setEncoding('utf-8')
            parser.parse(input_source)
        except Exception:
            '''s = traceback.format_exc()
            feedback.pushInfo(s)'''
            feedback.reportError(tr('Failure in kml extraction - May return partial results.'))
            handler.endDocument()

        self.namelist = set()
        # Iterate through each found overlay images
        for overlay in self.overlays:
            if feedback.isCanceled():
                break
            north = overlay[0]
            south = overlay[1]
            east = overlay[2]
            west = overlay[3]
            rotation = overlay[4]
            href = overlay[5]
            if href.startswith('http:') or href.startswith('https:'):
                feedback.reportError('Cannot process network images: {}'.format(href))
                continue
            if extension == '.kmz':
                try:
                    image = kmz.read(href)
                    output_file = os.path.basename(href)
                    # Could use this method to prevent multiple names overwriting each other
                    # Could be problematic if these are abloslute path filenames on the computer
                    # (out_dir, output_file) = os.path.split(href)
                    # '_'.join(out_dir.replace('\\', '/').split('/'))
                    file_name, ext = os.path.splitext(output_file)
                    # Write out a temporary image
                    temp_file_name = os.path.join(out_folder,'{}_temp{}'.format(file_name, ext))
                    fp = open(temp_file_name, "wb")
                    fp.write(image)
                    fp.close()
                    raster = QgsRasterLayer(temp_file_name, "temp")
                except Exception:
                    feedback.reportError('Image does not exist: {}'.format(href))
                    continue
            else:
                # Check to see if it is a valid file name
                in_path = os.path.join(dirname, href)
                if not os.path.isfile(in_path):
                    # The path was not valid
                    feedback.reportError('Image file does not exist: {}'.format(in_path))
                    continue
                raster = QgsRasterLayer(in_path, "temp")
                output_file = os.path.basename(in_path)
                file_name, ext = os.path.splitext(output_file)
            if not raster.isValid():
                feedback.reportError('Invalid raster image: {}'.format(href))
                continue
            # Make sure the name is unique so the images are not overwritten
            file_name = self.uniqueName(file_name)
            out_path = os.path.join(out_folder, file_name+".tif")
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
            if load_geotiffs:
                context.addLayerToLoadOnCompletion(
                    out_path,
                    context.LayerDetails(
                        file_name,
                        project=context.project()
                    ))
                
            del raster
            if extension == '.kmz':
                try:
                    os.remove(temp_file_name)
                    os.remove(temp_file_name+'.aux.xml')
                except Exception:
                    pass

        if extension == '.kmz':
            kmz.close()
        else:
            kml.close()
            
        # self.feedback.pushInfo('Number of overlays: {}'.format(len(self.overlays)))

        return ({})

    def uniqueName(self, name):
        index = 1
        n = name
        while n in self.namelist:
            n = '{}_{}'.format(name, index)
            index += 1
        # Keep track of all of the used names
        self.namelist.add(n)
        return (n)

    def groundoverlay(self, north, south, east, west, rotation, href):
        # self.feedback.pushInfo('In groundoverlay')
        try:
            if north:
                north = float(north)
            else:
                north = 0.0
            if south:
                south = float(south)
            else:
                south = 0.0
            if east:
                east = float(east)
            else:
                east = 0.0
            if west:
                west = float(west)
            else:
                west = 0.0
            if rotation:
                rotation = float(rotation)
            else:
                rotation = 0.0
            self.overlays.append([north, south, east, west, rotation, href])
        except Exception:
            '''s = traceback.format_exc()
            feedback.pushInfo(s)'''
            pass
            

    def name(self):
        return 'extractgroundoverlays'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/gnd_overlay_import.svg')

    def displayName(self):
        return tr('Extract KML/KMZ Ground Overlays')

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
        file = os.path.dirname(__file__) + '/doc/extractgndoverlays.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return ConvertGroundOverlayAlgorithm()

class GroundOverlayHandler(xml.sax.handler.ContentHandler, QObject):
    groundoverlay = pyqtSignal(str, str, str, str, str, str)

    def __init__(self, feedback):
        QObject.__init__(self)
        xml.sax.handler.ContentHandler.__init__(self)
        self.schema = {}
        self.feedback = feedback

        self.resetSettings()

    def resetSettings(self):
        '''Set all settings to a default new placemark.'''
        self.inGroundOverlay = False
        self.inNorth = False
        self.inSouth = False
        self.inEast = False
        self.inWest = False
        self.inRotation = False
        self.inHref = False
        self.north = ""
        self.south = ""
        self.east = ""
        self.west = ""
        self.rotation = ""
        self.href = ""

    def startElement(self, name, attr):
        if name.startswith('kml:'):
            name = name[4:]

        if name == "GroundOverlay":
            self.inGroundOverlay = True
        elif self.inGroundOverlay:
            if name == "north":
                self.inNorth = True
                self.north = ""
            elif name == "south":
                self.inSouth = True
                self.south = ""
            elif name == "east":
                self.inEast = True
                self.east = ""
            elif name == "west":
                self.inWest = True
                self.west = ""
            elif name == "rotation":
                self.inRotation = True
                self.rotation = ""
            elif name == "href":
                self.inHref = True
                self.href = ""

    def characters(self, data):
        if self.inNorth:  # on text within tag
            self.north += data
        elif self.inSouth:
            self.south += data
        elif self.inEast:
            self.east += data
        elif self.inWest:
            self.west += data
        elif self.inRotation:
            self.rotation += data
        elif self.inHref:
            self.href += data

    def endElement(self, name):
        if name.startswith('kml:'):
            name = name[4:]
        if self.inGroundOverlay:
            if name == "north":
                self.inNorth = False  # on end title tag
                self.north = self.north.strip()
            elif name == "south":
                self.inSouth = False
                self.south = self.south.strip()
            elif name == "east":
                self.inEast = False
                self.east = self.east.strip()
            elif name == "west":
                self.inWest = False
                self.west = self.west.strip()
            elif name == "rotation":
                self.inRotation = False
                self.rotation = self.rotation.strip()
            elif name == "href":
                self.inHref = False
                self.href = self.href.strip()
            elif name == 'GroundOverlay':
                self.inGroundOverlay = False
                self.groundoverlay.emit(self.north, self.south, self.east, self.west, self.rotation, self.href)

