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
#from PyQt4 import uic, QtCore, QtGui

from  PostTelemac.meshlayer.post_telemac_pluginlayer import SelafinPluginLayer
from PostTelemac.meshlayertools.meshlayer_flow_tool import  FlowTool, computeFlow

def output(str1):
    print(str1)
    
def finishedd(lst1,lst2,lst3):
    print('finished ********************')
    print(lst1)


def testFlowTool1():
    
    geomfinal = [[[437043.44736648886, 6392286.143149674], [438331.2797807046, 6392515.9717035955], [438331.2797807046, 6392515.9717035955]]]
    #geomfinal = [[[437043.44736648886, 6392286.143149674], [438331.2797807046, 6392515.9717035955]]]

    geom = qgis.core.QgsGeometry.fromPolyline([ qgis.core.QgsPoint(i[0],i[1])  for i in geomfinal[0] ])
    
    print(geom.asPolyline())
    
    temp = qgis.core.QgsGeometry.fromMultiPolyline([[ qgis.core.QgsPoint(i[0],i[1])  for i in geom.asPolyline() ]])
    
    print(geom.asPolyline())
    print(type(geom.asPolyline()))
    

    

    
    
    if False:
        
        print('begin')
        path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
        slf = SelafinPluginLayer()
        print('slf created')
        slf.load_selafin(path,'TELEMAC')
        print('slf loaded')
        
        
        #flowcompute = InitComputeFlow(slf,slf.propertiesdialog)
        flowcompute = computeFlow(slf, 0, geomfinal)
        flowcompute.status.connect(output)
        flowcompute.finished.connect(finishedd)
        flowcompute.error.connect(output)
        
        flowcompute.computeFlowMain()
    
    print('done')
    

    
    
testFlowTool1()
    
            
        

    
    
    
