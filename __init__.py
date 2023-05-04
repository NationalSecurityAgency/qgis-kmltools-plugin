try:
    import simplekml
except Exception:
    import os
    import site
    site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/libs'))

def classFactory(iface):
    if iface:
        from .kmltools import KMLTools
        return KMLTools(iface)
    else:
        # This is used when the plugin is loaded from the command line command qgis_process
        from .kmltoolsprocessing import KMLTools
        return KMLTools()
