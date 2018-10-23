# QGIS KML Tools

The native QGIS importer creates separate layers for each folder within a KML/KMZ. If there are hundreds or thousands of layers, the import can be very slow, crash QGIS, or create an undesirable number of layers. This plugin only creates one point layer, one line layer, and one polygon layer. This makes the KML/KMZ import very quick. It adds the nested folder structure to a field in the QGIS layer which you can then use to sort and filter on what were previously folders in the KML.

***KML Tools*** can be found in the QGIS menu under ***Vector->KML Tools***, on the tool bar, or in the Processing Toolbox under ***KML Tools****. It has two tools.

<img src="icon.png" alt="Import KML/KMZ"> ***Import KML/KMZ*** - This functions as the name implies. It's interface is simple. Click on the ... button on the right of ***Import KML/KMZ file*** to select your file. Choose whether you want to include points, lines or polygons from the KML as QGIS output layers. If the KML file does not contain one of these geometry types, then the associated layer will not be created anyway. 

<div style="text-align:center"><img src="doc/import.jpg" alt="Import KML/KMZ"></div>

<img src="html.png" alt="HTML description expansion"> ***Expand HTML description field*** - This attempts to expand HTML tag/value pairs into separate fields. Before this can be run, the KML needs to be imported into QGIS with ***Import KML/KMZ***. Next select from ***How to expand the description field*** option one of the following:

* ***Expand from a 2 column HTML table*** - If the KML has a description entry that contains an HTML table with two columns were the first column represents a table or field name and the second column its value, then this option will parse these fields and add them to a new attribute table field.  This is an example of data that it expands.

```
    <table>
        <tr><td>City</td><td>Provo</td></tr>
        <tr><td>State</td><td>Utah</td></tr>
    </table>
```
* ***Expand from "tag = value" pairs*** - If the KML has a description entry that contains "tag = value" entries separated by new paragraphs, line breaks, or entries in a single table column, then this option will parse these fields and add them to a new attribute table field. This is an example of data that it expands.

```
    <b>City<b/> = Provo<br/>
    <b>State<b/> = Utah<br/>
```
* ***Expand from "tag: value" pairs*** - If the KML has a description entry that contains "tag: value" entries separated by new paragraphs, line breaks, or entries in a single table column, then this option will parse these fields and add them to a new attribute table field. This is an example of data that it expands.

```
    <b>City:<b/> Provo<br/>
    <b>State:<b/> Utah<br/>
```

This can either be run from the menu, tool bar, or *Processing Toolbox*; however, running it from the menu or tool bar provides user interaction during the conversion to select which fields they want to expand. During expansion some of the expansion names may already exist in the table. If that is the case then an '_' followed by a number is appended to the end.

<div style="text-align:center"><img src="doc/html.jpg" alt="HTML Expander"></div>

Select the input layer and the field that has an HTML table of tag/value rows. Press ***OK*** and it will look through all records and find all possible tag values. If it finds tags, then it will pop up a menu for you to select which tags you want expanded into table entries like this.

<div style="text-align:center"><img src="doc/html2.jpg" alt="HTML Expander"></div>

The ***Processing Toolbox*** version of ***Expand HTML description table*** operates a little differently because processing routines cannot be interactive. In this case it will expand all possible tags that are found. Optionally, you can include a list of name tags you want expanded if you know them ahead of time. This is the Processing expansion dialog box.

<div style="text-align:center"><img src="doc/html3.jpg" alt="HTML Expander"></div>

Because there is no standard way of including additional information in the KML description entry, it is difficult to come up with a way to expand all cases. Right now this just works with two column HTML tables, ***tag=value***, and ***tag: value*** pairs, but please let us know if there are other description formats that you would like us to tackle.

This plugin may not be for everyone as it does not implement the entire KML specification, but if you find that it is missing some aspect of KML, let us know and perhaps we can add it.
