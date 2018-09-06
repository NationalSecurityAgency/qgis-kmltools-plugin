# QGIS KML Tools

The native QGIS importer creates separate layers for each folder within a KML/KMZ. If there are hundreds or thousands of layers, the import can be very slow, crash QGIS, or create an undesirable number of layers. This plugin only creates one point layer, one line layer, and one polygon layer. This makes the KML/KMZ import very quick. It adds the nested folder structure to a field in the QGIS layer which you can then use to sort and filter on what were previously folders in the KML.

***KML Tools*** can be found in the QGIS menu under ***Vector->KML Tools***, on the tool bar, or in the Processing Toolbox under ***KML Tools****. It has two tools.

<img src="icon.png" alt="Import KML/KMZ"> ***Import KML/KMZ*** - This functions as the name implies. It's interface is simple. Click on the ... button on the right of ***Import KML/KMZ file*** to select your file. Choose whether you want to include points, lines or polygons from the KML as QGIS output layers. If the KML file does not contain one of these geometry types, then the associated layer will not be created anyway. 

<div style="text-align:center"><img src="doc/import.jpg" alt="Import KML/KMZ"></div>

<img src="html.png" alt="HTML description expansion"> ***Expand HTML description table*** - This has a very narrow purpose. Before this can be run, the KML needs to be imported into QGIS with ***Import KML/KMZ***. If the KML has a description entry that contains an HTML table with two columns were the first column represents a table or field name and the second column its value, then this function will parse these fields and add them to a new attribute table field. This can either be run from the menu, tool bar, or *Processing Toolbox*; however, running it from the menu or tool bar provides user interaction during the conversion to select which fields they want to expand. 

<div style="text-align:center"><img src="doc/html.jpg" alt="HTML Expander"></div>

Select the input layer and the field that has an HTML table of tag/value rows. Press ***OK*** and it will look through all records and find all possible tag values. If it finds tags, then it will popup a menu for you to select which tags you want expanded into table entries like this.

<div style="text-align:center"><img src="doc/html2.jpg" alt="HTML Expander"></div>

This is the type of data that it currently expands. The two tags will become **City** and **State**.

<code><pre>
    &lt;table&gt;
        &lt;tr&gt;&lt;td&gt;City&lt;/td&gt;&lt;td&gt;Provo&lt;/td&gt;&lt;/tr&gt;
        &lt;tr&gt;&lt;td&gt;State&lt;/td&gt;&lt;td&gt;Utah&lt;/td&gt;&lt;/tr&gt;
    &lt;/table&gt;
</pre></code>

The ***Processing Toolbox*** version of ***Expand HTML description table*** operates a little differently because processing routines cannot be interactive. In this case it will expand all possible tags that are found.

Because there is no standard way of including additional information in the KML description entry, it is difficult to come up with a way to expand all cases. Right now this just works with HTML tables, but please let us know if there are other description formats that you would like us to tackle.

This plugin may not be for everyone as it does not implement the entire KML specification, but if you find that it is missing some aspect of KML, let us know and perhaps we can add it.
