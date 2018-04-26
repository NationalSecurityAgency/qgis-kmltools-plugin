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
from PyQt4 import uic
from PyQt4.QtCore import QSettings, QVariant, Qt
from PyQt4.QtGui import QDialog, QStandardItemModel, QStandardItem

from qgis.core import QgsVectorLayer, QgsPoint, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsMapLayerRegistry, QGis
from qgis.gui import QgsMessageBar, QgsMapLayerProxyModel
from HTMLParser import HTMLParser
#import traceback

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'htmlExpansion.ui'))
HTML_FIELDS_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'htmlFields.ui'))

        
class HTMLExpansionDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        """Initialize the QGIS Simple KML inport dialog window."""
        super(HTMLExpansionDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.inputLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.inputLayerComboBox.layerChanged.connect(self.layerChanged)
        self.tableFeatures = {}
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(HTMLExpansionDialog, self).showEvent(event)
        self.layerChanged()
    
    def accept(self):
        '''Called when the OK button has been pressed.'''
        layer = self.inputLayerComboBox.currentLayer()
        if not layer:
            return
        newlayername = self.outputLayerLineEdit.text()
        self.tableFeatures = {}
        wkbtype = layer.wkbType()
        layercrs = layer.crs()
        if wkbtype != QGis.WKBLineString and wkbtype != QGis.WKBPolygon and wkbtype != QGis.WKBPoint:
            self.iface.messageBar().pushMessage("", "Invalid input layer type", level=QgsMessageBar.WARNING, duration=3)
            return
            
        htmlparser = MyHTMLParser(self.tableFeatures)
        # Find all the possible fields in the description area
        field = self.descriptionComboBox.currentField()
        index = layer.fieldNameIndex(field)
        if index == -1:
            self.iface.messageBar().pushMessage("", "Invalid field name", level=QgsMessageBar.WARNING, duration=3)
            return
        
        iterator = layer.getFeatures()
        htmlparser.setMode(0)
        for feature in iterator:
            desc = "{}".format(feature[index])
            htmlparser.feed(desc)
            htmlparser.close()
        if len(self.tableFeatures) == 0:
            self.iface.messageBar().pushMessage("", "No HTML tables were found.", level=QgsMessageBar.WARNING, duration=3)
            return
        
        fieldsDialog = HTMLFieldSelectionDialog(self.iface, self.tableFeatures)
        fieldsDialog.exec_()
        items = fieldsDialog.selected
        
        fields = layer.fields()
        fieldsout = QgsFields(fields)
        for item in items:
            fieldsout.append(QgsField(item, QVariant.String))
        if wkbtype == QGis.WKBLineString:
            newLayer = QgsVectorLayer("LineString?crs={}".format(layercrs.authid()), newlayername, "memory")
        elif wkbtype == QGis.WKBPolygon:
            newLayer = QgsVectorLayer("Polygon?crs={}".format(layercrs.authid()), newlayername, "memory")
        elif wkbtype == QGis.WKBPoint:
            newLayer = QgsVectorLayer("Point?crs={}".format(layercrs.authid()), newlayername, "memory")
        dp = newLayer.dataProvider()
        dp.addAttributes(fieldsout)
        newLayer.updateFields()
        iterator = layer.getFeatures()
        htmlparser.setMode(1)
        for feature in iterator:
            desc = "{}".format(feature[index])
            htmlparser.clearData()
            htmlparser.feed(desc)
            htmlparser.close()
            featureout = QgsFeature()
            featureout.setGeometry(feature.geometry())
            attr = []
            for item in items:
                if item in self.tableFeatures:
                    attr.append(self.tableFeatures[item])
                else:
                    attr.append("")
            featureout.setAttributes(feature.attributes()+attr)
            dp.addFeatures([featureout])
                
        newLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(newLayer)
        self.close()
        
    def layerChanged(self):
        if not self.isVisible():
            return
        layer = self.inputLayerComboBox.currentLayer()
        self.descriptionComboBox.setLayer(layer)
        if layer:
            self.descriptionComboBox.setField('description')
            
class MyHTMLParser(HTMLParser):
    def __init__(self, feat):
        # initialize the base class
        HTMLParser.__init__(self)
        self.tableFeatures = feat
        self.inTable = False
        self.inTR = False
        self.inTD = False
        self.col = -1
        self.mapping = {}
        self.buffer1 = ""
        self.buffer2 = ""
        self.mode = 0
        
    def clearData(self):
        self.tableFeatures.clear()
        
    def setMode(self, mode):
        self.mode = mode
        
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
        elif tag == 'tr':
            if self.mode == 0:
                if self.buffer1 in self.tableFeatures:
                    if self.buffer2 != '':
                        self.tableFeatures[self.buffer1] += 1
                else:
                    if self.buffer2 != '':
                        self.tableFeatures[self.buffer1] = 1
                    else:
                        self.tableFeatures[self.buffer1] = 0
            else:
                self.tableFeatures[self.buffer1] = self.buffer2
            
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
        for key in self.feat.keys():
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