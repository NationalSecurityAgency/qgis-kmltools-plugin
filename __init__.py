try:
    import simplekml
except Exception:
    import os
    import site
    site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/libs'))

def classFactory(iface):
    from .kmltools import KMLTools
    return KMLTools(iface)
