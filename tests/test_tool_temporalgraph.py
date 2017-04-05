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
import qgis

from  PostTelemac.meshlayer.post_telemac_pluginlayer import SelafinPluginLayer
from PostTelemac.meshlayertools.meshlayer_temporalgraph_tool import TemporalGraphTool
from  qgis.PyQt import QtCore, QtGui, uic
try:        #qt4
    from qgis.PyQt.QtGui import QDialog, QVBoxLayout
except:     #qt5
    from qgis.PyQt.QtWidgets import  QDialog, QVBoxLayout


def testToshapeTool():
    
    print('begin')
    path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100.res')
#    path = os.path.normpath('C://00_Bureau//data2//SMEAG_REF_Q100_MAX.res')
    slf = SelafinPluginLayer()
    print('slf created')
    slf.load_selafin(path,'TELEMAC')
    print('slf loaded')
    
    slf.propertiesdialog.debugtoprint = True
    
    temporaltool = TemporalGraphTool(slf,slf.propertiesdialog)
    
    dlg = qgis.gui.QgsDialog()
    temporaltool.setParent(dlg)
#    dlg.layout = QVBoxLayout()
    dlg.layout().addWidget(temporaltool)

    temporaltool.setVisible(True)
    temporaltool.computeGraphTemp(qgis.core.QgsPoint(444653.6,6389525.0))
    dlg.exec_()

    print('done')
    
    
testToshapeTool()
    
            
        

    
    
    
