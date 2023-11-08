"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
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
