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


#from PyQt4 import uic, QtCore, QtGui
from qgis.PyQt import uic, QtCore, QtGui
from .meshlayer_abstract_tool import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ProfileTool.ui'))



class ProfileTool(AbstractMeshLayerTool,FORM_CLASS):

    NAME = 'PROFILETOOL'


    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Line_Graph_48x48_spatial.png' )
        

        
    def onActivation(self):
        pass

    def onDesactivation(self):
        pass
