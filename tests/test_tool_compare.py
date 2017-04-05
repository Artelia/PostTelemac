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

from  PostTelemac.meshlayer.post_telemac_pluginlayer import SelafinPluginLayer
from PostTelemac.meshlayertools.meshlayer_compare_tool import CompareTool



def testCompareTool():
    
    print('begin')
    #path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
    path1 = os.path.normpath('C://00_Bureau//00_QGIs//testcompare//SMEAG_R1_ARA_Q100_MAX.res')
    path2 = os.path.normpath('C://00_Bureau//00_QGIs//testcompare//SMEAG_REF_Q5_MAX.res')
    slf = SelafinPluginLayer()
    print('slf created')
    slf.load_selafin(path1,'TELEMAC')
    print('slf loaded')
    
    slf.propertiesdialog.debugtoprint = True
    
    comparetool = CompareTool(slf,slf.propertiesdialog)
    
    comparetool.initCompare(path2)
    comparetool.checkBox_6.setCheckState(2)
    
    comparetool.compare1(0)
    
    
    
    print('done')
    
    
testCompareTool()
    
            
        

    
    
    
