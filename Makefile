PLUGINNAME = simplekml
PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
PY_FILES = simplekml.py __init__.py simpleKMLDialog.py htmlExpansionDialog.py
EXTRAS = icon.png html.png metadata.txt
UI_FILES = simplekmldialog.ui htmlExpansion.ui htmlFields.ui

deploy: 
	mkdir -p $(PLUGINS)
	cp -vf $(PY_FILES) $(PLUGINS)
	cp -vf $(UI_FILES) $(PLUGINS)
	cp -vf $(EXTRAS) $(PLUGINS)
