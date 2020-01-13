import qgis.core
import qgis.utils

#import PyQT
from qgis.PyQt import QtCore
#import posttelemac
from .post_telemac_pluginlayer import SelafinPluginLayer

class SelafinPluginLayerType(qgis.core.QgsPluginLayerType):

    def __init__(self):
        qgis.core.QgsPluginLayerType.__init__(self, SelafinPluginLayer.LAYER_TYPE)
        self.iface = qgis.utils.iface

    def createLayer(self):
        return SelafinPluginLayer()
        
    def showLayerProperties(self, layer):
        self.iface.addDockWidget( QtCore.Qt.RightDockWidgetArea, layer.propertiesdialog )
        self.iface.mapCanvas().setRenderFlag(True)
        return True

    def addToRegistry(self):
        #Add telemac_viewer in QgsPluginLayerRegistry
        if u'selafin_viewer' in QgsPluginLayerRegistry.instance().pluginLayerTypes():
            QgsPluginLayerRegistry.instance().removePluginLayerType('selafin_viewer')
        self.pluginLayerType = self()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.pluginLayerType)
 