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
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QObject, QVariant, Qt, QCoreApplication, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon

from qgis.core import Qgis, QgsVectorLayer, QgsFeature, QgsFields, QgsField, QgsWkbTypes, QgsMapLayerProxyModel, QgsProject

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink)

from html.parser import HTMLParser
# import traceback

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'htmlExpansion.ui'))
HTML_FIELDS_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'htmlFields.ui'))

def tr(string):
    return QCoreApplication.translate('Processing', string)

class HTMLExpansionProcess(QObject):
    addFeature = pyqtSignal(QgsFeature)

    def __init__(self, source, descField, type):
        QObject.__init__(self)
        self.source = source
        self.descField = descField
        self.type = type
        self.htmlparser = MyHTMLParser()
        self.selected = []

    def autoGenerateFileds(self):
        """Look through the description field for each vector entry
        for any HTMLtables that have
        name/value pairs and collect all the names. These will become
        the desired output expanded name fields."""
        iterator = self.source.getFeatures()
        self.htmlparser.setMode(0)
        if self.type == 0:
            for feature in iterator:
                desc = "{}".format(feature[self.descField])
                self.htmlparser.feed(desc)
                self.htmlparser.close()
        elif self.type == 1:  # tag = value
            for feature in iterator:
                desc = "{}".format(feature[self.descField])
                self.htmlparser.processHtmlTagValue(desc, '=')
        else:  # tag: value
            for feature in iterator:
                desc = "{}".format(feature[self.descField])
                self.htmlparser.processHtmlTagValue(desc, ':')
        self.selected = self.htmlparser.fieldList()

    def setDesiredFields(self, selected):
        """Set the desired expanded field names"""
        self.selected = list(selected)

    def desiredFields(self):
        """Return a list of all the desired expanded output names"""
        return self.selected

    def fields(self):
        """Return a dictionary of all the unique names and a count as to
        the number of times it had content.
        """
        return self.htmlparser.fields()

    def uniqueDesiredNames(self, names):
        """Make sure field names are not repeated. This looks at the
        source names and the desired field names to make sure they are not the
        same. If they are a number is appended to make it unique.
        """
        nameSet = set(names)
        newnames = []  # These are the unique selected field names
        for name in self.selected:
            if name in nameSet:
                # The name already exists so we need to create a new name
                n = name + "_1"
                index = 2
                # Find a unique name
                while n in nameSet:
                    n = '{}_{}'.format(name, index)
                    index += 1
                newnames.append(n)
                nameSet.add(n)
            else:
                newnames.append(name)
                nameSet.add(name)
        return(newnames)

    def processSource(self):
        """Iterate through each record and look for html table entries in the description
        filed and see if there are any name/value pairs that match the desired expanded
        ouput field names.
        """
        self.htmlparser.setMode(1)
        iterator = self.source.getFeatures()
        tableFields = self.htmlparser.fields()
        for feature in iterator:
            desc = "{}".format(feature[self.descField])
            self.htmlparser.clearData()
            if self.type == 0:
                self.htmlparser.feed(desc)
                self.htmlparser.close()
            elif self.type == 1:  # tag=value
                self.htmlparser.processHtmlTagValue(desc, '=')
            else:  # tag: value
                self.htmlparser.processHtmlTagValue(desc, ':')
            featureout = QgsFeature()
            featureout.setGeometry(feature.geometry())
            attr = []
            for item in self.selected:
                if item in tableFields:
                    attr.append(tableFields[item])
                else:
                    attr.append("")
            featureout.setAttributes(feature.attributes() + attr)
            self.addFeature.emit(featureout)

class HTMLExpansionAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to expand HTML tables located in a description field into additional
    attributes.
    """
    PrmInputLayer = 'InputLayer'
    PrmDescriptionField = 'DescriptionField'
    PrmExpansionTags = 'ExpansionTags'
    PrmOutputLayer = 'OutputLayer'
    PrmExpansionType = 'ExpansionType'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input layer'),
                [QgsProcessing.TypeVector])
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmDescriptionField,
                tr('Description field'),
                defaultValue='description',
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.String
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PrmExpansionTags,
                tr('Comma separated list of expansion tags - Left blank autogenerates all tags'),
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmExpansionType,
                tr('How to expand the description field'),
                options=[tr('Expand from a 2 column HTML table'),
                    tr('Expand from "tag = value" pairs'),
                    tr('Expand from "tag: value" pairs')],
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        field = self.parameterAsString(parameters, self.PrmDescriptionField, context)
        tags = self.parameterAsString(parameters, self.PrmExpansionTags, context).strip()
        type = self.parameterAsInt(parameters, self.PrmExpansionType, context)
        feedback.pushInfo(tags)
        if not field:
            msg = tr('Must have a valid description field')
            feedback.reportError(msg)
            raise QgsProcessingException(msg)

        # Set up the HTML expansion processor
        self.htmlProcessor = HTMLExpansionProcess(source, field, type)
        self.htmlProcessor.addFeature.connect(self.addFeature)
        # Have it generate a list of all possible expansion field names
        if self.PrmExpansionTags in parameters and tags != '':
            expansionNames = [x.strip() for x in tags.split(',')]
            feedback.pushInfo('{}'.format(expansionNames))
            self.htmlProcessor.setDesiredFields(expansionNames)
        else:
            self.htmlProcessor.autoGenerateFileds()

        srcCRS = source.sourceCrs()
        wkbtype = source.wkbType()

        # Create a copy of the fields for the output
        fieldsout = QgsFields(source.fields())
        for item in self.htmlProcessor.uniqueDesiredNames(source.fields().names()):
            fieldsout.append(QgsField(item, QVariant.String))

        (self.sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, fieldsout, wkbtype, srcCRS)

        self.htmlProcessor.processSource()
        self.htmlProcessor.addFeature.disconnect(self.addFeature)
        return {self.PrmOutputLayer: dest_id}

    def addFeature(self, f):
        self.sink.addFeature(f)

    def name(self):
        return 'htmlexpansion'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/html.png')

    def displayName(self):
        return tr('Expand HTML description field')

    def group(self):
        return tr('Vector conversion')

    def groupId(self):
        return 'vectorconversion'

    def createInstance(self):
        return HTMLExpansionAlgorithm()

class HTMLExpansionDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        """Initialize the HTML expansion dialog window."""
        super(HTMLExpansionDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.inputLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.inputLayerComboBox.layerChanged.connect(self.layerChanged)
        self.typeComboBox.addItems([
            tr('Expand from a 2 column HTML table'),
            tr('Expand from "tag = value" pairs'),
            tr('Expand from "tag: value" pairs')])

    def showEvent(self, event):
        """The dialog is being shown. We need to initialize it."""
        super(HTMLExpansionDialog, self).showEvent(event)
        self.layerChanged()

    def accept(self):
        """Called when the OK button has been pressed."""
        layer = self.inputLayerComboBox.currentLayer()
        if not layer:
            return
        newlayername = self.outputLayerLineEdit.text().strip()
        type = self.typeComboBox.currentIndex()

        # Find all the possible fields in the description area
        field = self.descriptionComboBox.currentField()
        index = layer.fields().indexFromName(field)
        if index == -1:
            self.iface.messageBar().pushMessage("", "Invalid field name", level=Qgis.Warning, duration=3)
            return

        # Set up the HTML expansion processor
        self.htmlProcessor = HTMLExpansionProcess(layer, field, type)
        self.htmlProcessor.addFeature.connect(self.addFeature)
        # Have it generate a list of all possible expansion field names
        self.htmlProcessor.autoGenerateFileds()

        # From the expansion processor get the list of possible expansion fields
        # and show a popup of them so the user can select which he wants in the output.
        fieldsDialog = HTMLFieldSelectionDialog(self.iface, self.htmlProcessor.fields())
        fieldsDialog.exec_()
        # From the users selections of expansion fields, set them in the processor.
        # This is just a list of names.
        self.htmlProcessor.setDesiredFields(fieldsDialog.selected)

        wkbtype = layer.wkbType()
        layercrs = layer.crs()
        # Create the new list of attribute names from the original data with the unique
        # expansion names.
        fieldsout = QgsFields(layer.fields())
        for item in self.htmlProcessor.uniqueDesiredNames(layer.fields().names()):
            fieldsout.append(QgsField(item, QVariant.String))
        newLayer = QgsVectorLayer("{}?crs={}".format(QgsWkbTypes.displayString(wkbtype), layercrs.authid()), newlayername, "memory")

        self.dp = newLayer.dataProvider()
        self.dp.addAttributes(fieldsout)
        newLayer.updateFields()

        # Process each record in the input layer with the expanded entries.
        # The actual record is added with the 'addFeature' callback
        self.htmlProcessor.processSource()
        self.htmlProcessor.addFeature.disconnect(self.addFeature)

        newLayer.updateExtents()
        QgsProject.instance().addMapLayer(newLayer)
        self.close()

    def addFeature(self, f):
        self.dp.addFeatures([f])

    def layerChanged(self):
        if not self.isVisible():
            return
        layer = self.inputLayerComboBox.currentLayer()
        self.descriptionComboBox.setLayer(layer)
        if layer:
            self.descriptionComboBox.setField('description')

class MyHTMLParser(HTMLParser):
    def __init__(self):
        # initialize the base class
        HTMLParser.__init__(self)
        self.tableFields = {}
        self.inTable = False
        self.inTR = False
        self.inTD = False
        self.col = -1
        self.mapping = {}
        self.buffer1 = ""
        self.buffer2 = ""
        self.mode = 0

    def clearData(self):
        self.tableFields.clear()

    def setMode(self, mode):
        self.mode = mode
        self.clearData()

    def fieldList(self):
        return [*self.tableFields]

    def fields(self):
        return self.tableFields

    def processHtmlTagValue(self, desc, delim='='):
        lines = re.split(r'<br.*?>|<p.*?>|<td.*?>|<th.*?>', desc, flags=re.IGNORECASE)
        p = re.compile(r'<.*?>')
        s = re.compile(r'\s+')
        parser = re.compile(r'(.+?)\s*{}\s*(.+)'.format(delim))
        for line in lines:
            line = p.sub('', line)  # remove HTML formatting
            line = s.sub(' ', line)  # remove extra white space
            line = line.strip()
            m = parser.match(line)
            if m:  # We have a tag=value match
                tag = m.group(1).strip()
                value = m.group(2).strip()
                if self.mode == 0:
                    if tag in self.tableFields:
                        if value != '':
                            self.tableFields[tag] += 1
                    else:
                        if value != '':
                            self.tableFields[tag] = 1
                        else:
                            self.tableFields[tag] = 0
                else:
                    self.tableFields[tag] = value

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'table':
            self.inTable = True
        elif tag == 'tr':
            self.inTR = True
            self.col = -1
            self.buffer1 = ""
            self.buffer2 = ""
        elif tag == 'th' or tag == 'td':
            self.col += 1
            self.inTD = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'table':
            self.inTable = False
        elif tag == 'tr' and self.col >= 1:
            if self.mode == 0:
                if self.buffer1 in self.tableFields:
                    if self.buffer2 != '':
                        self.tableFields[self.buffer1] += 1
                else:
                    if self.buffer2 != '':
                        self.tableFields[self.buffer1] = 1
                    else:
                        self.tableFields[self.buffer1] = 0
            else:
                self.tableFields[self.buffer1] = self.buffer2

            self.col = -1
            self.inTR = False
            self.inTD = False
        elif tag == 'th' or tag == 'td':
            self.inTD = False

    def handle_data(self, data):
        if self.inTable:
            if self.inTD:
                if self.col == 0:
                    self.buffer1 += data.strip()
                elif self.col == 1:
                    self.buffer2 += data.strip()

class HTMLFieldSelectionDialog(QDialog, HTML_FIELDS_CLASS):
    def __init__(self, iface, feat):
        super(HTMLFieldSelectionDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.feat = feat
        self.selected = []
        self.selectAllButton.clicked.connect(self.selectAll)
        self.clearButton.clicked.connect(self.clearAll)
        self.checkBox.stateChanged.connect(self.initModel)
        self.initModel()

    def initModel(self):
        self.model = QStandardItemModel(self.listView)
        state = self.checkBox.isChecked()
        for key in list(self.feat.keys()):
            if state is False or self.feat[key] > 0:
                item = QStandardItem()
                item.setText(key)
                item.setCheckable(True)
                item.setSelectable(False)
                self.model.appendRow(item)
        self.listView.setModel(self.model)
        self.listView.show()

    def selectAll(self):
        cnt = self.model.rowCount()
        for i in range(0, cnt):
            item = self.model.item(i)
            item.setCheckState(Qt.Checked)

    def clearAll(self):
        cnt = self.model.rowCount()
        for i in range(0, cnt):
            item = self.model.item(i)
            item.setCheckState(Qt.Unchecked)

    def accept(self):
        self.selected = []
        cnt = self.model.rowCount()
        for i in range(0, cnt):
            item = self.model.item(i)
            if item.checkState() == Qt.Checked:
                self.selected.append(item.text())
        self.close()
