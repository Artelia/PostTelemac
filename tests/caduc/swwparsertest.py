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
import sys
import os
from PyQt4 import uic, QtCore, QtGui

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from meshlayertools.meshlayer_opengl_tool import OpenGLDialog
from meshlayerparsers.posttelemac_anuga_parser import PostTelemacSWWParser


        
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
import sys
import os
from PyQt4 import uic, QtCore, QtGui

#sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from meshlayertools.meshlayer_opengl_tool import OpenGLDialog
from meshlayerparsers.posttelemac_anuga_parser import PostTelemacSWWParser



def doThings():
    try:
        print 'DEBUT'
        path = os.path.normpath('C://00_Bureau//00_QGIs//PostTelemac_test_file//test2.sww')
        parser = PostTelemacSWWParser()
        parser.loadHydrauFile(path)
        
        
        
        print 'END'
    except Exception, e:
        print str(e)
    
        
if __name__ == '__main__':
    doThings()
    
