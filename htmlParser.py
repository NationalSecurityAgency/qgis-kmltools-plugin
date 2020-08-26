import re
from qgis.PyQt.QtCore import QObject, pyqtSignal

from qgis.core import QgsFeature

from html.parser import HTMLParser

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
