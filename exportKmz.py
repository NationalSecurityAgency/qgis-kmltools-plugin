import os
import math
from qgis.PyQt.QtCore import QUrl, QTime, QDateTime, QDate, QSize, QPointF
from qgis.PyQt.QtGui import QIcon

from qgis.core import (
    QgsCoordinateTransform, QgsCoordinateReferenceSystem,
    QgsProject, QgsRenderContext, QgsWkbTypes)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSource)

import dateutil.parser
import datetime
from xml.sax.saxutils import escape
import simplekml
# import traceback
import tempfile
import utils

def qcolor2kmlcolor(color):
    return('{:02x}{:02x}{:02x}{:02x}'.format(color.alpha(), color.blue(), color.green(), color.red()))


ALTITUDE_MODES = ['clampToGround', 'relativeToGround', 'absolute']

class ExportKmzAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to import KML and KMZ files.
    """
    PrmInputLayer = 'InputLayer'
    PrmOutputKmz = 'OutputKmz'
    PrmNameField = 'NameField'
    PrmDescriptionField = 'DescriptionField'
    PrmExportStyle = 'ExportStyle'
    PrmShowLabels = 'ShowLabels'
    PrmLineWidthFactor = 'LineWidthFactor'
    PrmAltitudeInterpretation = 'AltitudeInterpretation'
    PrmAltitudeMode = 'AltitudeMode'
    PrmAltitudeModeField = 'AltitudeModeField'
    PrmAltitudeField = 'AltitudeField'
    PrmDateTimeStampField = 'DateTimeStampField'
    PrmDateStampField = 'DateStampField'
    PrmTimeStampField = 'TimeStampField'
    PrmDateTimeBeginField = 'DateTimeBeginField'
    PrmDateBeginField = 'DateBeginField'
    PrmTimeBeginField = 'TimeBeginField'
    PrmDateTimeEndField = 'DateTimeEndField'
    PrmDateEndField = 'DateEndField'
    PrmTimeEndField = 'TimeEndField'
    epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
    temp_dir = tempfile.gettempdir()

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                'Input layer',
                [QgsProcessing.TypeVector])
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmNameField,
                'Name field',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                defaultValue='name',
                optional=True
            )
        )
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
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmExportStyle,
                'Export style for single and categorized symbols',
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmShowLabels,
                'Show line labels',
                False,
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
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        layer = self.parameterAsLayer(parameters, self.PrmInputLayer, context)
        name_field = self.parameterAsString(parameters, self.PrmNameField, context)
        desc_fields = self.parameterAsFields(parameters, self.PrmDescriptionField, context)
        desc_cnt = len(desc_fields)
        export_style = self.parameterAsInt(parameters, self.PrmExportStyle, context)
        show_labels = self.parameterAsInt(parameters, self.PrmShowLabels, context)
        self.line_width_factor = self.parameterAsDouble(parameters, self.PrmLineWidthFactor, context)
        alt_interpret = self.parameterAsEnum(parameters, self.PrmAltitudeInterpretation, context)
        if self.PrmAltitudeMode not in parameters or parameters[self.PrmAltitudeMode] is None:
            default_alt_mode = None
        else:
            default_alt_mode = ALTITUDE_MODES[self.parameterAsEnum(parameters, self.PrmAltitudeMode, context)]
        alt_mode_field = self.parameterAsString(parameters, self.PrmAltitudeModeField, context)
        altitude_field = self.parameterAsString(parameters, self.PrmAltitudeField, context)
        date_time_stamp_field = self.parameterAsString(parameters, self.PrmDateTimeStampField, context)
        date_stamp_field = self.parameterAsString(parameters, self.PrmDateStampField, context)
        time_stamp_field = self.parameterAsString(parameters, self.PrmTimeStampField, context)
        date_time_begin_field = self.parameterAsString(parameters, self.PrmDateTimeBeginField, context)
        date_begin_field = self.parameterAsString(parameters, self.PrmDateBeginField, context)
        time_begin_field = self.parameterAsString(parameters, self.PrmTimeBeginField, context)
        date_time_end_field = self.parameterAsString(parameters, self.PrmDateTimeEndField, context)
        date_end_field = self.parameterAsString(parameters, self.PrmDateEndField, context)
        time_end_field = self.parameterAsString(parameters, self.PrmTimeEndField, context)

        wkbtype = source.wkbType()
        hasz = QgsWkbTypes.hasZ(wkbtype)
        if alt_interpret == 0:
            hasz = False
            default_alt_mode = None
            alt_mode_field = None
            altitude_field = None
        elif alt_interpret == 2:
            hasz = False
        geomtype = QgsWkbTypes.geometryType(wkbtype)
        src_crs = source.sourceCrs()
        if src_crs != self.epsg4326:
            geomTo4326 = QgsCoordinateTransform(src_crs, self.epsg4326, QgsProject.instance())

        self.symcontext = QgsRenderContext.fromMapSettings(utils.canvas.mapSettings())
        self.png_icons = []
        self.cat_styles = {}
        kml = simplekml.Kml()
        kml.resetidcounter()
        if export_style:
            render = layer.renderer()
            render_type = render.type()
            if render_type == 'singleSymbol':
                export_style = 1
            elif render_type == 'categorizedSymbol':
                export_style = 2
            else:
                feedback.reportError('Only single symobl and categorized symbols can be exported. Processing will continue without symbol export.')
                export_style = 0
            if export_style:
                self.initStyles(export_style, show_labels, geomtype, layer, render, kml)

        folder = kml.newfolder(name=source.sourceName())
        altitude = 0
        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0
        num_features = 0
        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            num_features += 1
            if altitude_field:
                try:
                    altitude = float(feature[altitude_field])
                except Exception:
                    altitude = 0
            geom = feature.geometry()
            if src_crs != self.epsg4326:
                geom.transform(geomTo4326)
            if geom.isMultipart():
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
                        kmlpart.coords = [(pt.x(), pt.y(), pt.z())]
                    else:
                        kmlpart.coords = [(pt.x(), pt.y(), altitude)]
            elif geomtype == QgsWkbTypes.LineGeometry:  # LINES
                for part in geom.parts():
                    kmlpart = kmlgeom.newlinestring()
                    self.setAltitudeMode(kmlpart, feature, default_alt_mode, alt_mode_field)
                    if kml_item is None:
                        kml_item = kmlpart
                    if hasz:
                        kmlpart.coords = [(pt.x(), pt.y(), pt.z()) for pt in part]
                    else:
                        kmlpart.coords = [(pt.x(), pt.y(), altitude) for pt in part]
            elif geomtype == QgsWkbTypes.PolygonGeometry:  # POLYGONS
                for part in geom.parts():
                    kmlpart = kmlgeom.newpolygon()
                    self.setAltitudeMode(kmlpart, feature, default_alt_mode, alt_mode_field)
                    if kml_item is None:
                        kml_item = kmlpart
                    num_interior_rings = part.numInteriorRings()
                    ext_ring = part.exteriorRing()
                    if hasz:
                        kmlpart.outerboundaryis = [(pt.x(), pt.y(), pt.z()) for pt in ext_ring]
                    else:
                        kmlpart.outerboundaryis = [(pt.x(), pt.y(), altitude) for pt in ext_ring]
                    if num_interior_rings:
                        ib = []
                        for i in range(num_interior_rings):
                            if hasz:
                                ib.append([(pt.x(), pt.y(), pt.z()) for pt in part.interiorRing(i)])
                            else:
                                ib.append([(pt.x(), pt.y(), altitude) for pt in part.interiorRing(i)])
                        kmlpart.innerboundaryis = ib

            self.exportStyle(kml_item, feature, export_style)
            if name_field:
                self.exportName(kml_item, feature[name_field])

            if desc_cnt == 1:
                self.exportDescription(kml_item, feature[desc_fields[0]])
            elif desc_cnt > 1:
                self.exportFields(kml_item, desc_fields, feature)

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

    def exportStyle(self, kml_item, feature, export_style):
        if export_style == 1:
            kml_item.style = self.simple_style
        elif export_style == 2:
            cat = '{}'.format(feature[self.style_field])
            # self.feedback.pushInfo('cat: {}'.format(cat))
            if cat not in self.cat_styles:
                # self.feedback.pushInfo('cat not in cat_styles')
                cat = ''
            if cat in self.cat_styles:
                # self.feedback.pushInfo('cat in cat_styles')
                kml_item.style = self.cat_styles[cat]
                # self.feedback.pushInfo('style {}'.format(kml_item.style))

    def initStyles(self, type, show_labels, geomtype, layer, render, kml):
        if type == 1:
            symbol = render.symbol()
            self.simple_style = simplekml.Style()
            if geomtype == QgsWkbTypes.PointGeometry:
                sym_size = symbol.size(self.symcontext)
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
            elif geomtype == QgsWkbTypes.LineGeometry:
                self.simple_style.linestyle.color = qcolor2kmlcolor(symbol.color())
                self.simple_style.linestyle.width = symbol.width() * self.line_width_factor
                if show_labels:
                    self.simple_style.linestyle.gxlabelvisibility = True
            else:
                symbol_layer = symbol.symbolLayer(0)
                self.simple_style.linestyle.color = qcolor2kmlcolor(symbol_layer.strokeColor())
                self.simple_style.linestyle.width = symbol_layer.strokeWidth() * self.line_width_factor
                self.simple_style.polystyle.color = qcolor2kmlcolor(symbol_layer.color())
        else:
            self.style_field = render.classAttribute()
            for idx, category in enumerate(render.categories()):
                cat_style = simplekml.Style()
                symbol = category.symbol()
                if geomtype == QgsWkbTypes.PointGeometry:
                    sym_size = symbol.size(self.symcontext)
                    # self.feedback.pushInfo('sym_size: {}'.format(sym_size))
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
                elif geomtype == QgsWkbTypes.LineGeometry:
                    cat_style.linestyle.color = qcolor2kmlcolor(symbol.color())
                    cat_style.linestyle.width = symbol.width() * self.line_width_factor
                    if show_labels:
                        cat_style.linestyle.gxlabelvisibility = True
                else:
                    symbol_layer = symbol.symbolLayer(0)
                    cat_style.linestyle.color = qcolor2kmlcolor(symbol_layer.strokeColor())
                    cat_style.linestyle.width = symbol_layer.strokeWidth() * self.line_width_factor
                    cat_style.polystyle.color = qcolor2kmlcolor(symbol_layer.color())
                self.cat_styles[category.value()] = cat_style

    def cleanup(self):
        for icon in self.png_icons:
            if os.path.exists(icon):
                os.remove(icon)

    def exportName(self, kml_item, fname):
        name = '{}'.format(fname)
        name = name.strip()
        kml_item.name = name

    def exportDescription(self, kml_item, desc):
        desc = '{}'.format(desc).strip()
        if desc:
            kml_item.description = desc

    def exportFields(self, kml_item, fields, f):
        for field in fields:
            v = escape('{}'.format(f[field]).strip())
            if v != '':
                kml_item.extendeddata.newdata(name=field, value=v, displayname=field)

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
        return QIcon(os.path.dirname(__file__) + '/icons/export.png')

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
