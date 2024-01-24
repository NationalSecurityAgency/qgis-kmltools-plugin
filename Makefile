PLUGINNAME = kmltools
PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
PY_FILES = __init__.py convertGroundOverlays.py createGroundOverlayGeoTiff.py exportKmz.py htmlExpansionAlgorithm.py htmlExpansionDialog.py htmlParser.py importKml.py kmltools.py kmltoolsprocessing.py provider.py settings.py
EXTRAS = metadata.txt icon.png LICENSE
UI_FILES = htmlExpansion.ui htmlFields.ui

deploy: 
	mkdir -p $(PLUGINS)
	cp -vf $(PY_FILES) $(PLUGINS)
	cp -vf $(UI_FILES) $(PLUGINS)
	cp -vf $(EXTRAS) $(PLUGINS)
	cp -vrf icons $(PLUGINS)
	cp -vrf libs $(PLUGINS)
	cp -vfr doc $(PLUGINS)
	cp -vf helphead.html index.html
	python -m markdown -x extra readme.md >> index.html
	echo '</body>' >> index.html
	cp -vf index.html $(PLUGINS)/index.html
