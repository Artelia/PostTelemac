#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
#import posttelemac
from post_telemac_pluginlayer import SelafinPluginLayer




class SelafinPluginLayerType(QgsPluginLayerType):

    def __init__(self):
        QgsPluginLayerType.__init__(self, SelafinPluginLayer.LAYER_TYPE)
        self.iface = iface

    def createLayer(self):
        return SelafinPluginLayer()
        
    def showLayerProperties(self, layer):
        self.iface.addDockWidget( Qt.RightDockWidgetArea, layer.propertiesdialog )
        self.iface.mapCanvas().setRenderFlag(True)
        return True

    def addToRegistry(self):
        #Add telemac_viewer in QgsPluginLayerRegistry
        if u'selafin_viewer' in QgsPluginLayerRegistry.instance().pluginLayerTypes():
            QgsPluginLayerRegistry.instance().removePluginLayerType('selafin_viewer')
        self.pluginLayerType = self()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.pluginLayerType)
 