PLUGINNAME = kmltools
PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
PY_FILES = kmltools.py __init__.py importKml.py htmlExpansionDialog.py htmlParser.py htmlExpansionAlgorithm.py exportKmz.py provider.py
EXTRAS = metadata.txt
UI_FILES = htmlExpansion.ui htmlFields.ui

deploy: 
	mkdir -p $(PLUGINS)
	cp -vf $(PY_FILES) $(PLUGINS)
	cp -vf $(UI_FILES) $(PLUGINS)
	cp -vf $(EXTRAS) $(PLUGINS)
	cp -vrf icons $(PLUGINS)
	cp -vrf libs $(PLUGINS)
	cp -vf helphead.html $(PLUGINS)/index.html
	cp -vfr doc $(PLUGINS)
	python -m markdown -x extra readme.md >> $(PLUGINS)/index.html
	echo '</body>' >> $(PLUGINS)/index.html
