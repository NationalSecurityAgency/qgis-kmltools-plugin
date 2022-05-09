import os
import math
from qgis.PyQt.QtCore import Qt, QUrl, QTime, QDateTime, QDate, QSize, QPointF
from qgis.PyQt.QtGui import QIcon

from qgis.core import (
    QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsCompoundCurve,
    QgsProject, QgsRenderContext, QgsWkbTypes, Qgis, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils)

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterField,
    QgsProcessingParameterVectorLayer)

import dateutil.parser
import datetime
from xml.sax.saxutils import escape
import simplekml
# import traceback
import tempfile
from .settings import settings

def qcolor2kmlcolor(color, opacity=1):
    return('{:02x}{:02x}{:02x}{:02x}'.format(int(color.alpha()*opacity), color.blue(), color.green(), color.red()))


ALTITUDE_MODES = ['clampToGround', 'relativeToGround', 'absolute']

GOOGLE_ICONS = {
    'Square placemark':'http://maps.google.com/mapfiles/kml/shapes/placemark_square.png',
    'Circle placemark':'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png',
    'Shaded dot':'http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png',
    'Donut':'http://maps.google.com/mapfiles/kml/shapes/donut.png',
    'Polygon':'http://maps.google.com/mapfiles/kml/shapes/polygon.png',
    'Open diamond':'http://maps.google.com/mapfiles/kml/shapes/open-diamond.png',
    'Square':'http://maps.google.com/mapfiles/kml/shapes/square.png',
    'Star':'http://maps.google.com/mapfiles/kml/shapes/star.png',
    'Target':'http://maps.google.com/mapfiles/kml/shapes/target.png',
    'Triangle':'http://maps.google.com/mapfiles/kml/shapes/triangle.png'
    }

class ExportKmzAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to import KML and KMZ files.
    """
    PrmInputLayer = 'InputLayer'
    PrmSelectedFeaturesOnly = 'SelectedFeaturesOnly'
    PrmOutputKmz = 'OutputKmz'
    PrmNameField = 'NameField'
    PrmDescriptionField = 'DescriptionField'
    PrmExportStyle = 'ExportStyle'
    PrmUseGoogleIcon = 'UseGoogleIcon'
    PrmLineWidthFactor = 'LineWidthFactor'
    PrmAltitudeInterpretation = 'AltitudeInterpretation'
    PrmAltitudeMode = 'AltitudeMode'
    PrmAltitudeModeField = 'AltitudeModeField'
    PrmAltitudeField = 'AltitudeField'
    PrmAltitudeAddend = 'AltitudeAddend'
    PrmDateTimeStampField = 'DateTimeStampField'
    PrmDateStampField = 'DateStampField'
    PrmTimeStampField = 'TimeStampField'
    PrmDateTimeBeginField = 'DateTimeBeginField'
    PrmDateBeginField = 'DateBeginField'
    PrmTimeBeginField = 'TimeBeginField'
    PrmDateTimeEndField = 'DateTimeEndField'
    PrmDateEndField = 'DateEndField'
    PrmTimeEndField = 'TimeEndField'
    PrmPhotoField = 'PhotoField'
    PrmPhotoDir = 'PhotoDir'
    epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
    temp_dir = tempfile.gettempdir()

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.PrmInputLayer,
                'Input layer',
                [QgsProcessing.TypeVector])
        )
        self.addParameter(
            QgsProcessingParameterBoolean (
                self.PrmSelectedFeaturesOnly,
                'Selected features only',
                False,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmNameField,
                'Name/Label field',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                defaultValue='name',
                optional=True
            )
        )
        if Qgis.QGIS_VERSION_INT >= 31200:
            self.addParameter(
                QgsProcessingParameterField(
                    self.PrmDescriptionField,
                    'Description fields',
                    parentLayerParameterName=self.PrmInputLayer,
                    type=QgsProcessingParameterField.Any,
                    optional=True,
                    allowMultiple=True,
                    defaultToAllFields=True
                )
            )
        else:
            self.addParameter(
                QgsProcessingParameterField(
                    self.PrmDescriptionField,
                    'Description fields',
                    parentLayerParameterName=self.PrmInputLayer,
                    type=QgsProcessingParameterField.Any,
                    optional=True,
                    allowMultiple=True
                )
            )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmExportStyle,
                'Export style for single, categorized, and graduated symbols',
                True,
                optional=True)
        )
        self.google_icons = list(GOOGLE_ICONS.keys())
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUseGoogleIcon,
                #'Use QGIS point color &amp; size, but use one of these Google icons.',
                'Point Layers: Use the following Google icon but use QGIS icon color and size',
                options=self.google_icons,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmAltitudeInterpretation,
                'Specify whether to include altitude in the KMZ (must be in meters)',
                options=['Don\'t use altitude', 'Use QGIS geometry Z value if present', 'Use altitude from one of the feature\'s attributes'],
                defaultValue=1,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmAltitudeMode,
                'Default altitude mode when not obtained from the attribute table',
                options=ALTITUDE_MODES,
                defaultValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmAltitudeModeField,
                'Altitude mode field',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.String,
                defaultValue='alt_mode',
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmAltitudeField,
                'Altitude field (value must be in meters)',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                defaultValue='altitude',
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmAltitudeAddend,
                'Altitude addend (value must be in meters)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmDateTimeStampField,
                'Date/Time stamp field (see advanced parameters)',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                defaultValue='time_when',
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmDateTimeBeginField,
                'Date/Time span begin field (see advanced parameters)',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                defaultValue='time_begin',
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmDateTimeEndField,
                'Date/Time span end field (see advanced parameters)',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                defaultValue='time_end',
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmPhotoField,
                'Image path/name field',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.String,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.PrmOutputKmz,
                'Output KMZ file',
                fileFilter='*.kmz')
        )
        # Set up Advanced Parameters
        param = QgsProcessingParameterNumber(
            self.PrmLineWidthFactor,
            'Line width multiplication factor (widths appear smaller in Google Earth)',
            QgsProcessingParameterNumber.Double,
            defaultValue=2,
            minValue=0,
            optional=True)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterField(
            self.PrmDateStampField,
            'Date stamp field',
            parentLayerParameterName=self.PrmInputLayer,
            type=QgsProcessingParameterField.Any,
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterField(
            self.PrmTimeStampField,
            'Time stamp field',
            parentLayerParameterName=self.PrmInputLayer,
            type=QgsProcessingParameterField.Any,
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterField(
            self.PrmDateBeginField,
            'Date span begin field',
            parentLayerParameterName=self.PrmInputLayer,
            type=QgsProcessingParameterField.Any,
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterField(
            self.PrmTimeBeginField,
            'Time span begin field',
            parentLayerParameterName=self.PrmInputLayer,
            type=QgsProcessingParameterField.Any,
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterField(
            self.PrmDateEndField,
            'Date span end field',
            parentLayerParameterName=self.PrmInputLayer,
            type=QgsProcessingParameterField.Any,
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterField(
            self.PrmTimeEndField,
            'Time span end field',
            parentLayerParameterName=self.PrmInputLayer,
            type=QgsProcessingParameterField.Any,
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, feedback):
        self.parameters = parameters
        self.context = context
        self.feedback = feedback
        filename = self.parameterAsFileOutput(parameters, self.PrmOutputKmz, context)
        layer = self.parameterAsLayer(parameters, self.PrmInputLayer, context)
        selected_features_only = self.parameterAsInt(parameters, self.PrmSelectedFeaturesOnly, context)

        # Before we go further check to make sure we have a valid vector layer
        if not layer:
            raise QgsProcessingException('No valid vector layer selected.')
        wkbtype = layer.wkbType()
        geomtype = QgsWkbTypes.geometryType(wkbtype)
        if geomtype == QgsWkbTypes.UnknownGeometry or geomtype == QgsWkbTypes.NullGeometry:
            raise QgsProcessingException('Algorithm input is not a valid point, line, or polygon layer.')
        if self.PrmNameField not in parameters or parameters[self.PrmNameField] is None:
            name_field = None
        else:
            name_field = self.parameterAsString(parameters, self.PrmNameField, context)
        desc_fields = self.parameterAsFields(parameters, self.PrmDescriptionField, context)
        desc_cnt = len(desc_fields)
        export_style = self.parameterAsInt(parameters, self.PrmExportStyle, context)
        if self.PrmUseGoogleIcon not in parameters or parameters[self.PrmUseGoogleIcon] is None:
            google_icon = None
        else:
            google_icon = self.parameterAsEnum(parameters, self.PrmUseGoogleIcon, context)
        self.line_width_factor = self.parameterAsDouble(parameters, self.PrmLineWidthFactor, context)
        alt_interpret = self.parameterAsEnum(parameters, self.PrmAltitudeInterpretation, context)
        if self.PrmAltitudeMode not in parameters or parameters[self.PrmAltitudeMode] is None:
            default_alt_mode = None
        else:
            default_alt_mode = ALTITUDE_MODES[self.parameterAsEnum(parameters, self.PrmAltitudeMode, context)]
        alt_mode_field = self.parameterAsString(parameters, self.PrmAltitudeModeField, context)
        altitude_field = self.parameterAsString(parameters, self.PrmAltitudeField, context)
        altitude_addend = self.parameterAsDouble(parameters, self.PrmAltitudeAddend, context)
        date_time_stamp_field = self.parameterAsString(parameters, self.PrmDateTimeStampField, context)
        date_stamp_field = self.parameterAsString(parameters, self.PrmDateStampField, context)
        time_stamp_field = self.parameterAsString(parameters, self.PrmTimeStampField, context)
        date_time_begin_field = self.parameterAsString(parameters, self.PrmDateTimeBeginField, context)
        date_begin_field = self.parameterAsString(parameters, self.PrmDateBeginField, context)
        time_begin_field = self.parameterAsString(parameters, self.PrmTimeBeginField, context)
        date_time_end_field = self.parameterAsString(parameters, self.PrmDateTimeEndField, context)
        date_end_field = self.parameterAsString(parameters, self.PrmDateEndField, context)
        time_end_field = self.parameterAsString(parameters, self.PrmTimeEndField, context)
        if self.PrmPhotoField not in parameters or parameters[self.PrmPhotoField] is None:
            photo_path_field = None
        else:
            photo_path_field = self.parameterAsString(parameters, self.PrmPhotoField, context)
        self.photos = {}

        hasz = QgsWkbTypes.hasZ(wkbtype)
        if alt_interpret == 0:
            hasz = False
            default_alt_mode = None
            alt_mode_field = None
            altitude_field = None
        elif alt_interpret == 2:
            hasz = False
        src_crs = layer.crs()
        if src_crs != self.epsg4326:
            geomTo4326 = QgsCoordinateTransform(src_crs, self.epsg4326, QgsProject.instance())

        self.symcontext = QgsRenderContext.fromMapSettings(settings.canvas.mapSettings())
        self.png_icons = []
        self.cat_styles = {}
        kml = simplekml.Kml()
        kml.resetidcounter()
        try:
            self.render = layer.renderer()
            self.exp_context = QgsExpressionContext()
            self.exp_context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        except Exception:
            if export_style:
                export_style = 0
                feedback.reportError('Layer style cannot be determined. Processing will continue without symbol style export.')
        if export_style:
            render_type = self.render.type()
            if render_type == 'singleSymbol':
                export_style = 1
            elif render_type == 'categorizedSymbol':
                style_field = self.render.classAttribute()
                self.field_exp = QgsExpression(style_field)
                export_style = 2
            elif render_type == 'graduatedSymbol':
                style_field = self.render.classAttribute()
                self.field_exp = QgsExpression(style_field)
                export_style = 3
            else:
                feedback.reportError('Only single, categorized, and graduated symbol styles can be exported. Processing will continue without symbol style export.')
                export_style = 0
            if export_style:
                self.initStyles(export_style, google_icon, name_field, geomtype, kml)

        folder = kml.newfolder(name=layer.sourceName())
        altitude = 0
        if selected_features_only:
            iterator = layer.getSelectedFeatures()
            featureCount = layer.selectedFeatureCount()
        else:
            featureCount = layer.featureCount()
            iterator = layer.getFeatures()
        total = 100.0 / featureCount if featureCount else 0
        num_features = 0
        
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            num_features += 1
            # feedback.pushInfo('Feature {} - {}'.format(num_features, type(feature)))
            geom = feature.geometry()
            # Check to see if there is a Null geometery and skip this feature.
            if geom.isNull():
                continue
            if src_crs != self.epsg4326:
                geom.transform(geomTo4326)

            if altitude_field:
                try:
                    altitude = float(feature[altitude_field])
                except Exception:
                    altitude = 0

            if geom.isMultipart() or (name_field and geomtype == QgsWkbTypes.PolygonGeometry):
                kmlgeom = folder.newmultigeometry()
                kml_item = kmlgeom
            else:
                kmlgeom = folder
                kml_item = None
            if geomtype == QgsWkbTypes.PointGeometry:  # POINTS
                for pt in geom.parts():
                    kmlpart = kmlgeom.newpoint()
                    self.setAltitudeMode(kmlpart, feature, default_alt_mode, alt_mode_field)
                    if kml_item is None:
                        kml_item = kmlpart
                    if hasz:
                        kmlpart.coords = [(pt.x(), pt.y(), pt.z() + altitude_addend)]
                    else:
                        kmlpart.coords = [(pt.x(), pt.y(), altitude + altitude_addend)]
            elif geomtype == QgsWkbTypes.LineGeometry:  # LINES
                for part in geom.parts():
                    kmlpart = kmlgeom.newlinestring()
                    self.setAltitudeMode(kmlpart, feature, default_alt_mode, alt_mode_field)
                    if kml_item is None:
                        kml_item = kmlpart
                    if hasz:
                        kmlpart.coords = [(pt.x(), pt.y(), pt.z() + altitude_addend) for pt in part]
                    else:
                        kmlpart.coords = [(pt.x(), pt.y(), altitude + altitude_addend) for pt in part]
            elif geomtype == QgsWkbTypes.PolygonGeometry:  # POLYGONS
                if name_field:
                    try:
                        centroid = geom.centroid().asPoint()
                        name = '{}'.format(feature[name_field])
                        labelpart = kmlgeom.newpoint(coords=[(centroid.x(), centroid.y())], name=name)
                    except Exception:
                        pass

                for part in geom.parts():
                    kmlpart = kmlgeom.newpolygon()
                    self.setAltitudeMode(kmlpart, feature, default_alt_mode, alt_mode_field)
                    if kml_item is None:
                        kml_item = kmlpart
                    num_interior_rings = part.numInteriorRings()
                    ext_ring = part.exteriorRing()
                    if isinstance(ext_ring, QgsCompoundCurve):
                        ext_ring = ext_ring.curveToLine()
                    # feedback.pushInfo('ext_ring type {}'.format(type(ext_ring)))
                    
                    if hasz:
                        kmlpart.outerboundaryis = [(pt.x(), pt.y(), pt.z() + altitude_addend) for pt in ext_ring]
                    else:
                        kmlpart.outerboundaryis = [(pt.x(), pt.y(), altitude + altitude_addend) for pt in ext_ring]
                    if num_interior_rings:
                        ib = []
                        for i in range(num_interior_rings):
                            ring = part.interiorRing(i)
                            if isinstance(ring, QgsCompoundCurve):
                                ring = ring.curveToLine()
                            if hasz:
                                ib.append([(pt.x(), pt.y(), pt.z() + altitude_addend) for pt in ring])
                            else:
                                ib.append([(pt.x(), pt.y(), altitude + altitude_addend) for pt in ring])
                        kmlpart.innerboundaryis = ib

            self.exportStyle(kml_item, feature, export_style, geomtype)
            if name_field:
                self.exportName(kml_item, feature[name_field])

            if photo_path_field:
                photo_path = feature[photo_path_field].strip()
                if os.path.exists(photo_path):
                    if not (photo_path in self.photos):
                        local_path = kml.addfile(photo_path)
                        self.photos[photo_path] = local_path
                else:
                    photo_path = None
            else:
                photo_path = None
                    
            if desc_cnt == 1:
                self.exportDescription(kml_item, feature[desc_fields[0]], photo_path)
            elif desc_cnt > 1:
                self.exportFields(kml_item, desc_fields, feature, photo_path)

            # Process the first date / time fields
            date_time_str = self.parseDateTimeValues(
                feature,
                date_time_stamp_field,
                date_stamp_field,
                time_stamp_field)
            if date_time_str:
                kml_item.timestamp.when = date_time_str
            date_time_str = self.parseDateTimeValues(
                feature,
                date_time_begin_field,
                date_begin_field,
                time_begin_field)
            if date_time_str:
                kml_item.timespan.begin = date_time_str
            date_time_str = self.parseDateTimeValues(
                feature,
                date_time_end_field,
                date_end_field,
                time_end_field)
            if date_time_str:
                kml_item.timespan.end = date_time_str

            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))
        if num_features == 0:
            feedback.pushInfo('No features processed')
        else:
            kml.savekmz(filename)

        self.cleanup()

        return({})

    def exportStyle(self, kml_item, feature, export_style, geomtype):
        # self.feedback.pushInfo('exportStyle')
        if export_style == 1:
            kml_item.style = self.simple_style
        elif export_style == 2:
            # Determine the category expression value
            self.exp_context.setFeature(feature)
            try:
                value = self.field_exp.evaluate(self.exp_context)
                # Which category does feature value fall in
                catindex = self.render.categoryIndexForValue(value)
            except Exception:
                return
            # If it is outside the category ranges assign it to the 0 index
            if catindex not in self.cat_styles:
                catindex = 0
            if catindex in self.cat_styles:
                kml_item.style = self.cat_styles[catindex]
        elif export_style == 3:
            # Determine the gradient expression value
            self.exp_context.setFeature(feature)
            try:
                value = self.field_exp.evaluate(self.exp_context)
                # Which range of the gradient does this value fall in
                range = self.render.rangeForValue(value)
                if range is None:
                    minimum = 1e16
                    maximum = -1e16
                    for ran in self.render.ranges():
                        if ran.lowerValue() < minimum:
                            minimum = ran.lowerValue()
                        if ran.upperValue() > maximum:
                            maximum = ran.upperValue()
                    if value > maximum:
                        value = maximum
                    if value < minimum:
                        value = minimum
                    range = self.render.rangeForValue(value)
                    if range is None:
                        self.feedback.pushInfo('An error occured in defining the range object')
                        return
            except Exception:
                '''s = traceback.format_exc()
                self.feedback.pushInfo(s)'''
                return
            # Get the symbol related to the specified gradient range
            # For lines and polygons we would use the color and line sizes
            symbol = range.symbol()
            opacity = symbol.opacity()
            if geomtype == QgsWkbTypes.PointGeometry:
                sym_size = symbol.size(self.symcontext)
                color = qcolor2kmlcolor(symbol.color())
            elif geomtype == QgsWkbTypes.LineGeometry:
                sym_size = symbol.width()
                if sym_size == 0:
                    sym_size = 0.5
                color = qcolor2kmlcolor(symbol.color())
                key = (sym_size, color)
            else:
                symbol_layer = symbol.symbolLayer(0)
                stroke_style = symbol_layer.strokeStyle()
                if stroke_style == 0:
                    sym_size = 0
                else:
                    sym_size = symbol_layer.strokeWidth()
                color = qcolor2kmlcolor(symbol_layer.color(), opacity)
            key = (sym_size, color)
            if key in self.cat_styles:
                # self.feedback.pushInfo('  catindex in cat_styles')
                kml_item.style = self.cat_styles[key]
                # self.feedback.pushInfo('  style {}'.format(kml_item.style))

    def initStyles(self, symtype, google_icon, name_field, geomtype, kml):
        # self.feedback.pushInfo('initStyles type: {}'.format(symtype))
        if symtype == 1: # Single Symbol
            symbol = self.render.symbol()
            opacity = symbol.opacity()
            self.simple_style = simplekml.Style()
            if geomtype == QgsWkbTypes.PointGeometry:
                sym_size = symbol.size(self.symcontext)
                if google_icon is None:
                    bounds = symbol.bounds(QPointF(0, 0), self.symcontext)
                    size = bounds.width()
                    if bounds.height() > size:
                        size = bounds.height()
                    size = math.ceil(size * 1.1)
                    path = os.path.join(self.temp_dir, 'icon.png')
                    self.png_icons.append(path)
                    symbol.exportImage(path, "png", QSize(size, size))
                    kml.addfile(path)
                    self.simple_style.iconstyle.scale = sym_size / 15
                    self.simple_style.iconstyle.icon.href = 'files/icon.png'
                else:
                    self.simple_style.iconstyle.scale = sym_size / 10
                    self.simple_style.iconstyle.icon.href = GOOGLE_ICONS[self.google_icons[google_icon]]
                    self.simple_style.iconstyle.color = qcolor2kmlcolor(symbol.color())
            elif geomtype == QgsWkbTypes.LineGeometry:
                symbol_width = symbol.width()
                if symbol_width == 0:
                    symbol_width = 0.5
                self.simple_style.linestyle.color = qcolor2kmlcolor(symbol.color(), opacity)
                self.simple_style.linestyle.width = symbol_width * self.line_width_factor
                if name_field:
                    self.simple_style.linestyle.gxlabelvisibility = True
            else:
                symbol_layer = symbol.symbolLayer(0)
                stroke_style = symbol_layer.strokeStyle()
                if stroke_style == 0:
                    stroke_width = 0
                else:
                    stroke_width = symbol_layer.strokeWidth()
                self.simple_style.linestyle.color = qcolor2kmlcolor(symbol_layer.strokeColor(), opacity)
                self.simple_style.linestyle.width = stroke_width * self.line_width_factor
                self.simple_style.polystyle.color = qcolor2kmlcolor(symbol_layer.color(), opacity)
                if name_field:
                    self.simple_style.iconstyle.scale = 0
        elif symtype == 2: # Categorized Symbols
            for idx, category in enumerate(self.render.categories()):
                cat_style = simplekml.Style()
                symbol = category.symbol()
                opacity = symbol.opacity()
                # self.feedback.pushInfo(' categories idx: {}'.format(idx))
                if geomtype == QgsWkbTypes.PointGeometry:
                    # self.feedback.pushInfo('  PointGeometry')
                    sym_size = symbol.size(self.symcontext)
                    # self.feedback.pushInfo('sym_size: {}'.format(sym_size))
                    if google_icon is None:
                        bounds = symbol.bounds(QPointF(0, 0), self.symcontext)
                        size = bounds.width()
                        if bounds.height() > size:
                            size = bounds.height()
                        size = math.ceil(size * 1.1)
                        name = 'icon{}.png'.format(idx)
                        path = os.path.join(self.temp_dir, name)
                        self.png_icons.append(path)
                        symbol.exportImage(path, "png", QSize(size, size))
                        kml.addfile(path)
                        cat_style.iconstyle.scale = sym_size / 15
                        cat_style.iconstyle.icon.href = 'files/' + name
                    else:
                        cat_style.iconstyle.scale = sym_size / 10
                        cat_style.iconstyle.icon.href = GOOGLE_ICONS[self.google_icons[google_icon]]
                        cat_style.iconstyle.color = qcolor2kmlcolor(symbol.color())
                elif geomtype == QgsWkbTypes.LineGeometry:
                    # self.feedback.pushInfo('  LineGeometry')
                    symbol_width = symbol.width()
                    if symbol_width == 0:
                        symbol_width = 0.5
                    cat_style.linestyle.color = qcolor2kmlcolor(symbol.color(), opacity)
                    cat_style.linestyle.width = symbol_width * self.line_width_factor
                    if name_field:
                        cat_style.linestyle.gxlabelvisibility = True
                else:
                    # self.feedback.pushInfo('  PolygonGeometry')
                    symbol_layer = symbol.symbolLayer(0)
                    stroke_style = symbol_layer.strokeStyle()
                    if stroke_style == 0:
                        stroke_width = 0
                    else:
                        stroke_width = symbol_layer.strokeWidth()
                    cat_style.linestyle.color = qcolor2kmlcolor(symbol_layer.strokeColor(), opacity)
                    cat_style.linestyle.width = stroke_width * self.line_width_factor
                    cat_style.polystyle.color = qcolor2kmlcolor(symbol_layer.color(), opacity)
                    if name_field:
                        cat_style.iconstyle.scale = 0
                self.cat_styles[idx] = cat_style
        else: # Graduated Symbols
            for idx, range in enumerate(self.render.ranges()):
                cat_style = simplekml.Style()
                symbol = range.symbol()
                opacity = symbol.opacity()
                # self.feedback.pushInfo(' categories idx: {}'.format(idx))
                if geomtype == QgsWkbTypes.PointGeometry:
                    # self.feedback.pushInfo('  PointGeometry')
                    sym_size = symbol.size(self.symcontext)
                    color = qcolor2kmlcolor(symbol.color(), opacity)
                    # self.feedback.pushInfo('sym_size: {}'.format(sym_size))
                    if google_icon is None:
                        bounds = symbol.bounds(QPointF(0, 0), self.symcontext)
                        size = bounds.width()
                        if bounds.height() > size:
                            size = bounds.height()
                        size = math.ceil(size * 1.1)
                        name = 'icon{}.png'.format(idx)
                        path = os.path.join(self.temp_dir, name)
                        self.png_icons.append(path)
                        symbol.exportImage(path, "png", QSize(size, size))
                        kml.addfile(path)
                        cat_style.iconstyle.scale = sym_size / 15
                        cat_style.iconstyle.icon.href = 'files/' + name
                    else:
                        cat_style.iconstyle.scale = sym_size / 10
                        cat_style.iconstyle.icon.href = GOOGLE_ICONS[self.google_icons[google_icon]]
                        cat_style.iconstyle.color = color
                elif geomtype == QgsWkbTypes.LineGeometry:
                    # self.feedback.pushInfo('  LineGeometry')
                    color = qcolor2kmlcolor(symbol.color(), opacity)
                    cat_style.linestyle.color = color
                    symbol_width = symbol.width()
                    if symbol_width == 0:
                        symbol_width = 0.5
                    cat_style.linestyle.width = symbol_width * self.line_width_factor
                    if name_field:
                        cat_style.linestyle.gxlabelvisibility = True
                else:
                    # self.feedback.pushInfo('  PolygonGeometry')
                    symbol_layer = symbol.symbolLayer(0)
                    stroke_style = symbol_layer.strokeStyle()
                    if stroke_style == 0:
                        stroke_width = 0
                    else:
                        stroke_width = symbol_layer.strokeWidth()
                    color = qcolor2kmlcolor(symbol_layer.color(), opacity)
                    cat_style.linestyle.color = qcolor2kmlcolor(symbol_layer.strokeColor(), opacity)
                    cat_style.linestyle.width = stroke_width * self.line_width_factor
                    cat_style.polystyle.color = color
                    if name_field:
                        cat_style.iconstyle.scale = 0
                self.cat_styles[(stroke_width,color)] = cat_style

    def cleanup(self):
        for icon in self.png_icons:
            if os.path.exists(icon):
                os.remove(icon)
    def get_attribute_str(self, attr):
        if not attr:
            return( '' )
        if isinstance(attr, QDateTime):
            attr = attr.toString(Qt.ISODate)
        elif isinstance(attr, QDate):
            attr = attr.toString(Qt.ISODate)
        elif isinstance(attr, QTime):
            attr = attr.toString(Qt.ISODate)
        attr = escape('{}'.format(attr).strip())
        return(attr)
            
    def exportName(self, kml_item, fname):
        kml_item.name = self.get_attribute_str(fname)

    def exportDescription(self, kml_item, desc, photo_path):
        desc = self.get_attribute_str(desc)
        if photo_path:
            desc = '<img src="{}" style="max-width:300"/><br/><br/>{}'.format(self.photos[photo_path], desc)
        else:
            desc = '{}'.format(desc)
        if desc:
            kml_item.description = desc

    def exportFields(self, kml_item, fields, f, photo_path):
        strs = ['<![CDATA[']
        if photo_path:
            strs.append('<img src="{}" style="max-width:300"/><br/><br/>'.format(self.photos[photo_path]))
        strs.append('<table>')
        for row, field in enumerate(fields):
            v = self.get_attribute_str(f[field])
            kml_item.extendeddata.newdata(name=field, value=v, displayname=field)
            if row & 1:
                strs.append('<tr><td>{}</td><td>$[{}]</td></tr>'.format(field, field))
            else:
                strs.append('<tr style="background-color:#DDDDFF"><td>{}</td><td>$[{}]</td></tr>'.format(field, field))
        strs.append('</table>\n]]>')
        str = '\n'.join(strs)
        kml_item.description = str

    def setAltitudeMode(self, kml_item, f, alt_mode, mode_field):
        try:
            mode = None
            if mode_field:
                mode = f[mode_field]
            if mode not in ALTITUDE_MODES and alt_mode:
                kml_item.altitudemode = alt_mode
                return
            if mode in ALTITUDE_MODES:
                kml_item.altitudemode = mode
        except Exception:
            return

    def parseDateTimeValues(self, feature, dt_field, date_field, time_field):
        if dt_field is None and date_field is None:
            return(None)
        try:
            dt = None
            date = None
            time = None
            if dt_field:
                dt = feature[dt_field]
            else:
                if date_field:
                    date = feature[date_field]
                if time_field:
                    time = feature[time_field]
            if dt:
                if isinstance(dt, QDateTime):
                    year = dt.date().year()
                    month = dt.date().month()
                    day = dt.date().day()
                    hour = dt.time().hour()
                    minute = dt.time().minute()
                    second = dt.time().second()
                    msec = dt.time().msec()
                    if msec == 0:
                        str = '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}'.format(year, month, day, hour, minute, second)
                    else:
                        str = '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:03d}'.format(year, month, day, hour, minute, second, msec)
                    return(str)
                elif isinstance(dt, QDate):
                    year = dt.year()
                    month = dt.month()
                    day = dt.day()
                    str = '{:04d}-{:02d}-{:02d}'.format(year, month, day)
                    return(str)
                elif isinstance(dt, float) or isinstance(dt, int):
                    str = self.prepareEpochTimeString(dt)
                    return(str)
                else:
                    s = '{}'.format(dt).strip()
                    if not s:
                        return(None)
                    try:  # Check for EPOCH Time
                        str = self.prepareEpochTimeString(float(s))
                        return(str)
                    except ValueError:
                        pass
                    d1 = dateutil.parser.parse(s, default=datetime.datetime(datetime.MINYEAR, 1, 1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None))
                    d2 = dateutil.parser.parse(s, default=datetime.datetime(datetime.MINYEAR, 2, 2, hour=1, minute=1, second=1, microsecond=1, tzinfo=None))
                    str = self.prepareDateString(d1, d2)
                    return(str)
            else:
                # First format the date portion of the string
                if not date:
                    return(None)
                # If we have a date string that only has partial values items
                # will be stored here. We will use it at the end if there were not
                # time values.
                date_str_partial = None
                if isinstance(date, QDateTime):
                    year = date.date().year()
                    month = date.date().month()
                    day = date.date().day()
                    date_str = '{:04d}-{:02d}-{:02d}'.format(year, month, day)
                elif isinstance(date, QDate):
                    year = date.year()
                    month = date.month()
                    day = date.day()
                    date_str = '{:04d}-{:02d}-{:02d}'.format(year, month, day)
                else:
                    s = '{}'.format(date).strip()
                    if not s:
                        return(None)
                    d1 = dateutil.parser.parse(s, default=datetime.datetime(datetime.MINYEAR, 1, 1))
                    if not time:
                        d2 = dateutil.parser.parse(s, default=datetime.datetime(datetime.MINYEAR, 2, 2))
                        date_str_partial = '{:04d}'.format(d1.year)
                        if d1.month == d2.month:
                            date_str_partial = date_str_partial + '-{:02d}'.format(d1.month)
                        if d1.day == d2.day:
                            date_str_partial = date_str_partial + '-{:02d}'.format(d1.day)
                    date_str = '{:04d}-{:02d}-{:02d}'.format(d1.year, d1.month, d1.day)

                # Format the time portion string
                time_str = None
                if time:
                    if isinstance(time, QDateTime):
                        hour = time.time().hour()
                        minute = time.time().minute()
                        second = time.time().second()
                        msec = time.time().msec()
                        if msec == 0:
                            time_str = '{:02d}:{:02d}:{:02d}'.format(hour, minute, second)
                        else:
                            time_str = '{:02d}:{:02d}:{:02d}.{:03d}'.format(hour, minute, second, msec)
                    elif isinstance(time, QTime):
                        hour = time.hour()
                        minute = time.minute()
                        second = time.second()
                        msec = time.msec()
                        if msec == 0:
                            time_str = '{:02d}:{:02d}:{:02d}'.format(hour, minute, second)
                        else:
                            time_str = '{:02d}:{:02d}:{:02d}.{:03d}'.format(hour, minute, second, msec)
                    else:
                        s = '{}'.format(time).strip()
                        if not s:
                            return(None)
                        d = dateutil.parser.parse(s, default=datetime.datetime(datetime.MINYEAR, 1, 1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None))
                        time_str = '{:02d}:{:02d}:{:02d}'.format(d.hour, d.minute, d.second)
                if time_str:
                    return(date_str + 'T' + time_str)
                else:
                    if date_str_partial:
                        return(date_str_partial)
                    return(date_str)
        except Exception:
            '''s = traceback.format_exc()
            self.feedback.pushInfo(s)'''
            return(None)

    def prepareEpochTimeString(self, dt):
        edt = datetime.datetime.fromtimestamp(dt)
        year = edt.year
        month = edt.month
        day = edt.day
        hour = edt.hour
        minute = edt.minute
        second = edt.second
        microsec = edt.microsecond
        if microsec == 0:
            str = '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}'.format(year, month, day, hour, minute, second)
        else:
            str = '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:03d}'.format(year, month, day, hour, minute, second, int(microsec / 1000))
        return(str)

    def prepareDateString(self, d1, d2):
        # if only parts of the date are valid then just return those portions
        # otherwise return a fully formatted iso string.
        # self.feedback.pushInfo('{} {} {} {} {} {}'.format(d1.year, d1.month, d1.day, d2.year, d2.month, d2.day))
        if d1.year == datetime.MINYEAR:
            return(None)
        str = '{:04d}'.format(d1.year)
        if d1.month != d2.month:
            return(str)
        str = str + '-{:02d}'.format(d1.month)
        if d1.day != d2.day:
            return(str)
        str = str + '-{:02d}'.format(d1.day)
        if d1.hour != d2.hour:
            return(str)
        # We have a valid date and time string so just return the iso formated string
        str = d1.isoformat()
        return(str)

    def name(self):
        return 'exportkmz'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/export.svg')

    def displayName(self):
        return 'Export KMZ'

    def group(self):
        return 'Vector conversion'

    def groupId(self):
        return 'vectorconversion'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def createInstance(self):
        return ExportKmzAlgorithm()
