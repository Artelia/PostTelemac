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
from qgis.PyQt import uic, QtCore, QtGui
import numpy as np

import gdal
import qgis

import time

from ctypes import *

#sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
#from PostTelemac.meshlayerparsers.posttelemac_hdf_parser import PostTelemacHDFParser
#from PostTelemac.meshlayerparsers.libs_telemac.other.Class_Serafin import Serafin
from PostTelemac.meshlayerparsers.posttelemac_selafin_parser import PostTelemacSelafinParser

"""

from meshlayertools.meshlayer_opengl_tool import OpenGLDialog
from meshlayerparsers.posttelemac_anuga_parser import PostTelemacSWWParser
"""
def testimport():
    path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
    resin = Serafin(name = path, mode = 'rb')
    test = resin.read_header()
    ikle = resin.ikle
    temp = np.array(ikle).reshape((-1,3))
    
    print(temp)
    
    #print(temp)
    #print(temp.shape)
    
    #print(temp[0][2])
    
    #print(resin.ikle)
    #print(resin.nomvar)
    #temp = resin.nomvar
    
    #print(resin.nbvar)
    #print(resin.x)
    #print(resin.y)
    
    #test1 = resin.get_temps()
    #print( resin.temps)
    
    #print(resin.read(0).shape)
    
def testParser():
    path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
    parser = PostTelemacSelafinParser()
    parser.loadHydrauFile(path)
    
    parser.hydraufile.getSERIES([1],[0],False)
    
    print(parser.getElemFaces())
    
    
        


def testctpe():
    path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
    hdf5Lib = 'c://OSGeo4W64//bin//hdf5.dll'
    lib=cdll.LoadLibrary(hdf5Lib)
    H5Fopen = lib.H5Fopen(path)
    print('ok')
    
def testboundary():
    path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
    parser = PostTelemacSelafinParser()
    parser.loadHydrauFile(path)
    bd = parser.getBoundary()
    
    rubberbandelem = qgis.gui.QgsRubberBand(iface.mapCanvas(), qgis.core.QGis.Polygon)
    rubberbandelem.addGeometry(bd, None)
    #print str(bd.asPolygon())
    
    print('ok')

#testimport()
testParser()

#testctpe()

#testboundary()