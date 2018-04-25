PLUGINNAME = simplekml
PY_FILES = simplekml.py __init__.py simpleKMLDialog.py htmlExpansionDialog.py
EXTRAS = icon.png html.png metadata.txt
UI_FILES = simplekmldialog.ui htmlExpansion.ui htmlFields.ui

deploy: 
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(PY_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
