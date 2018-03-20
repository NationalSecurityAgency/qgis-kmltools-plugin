PLUGINNAME = simplekml
PY_FILES = simplekml.py __init__.py simpleKMLDialog.py
EXTRAS = icon.png metadata.txt
UI_FILES = simplekmldialog.ui

deploy: 
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(PY_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
