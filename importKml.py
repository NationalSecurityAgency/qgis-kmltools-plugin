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
import re
from qgis.PyQt.QtCore import QObject, QVariant, QCoreApplication, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsCoordinateReferenceSystem, QgsPoint, QgsLineString, QgsMultiLineString, QgsPolygon, QgsMultiPolygon, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsWkbTypes

from qgis.core import (QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFeatureSink)

from zipfile import ZipFile
import xml.sax, xml.sax.handler
#import traceback

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")

def tr(string):
    return QCoreApplication.translate('Processing', string)


class ImportKmlAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to import KML and KMZ files.
    """
    PrmInput = 'Input'
    PrmPointOutputLayer = 'PointOutputLayer'
    PrmLineOutputLayer = 'LineOutputLayer'
    PrmPolygonOutputLayer = 'PolygonOutputLayer'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PrmInput,
                tr('Import KML/KMZ file'))
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmPointOutputLayer,
                tr('Output point layer'),
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmLineOutputLayer,
                tr('Output line layer'),
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmPolygonOutputLayer,
                tr('Output polygon layer'),
                optional=True)
            )

    def processAlgorithm(self, parameters, context, feedback):
        self.parameters = parameters
        self.context = context
        filename = self.parameterAsFile(parameters, self.PrmInput, context)
        f, extension = os.path.splitext(filename)
        extension = extension.lower()
        try:
            if extension == '.kmz':
                kmz = ZipFile(filename, 'r')
                kml = kmz.open('doc.kml', 'r')
            elif extension == '.kml':
                kml = open(filename, encoding="utf-8", errors="backslashreplace")
            else:
                msg = "Invalid extension: Should be kml or kmz"
                feedback.reportError(msg)
                raise QgsProcessingException(msg)
        except:
            msg = "Failed to open file"
            feedback.reportError(msg)
            raise QgsProcessingException(msg)

        skipPt = True if self.PrmPointOutputLayer not in parameters or parameters[self.PrmPointOutputLayer] is None else False
        skipline = True if self.PrmLineOutputLayer not in parameters or parameters[self.PrmLineOutputLayer] is None else False
        skipPoly = True if self.PrmPolygonOutputLayer not in parameters or parameters[self.PrmPolygonOutputLayer] is None else False
        self.cntPt = 0
        self.cntLine = 0
        self.cntPoly = 0
        parser = xml.sax.make_parser()
        # Do a pre-pass through the KML to see if there are any extended data fields
        preprocess = PreProcessHandler()
        parser.setContentHandler(preprocess)
        try:
            input_source = xml.sax.xmlreader.InputSource()
            input_source.setByteStream(kml)
            input_source.setEncoding('utf-8')
            parser.parse(input_source)
        except:
            preprocess.endDocument()
        # Reset the KML/KMZ file to the beginning. The handler seems to automatically close the file
        # which is why we are reopening it.
        if extension == '.kmz':
            kmz.close()
        else:
            kml.close()
        if extension == '.kmz':
            kmz = ZipFile(filename, 'r')
            kml = kmz.open('doc.kml', 'r')
        else:
            kml = open(filename, encoding="utf-8", errors="backslashreplace")
        
        # Set up the handler for doing the main processing
        self.extData = preprocess.getExtendedDataFields()
        self.extData.sort()
        self.extDataMap = {}
        index = 0
        for item in self.extData:
            self.extDataMap[item] = index
            index += 1
        handler = PlacemarkHandler(skipPt, skipline, skipPoly, self.extDataMap, feedback)
        handler.addpoint.connect(self.addpoint)
        handler.addline.connect(self.addline)
        handler.addpolygon.connect(self.addpolygon)
        parser.setContentHandler(handler)
        try:
            input_source = xml.sax.xmlreader.InputSource()
            input_source.setByteStream(kml)
            input_source.setEncoding('utf-8')
            parser.parse(input_source)
        except:
            '''s = traceback.format_exc()
            feedback.pushInfo(s)'''
            feedback.pushInfo(tr('Failure in kml extraction - May return partial results.'))
            handler.endDocument()

        if extension == '.kmz':
            kmz.close()
        else:
            kml.close()

        feedback.pushInfo('{} points extracted'.format(self.cntPt))
        feedback.pushInfo('{} lines extracted'.format(self.cntLine))
        feedback.pushInfo('{} polygons extracted'.format(self.cntPoly))

        r = {}
        if self.cntPt > 0:
            r[self.PrmPointOutputLayer] = self.dest_id_pt
        if self.cntLine > 0:
            r[self.PrmLineOutputLayer] = self.dest_id_line
        if self.cntPoly > 0:
            r[self.PrmPolygonOutputLayer] = self.dest_id_poly

        return (r)

    def addpoint(self, feature):
        if self.cntPt == 0:
            f = QgsFields()
            f.append(QgsField("name", QVariant.String))
            f.append(QgsField("folders", QVariant.String))
            f.append(QgsField("description", QVariant.String))
            f.append(QgsField("altitude", QVariant.Double))
            f.append(QgsField("alt_mode", QVariant.String))
            f.append(QgsField("time_begin", QVariant.String))
            f.append(QgsField("time_end", QVariant.String))
            f.append(QgsField("time_when", QVariant.String))
            for item in self.extData:
                f.append(QgsField(item, QVariant.String))
            (self.sinkPt, self.dest_id_pt) = self.parameterAsSink(self.parameters,
                self.PrmPointOutputLayer, self.context, f,
                QgsWkbTypes.PointZ, epsg4326)

        self.cntPt += 1
        self.sinkPt.addFeature(feature)

    def addline(self, feature):
        if self.cntLine == 0:
            f = QgsFields()
            f.append(QgsField("name", QVariant.String))
            f.append(QgsField("folders", QVariant.String))
            f.append(QgsField("description", QVariant.String))
            f.append(QgsField("altitude", QVariant.Double))
            f.append(QgsField("alt_mode", QVariant.String))
            f.append(QgsField("time_begin", QVariant.String))
            f.append(QgsField("time_end", QVariant.String))
            f.append(QgsField("time_when", QVariant.String))
            for item in self.extData:
                f.append(QgsField(item, QVariant.String))
            (self.sinkLine, self.dest_id_line) = self.parameterAsSink(self.parameters,
                self.PrmLineOutputLayer, self.context, f,
                QgsWkbTypes.MultiLineStringZ, epsg4326)

        self.cntLine += 1
        self.sinkLine.addFeature(feature)

    def addpolygon(self, feature):
        if self.cntPoly == 0:
            f = QgsFields()
            f.append(QgsField("name", QVariant.String))
            f.append(QgsField("folders", QVariant.String))
            f.append(QgsField("description", QVariant.String))
            f.append(QgsField("altitude", QVariant.Double))
            f.append(QgsField("alt_mode", QVariant.String))
            f.append(QgsField("time_begin", QVariant.String))
            f.append(QgsField("time_end", QVariant.String))
            f.append(QgsField("time_when", QVariant.String))
            for item in self.extData:
                f.append(QgsField(item, QVariant.String))
            (self.sinkPoly, self.dest_id_poly) = self.parameterAsSink(self.parameters,
                self.PrmPolygonOutputLayer, self.context, f,
                QgsWkbTypes.MultiPolygonZ, epsg4326)
        self.cntPoly += 1
        self.sinkPoly.addFeature(feature)

    def name(self):
        return 'importkml'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icon.png')

    def displayName(self):
        return tr('Import KML/KMZ')

    def group(self):
        return tr('Vector conversion')

    def groupId(self):
        return 'vectorconversion'

    def helpUrl(self):
        file = os.path.dirname(__file__)+'/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def createInstance(self):
        return ImportKmlAlgorithm()


class PlacemarkHandler(xml.sax.handler.ContentHandler, QObject):
    addpoint = pyqtSignal(QgsFeature)
    addline = pyqtSignal(QgsFeature)
    addpolygon = pyqtSignal(QgsFeature)
    def __init__(self, skipPt, skipLine, skipPoly, extDataMap, feedback):
        QObject.__init__(self)
        xml.sax.handler.ContentHandler.__init__(self)
        self.schema = {}
        self.skipPt = skipPt
        self.skipLine = skipLine
        self.skipPoly = skipPoly
        self.extDataMap = extDataMap
        self.feedback = feedback
        self.extDataSize = len(extDataMap)

        self.inPlacemark = False
        self.resetSettings()
        self.folders = []

    def resetSettings(self):
        '''Set all settings to a default new placemark.'''
        self.inFolder = False
        self.inName = False
        self.inDescription = False
        self.inCoordinates = False
        self.inLatitude = False
        self.inLongitude = False
        self.inAltitude = False
        self.inAltitudeMode = False
        self.inLocation = False
        self.inOuterBoundary = False
        self.inInnerBoundary = False
        self.inTimeSpan = False
        self.inBegin = False
        self.inEnd = False
        self.inTimeStamp = False
        self.inWhen = False
        self.inExtendedData = False
        self.inData = False
        self.inDataValue = False
        self.inPoint = False
        self.inLineString = False
        self.inPolygon = False
        self.lineStrings = [] # List of QgsLineString
        self.ptPts = []
        self.ptAltitude = []
        self.polygons = []
        self.innerPoly = []
        self.outerPoly = ""
        self.folder = ""
        self.name = ""
        self.description = ""
        self.coord = ""
        self.lon = ""
        self.lat = ""
        self.altitude = ""
        self.altitudeMode = ""
        self.begin = ""
        self.end = ""
        self.when = ""
        self.dataName = None
        self.dataValue = ""
        self.extendedData = {}

    def schemaBaseLookup(self, name):
        if name in self.schema:
            return( self.schema[name] )
        return(name)

    def addSchema(self, name, parent):
        parent = self.schemaBaseLookup(parent)
        self.schema[name] = parent

    def startElement(self, name, attr):
        if name.startswith('kml:'):
            name = name[4:]
        if name == "Schema":
            n = None
            p = None
            for (k,v) in list(attr.items()):
                if k == 'name':
                    n = v
                if k == 'parent':
                    p = v
                if n and p:
                    self.addSchema(n, p)

        name = self.schemaBaseLookup(name)

        if name == "Folder":
            self.inFolder = True
            self.name = ""

        elif self.inFolder and not self.inPlacemark and name == "name":
            self.inName = True
            self.name = ""

        elif name == "Placemark":
            self.inPlacemark = True
            self.resetSettings()

        elif self.inPlacemark:
            if name == "Point":
                self.inPoint = True
            elif name == "LineString":
                self.inLineString = True
            elif name == "Polygon":
                self.inPolygon = True
            elif name == "Location":
                self.inLocation = True
            elif name == "name":
                self.inName = True
                self.name = ""
            elif name == "description":
                self.inDescription = True
                self.description = ""
            elif name == "coordinates":
                self.inCoordinates = True
                self.coord = ""
            elif name == "outerBoundaryIs":
                self.inOuterBoundary = True
                self.coord = ""
            elif name == "innerBoundaryIs":
                self.inInnerBoundary = True
                self.coord = ""
            elif name == "TimeSpan":
                self.inTimeSpan = True
            elif name == "TimeStamp":
                self.inTimeStamp = True
            elif name == "begin":
                self.inBegin = True
            elif name == "end":
                self.inEnd = True
            elif name == "when":
                self.inWhen = True
            elif name == "longitude" and self.inLocation:
                self.inLongitude = True
                self.lon = ""
            elif name == "latitude" and self.inLocation:
                self.inLatitude = True
                self.lat = ""
            elif name == "altitude" and self.inLocation:
                self.inAltitude = True
                self.altitude = ""
            elif name == "altitudeMode":
                self.inAltitudeMode = True
                self.altitudeMode = ""
            elif name == "Data" and self.inExtendedData:
                self.inData = True
                self.dataName = None
                for (k,v) in list(attr.items()):
                    if k == 'name':
                        self.dataName = v
            elif name == 'value' and self.inData:
                self.inDataValue = True
            elif name == "ExtendedData":
                self.inExtendedData = True

    def characters(self, data):
        if self.inName: # on text within tag
            self.name += data # save text if in title
        elif self.inDescription:
            self.description += data
        elif self.inCoordinates:
            self.coord += data
        elif self.inLongitude and self.inLocation:
            self.lon += data
        elif self.inLatitude and self.inLocation:
            self.lat += data
        elif self.inAltitude and self.inLocation:
            self.altitude += data
        elif self.inBegin and self.inTimeSpan:
            self.begin += data
        elif self.inEnd and self.inTimeSpan:
            self.end += data
        elif self.inWhen and self.inTimeStamp:
            self.when += data
        elif self.inAltitudeMode:
            self.altitudeMode += data
        elif self.inDataValue:
            self.dataValue += data


    def endElement(self, name):
        if name.startswith('kml:'):
            name = name[4:]
        name = self.schemaBaseLookup(name)
        if self.inPlacemark:
            if name == "name":
                self.inName = False # on end title tag
                self.name = self.name.strip()
            elif name == "description":
                self.inDescription = False
                self.description = self.description.strip()
            elif name == "Point":
                self.processPoint(self.coord)
                self.inPoint = False
            elif name == "LineString":
                self.processLineString(self.coord)
                self.inLineString = False
            elif name == "coordinates":
                self.inCoordinates = False
                if self.inPolygon:
                    if self.inOuterBoundary:
                        self.outerPoly = self.coord.strip()
                    elif self.inInnerBoundary:
                        self.innerPoly.append(self.coord.strip())
                else:
                    self.coord = self.coord.strip()
            elif name == "longitude" and self.inLocation:
                self.inLongitude = False
                self.lon = self.lon.strip()
            elif name == "latitude" and self.inLocation:
                self.inLatitude = False
                self.lat = self.lat.strip()
            elif name == "altitude" and self.inLocation:
                self.inAltitude = False
                self.altitude = self.altitude.strip()
            elif name == "Location":
                self.processLocation(self.lon, self.lat, self.altitude)
                self.inLocation = False
                self.inLongitude = False
                self.inLatitude = False
                self.inAltitude = False
            elif name == "Polygon":
                self.processPolygon()
                self.inPolygon = False
                self.inOuterBoundary = False
                self.inInnerBoundary = False
                self.outerPoly = ""
                self.innerPoly = []
            elif name == "outerBoundaryIs":
                self.inOuterBoundary = False
            elif name == "innerBoundaryIs":
                self.inInnerBoundary = False
            elif name == "TimeSpan":
                self.inTimeSpan = False
            elif name == "TimeStamp":
                self.inTimeStamp = False
            elif name == "begin":
                self.inBegin = False
            elif name == "end":
                self.inEnd = False
            elif name == "when":
                self.inWhen = False
            elif name == "altitudeMode":
                self.inAltitudeMode = False
            elif name == "Placemark":
                self.process(self.name, self.description, self.altitudeMode, self.begin, self.end, self.when)
                self.inPlacemark = False
                self.resetSettings()
            elif name == 'Data' and self.inExtendedData:
                self.inData = False
            elif name == 'value' and self.inData:
                if self.dataName:
                    self.extendedData[self.dataName] = self.dataValue.strip()
                self.inDataValue = False
                self.dataValue = ''
            elif name == 'ExtendedData':
                self.inExtendedData = False
                self.inData = False
        elif name == 'Folder':
            self.inFolder = False
            if len(self.folders) > 0:
                del self.folders[-1]
        elif self.inFolder:
            if name == 'name':
                self.inName = False # on end title tag
                self.inFolder = False
                self.name = self.name.strip()
                self.folders.append(self.name)

    def folderString(self):
        if len(self.folders) > 0:
            return(u"; ".join(self.folders))
        else:
            return("")

    def processLineString(self, coord):
        if self.skipLine:
            return
        lineStr = coord2ptsZ(coord)
        self.lineStrings.append(lineStr)

    def processPoint(self, coord):
        if self.skipPt:
            return

        c = coord.split(',')
        lat = 0.0
        lon = 0.0
        altitude = 0.0
        try:
            lon = float( c[0] )
            lat = float( c[1] )
            if len(c) >= 3:
                altitude = float(c[2])
        except:
            return
        pt = QgsPoint(lon,lat,altitude)
        self.ptPts.append(pt)
        self.ptAltitude.append(altitude)

    def processLocation(self, lon, lat, altitude):
        if self.skipPt:
            return

        try:
            lon = float(lon)
            lat = float(lat)
        except:
            return
        altitude = 0.0
        try:
            if altitude:
                altitude = float(altitude)
        except:
            pass
        pt = QgsPoint(lon,lat,altitude)
        self.ptPts.append(pt)
        self.ptAltitude.append(altitude)

    def processPolygon(self):
        if self.skipPoly:
            return
        interior_ring = []
        poly = QgsPolygon()
        outerLineStr = coord2ptsZ(self.outerPoly)
        poly.setExteriorRing(outerLineStr)
        if len(self.innerPoly) > 0:
            for p in self.innerPoly:
                innerLineStr = coord2ptsZ(p)
                interior_ring.append(innerLineStr)
            poly.setInteriorRings(interior_ring)
        self.polygons.append(poly)

    def process(self, name, desc, alt_mode, begin, end, when):
        if self.extDataSize > 0:
            extAttr = [''] * self.extDataSize
        for key in self.extendedData.keys():
            if key in self.extDataMap:
                extAttr[self.extDataMap[key]] = self.extendedData[key]
        # POINTS
        if len(self.ptPts) != 0:
            for x, pt in enumerate(self.ptPts):
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry(pt))
                attr = [name, self.folderString(), desc, self.ptAltitude[x], alt_mode, begin, end, when]
                if self.extDataSize > 0:
                    attr.extend(extAttr)
                feature.setAttributes(attr)
                self.addpoint.emit(feature)
        
        # LINES - lineStrings is a list of QgsLineString
        if len(self.lineStrings) != 0:
            feature = QgsFeature()
            if len(self.lineStrings) == 1:
                feature.setGeometry(QgsGeometry(self.lineStrings[0]))
            else:
                g = QgsMultiLineString()
                for lineStr in self.lineStrings:
                    g.addGeometry(lineStr)
                feature.setGeometry(QgsGeometry(g))
            attr = [name, self.folderString(), desc, 0, alt_mode, begin, end, when]
            if self.extDataSize > 0:
                attr.extend(extAttr)
            feature.setAttributes(attr)
            self.addline.emit(feature)

        # POLYGONS
        if len(self.polygons) != 0:
            feature = QgsFeature()
            if len(self.polygons) == 1:
                feature.setGeometry(QgsGeometry(self.polygons[0]))
            else:
                g = QgsMultiPolygon()
                for poly in self.polygons:
                    g.addGeometry(poly)
                feature.setGeometry(QgsGeometry(g))
            attr = [name, self.folderString(), desc, 0, alt_mode, begin, end, when]
            if self.extDataSize > 0:
                attr.extend(extAttr)
            feature.setAttributes(attr)
            self.addpolygon.emit(feature)

def coord2ptsZ(coords):
    lineStr = QgsLineString()
    coords = coords.strip()
    clist = re.split('\s+', coords)

    for pt in clist:
        c = pt.split(',')
        if len(c) >= 6:
            '''This is invalid KML syntax, but given some KMLs have been formatted
            this way the invalid exception is looked for. There should be a space
            between line string coordinates. This looks for a comma between them and
            also assumes it is formatted as lat,lon,altitude,lat,lon,altitude...'''
            i = 0
            while i < len(c) - 1:
                try:
                    lon = float(c[i])
                    lat = float(c[i+1])
                except:
                    lon = 0.0
                    lat = 0.0
                try:
                    altitude = float(c[i+2])
                except:
                    altitude = 0
                lineStr.addVertex(QgsPoint(lon,lat,altitude))
                i += 3
        else:
            altitude = 0
            try:
                lon = float(c[0])
                lat = float(c[1])
                if len(c) >= 3:
                    altitude = float(c[2])
            except:
                lon = 0.0
                lat = 0.0
                
            lineStr.addVertex(QgsPoint(lon,lat,altitude))

    return(lineStr)

class PreProcessHandler(xml.sax.handler.ContentHandler, QObject):
    def __init__(self):
        QObject.__init__(self)
        xml.sax.handler.ContentHandler.__init__(self)

        self.extendedData = set()
        self.inExtendedData = False

    def startElement(self, name, attr):

        if name == "Data" and self.inExtendedData:
            self.dataName = None
            for (k,v) in list(attr.items()):
                if k == 'name':
                    if v:
                        self.extendedData.add(v)
        elif name == "ExtendedData":
            self.inExtendedData = True

    def endElement(self, name):
        if name == 'ExtendedData':
            self.inExtendedData = False

    def getExtendedDataFields(self):
        return( list(self.extendedData) )
