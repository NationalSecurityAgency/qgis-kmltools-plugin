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
from qgis.PyQt.QtCore import QObject, QSettings, QVariant, Qt, QUrl, QCoreApplication, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon

from qgis.core import Qgis, QgsVectorLayer, QgsFeature, QgsFields, QgsField, QgsWkbTypes, QgsMapLayerProxyModel, QgsProject

from qgis.core import (QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink)

from html.parser import HTMLParser
#import traceback

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'htmlExpansion.ui'))
HTML_FIELDS_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'htmlFields.ui'))

def tr(string):
    return QCoreApplication.translate('Processing', string)

class HTMLExpansionProcess(QObject):
    addFeature = pyqtSignal(QgsFeature)
    def __init__(self, source, descField):
        QObject.__init__(self)
        self.source = source
        self.descField = descField
        self.htmlparser = MyHTMLParser()
        self.selected = []
        
    def autoGenerateFileds(self):
        iterator = self.source.getFeatures()
        self.htmlparser.setMode(0)
        for feature in iterator:
            desc = "{}".format(feature[self.descField])
            self.htmlparser.feed(desc)
            self.htmlparser.close()
        self.selected = self.htmlparser.fieldList()

    def setSelectedFields(self, selected):
        self.selected = list(selected)
        
    def selectedFields(self):
        return self.selected
        
    def fields(self):
        return self.htmlparser.fields()
        
    def processSource(self):
        self.htmlparser.setMode(1)
        iterator = self.source.getFeatures()
        tableFields = self.htmlparser.fields()
        for feature in iterator:
            desc = "{}".format(feature[self.descField])
            self.htmlparser.clearData()
            self.htmlparser.feed(desc)
            self.htmlparser.close()
            featureout = QgsFeature()
            featureout.setGeometry(feature.geometry())
            attr = []
            for item in self.selected:
                if item in tableFields:
                    attr.append(tableFields[item])
                else:
                    attr.append("")
            featureout.setAttributes(feature.attributes()+attr)
            self.addFeature.emit(featureout)
    
        
class HTMLExpansionAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to import KML and KMZ files.
    """
    PrmInputLayer = 'InputLayer'
    PrmDescriptionField = 'DescriptionField'
    PrmOutputLayer = 'OutputLayer'
    
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
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
            )
    
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        field = self.parameterAsString(parameters, self.PrmDescriptionField, context)
        if not field:
            msg = tr('Must have a valid description field')
            feedback.reportError(msg)
            raise QgsProcessingException(msg)
        
        self.htmlProcessor = HTMLExpansionProcess(source, field)
        self.htmlProcessor.addFeature.connect(self.addFeature)
        self.htmlProcessor.autoGenerateFileds()
        
        srcCRS = source.sourceCrs()
        wkbtype = source.wkbType()
        
        fieldsout = QgsFields(source.fields())
        for item in self.htmlProcessor.selectedFields():
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
        return tr('Expand HTML description table')
    
    def group(self):
        return tr('Vector conversion')
        
    def groupId(self):
        return 'vectorconversion'
        
    def createInstance(self):
        return HTMLExpansionAlgorithm()

class HTMLExpansionDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        """Initialize the QGIS Simple KML inport dialog window."""
        super(HTMLExpansionDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.inputLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.inputLayerComboBox.layerChanged.connect(self.layerChanged)
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(HTMLExpansionDialog, self).showEvent(event)
        self.layerChanged()
    
    def accept(self):
        '''Called when the OK button has been pressed.'''
        layer = self.inputLayerComboBox.currentLayer()
        if not layer:
            return
        newlayername = self.outputLayerLineEdit.text().strip()
            
        # Find all the possible fields in the description area
        field = self.descriptionComboBox.currentField()
        index = layer.fields().indexFromName(field)
        if index == -1:
            self.iface.messageBar().pushMessage("", "Invalid field name", level=Qgis.Warning, duration=3)
            return
        
        self.htmlProcessor = HTMLExpansionProcess(layer, field)
        self.htmlProcessor.addFeature.connect(self.addFeature)
        self.htmlProcessor.autoGenerateFileds()
        
        fieldsDialog = HTMLFieldSelectionDialog(self.iface, self.htmlProcessor.fields())
        fieldsDialog.exec_()
        self.htmlProcessor.setSelectedFields(fieldsDialog.selected)
        
        
        wkbtype = layer.wkbType()
        layercrs = layer.crs()
        fieldsout = QgsFields(layer.fields())
        for item in self.htmlProcessor.selectedFields():
            fieldsout.append(QgsField(item, QVariant.String))
        newLayer = QgsVectorLayer("{}?crs={}".format(QgsWkbTypes.displayString(wkbtype), layercrs.authid()), newlayername, "memory")
        
        self.dp = newLayer.dataProvider()
        self.dp.addAttributes(fieldsout)
        newLayer.updateFields()
        
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
            if state == False or self.feat[key] > 0:
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