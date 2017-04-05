# -*- coding: utf-8 -*-

"""
/***************************************************************************
 PostTelemac
                                 A QGIS plugin
 Post Traitment or Telemac
                              -------------------
        begin                : 2015-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Artelia
        email                : patrice.Verchere@arteliagroup.com
 ***************************************************************************/
 
 ***************************************************************************/
 get Image class
 Generate a Qimage from selafin file to be displayed in map canvas 
 with tht draw method of posttelemacpluginlayer
 
Versions :
0.0 : debut

 ***************************************************************************/
"""

import qgis


def getQgisVersion():
    try:
        version = qgis.core.QGis.QGIS_VERSION
    except:
        version = qgis.core.Qgis.QGIS_VERSION
    return float('.'.join(version.split('.')[0:2]))

        

            
        
        
        
        

        
        
        