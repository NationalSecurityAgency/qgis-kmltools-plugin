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
from qgis.PyQt.QtCore import QVariant, QCoreApplication
from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsFields, QgsField

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink)


def tr(string):
    return QCoreApplication.translate('Processing', string)

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
                options=[
                    tr('Expand from a 2 column HTML table'),
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
        from .htmlParser import HTMLExpansionProcess
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
        return QIcon(os.path.dirname(__file__) + '/icons/html.svg')

    def displayName(self):
        return tr('Expand HTML description field')

    def group(self):
        return tr('Vector conversion')

    def groupId(self):
        return 'vectorconversion'

    def createInstance(self):
        return HTMLExpansionAlgorithm()
