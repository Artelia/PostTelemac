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
"""

from qgis.core import QgsPluginLayerType
from qgis.utils import iface

# import PyQT
from qgis.PyQt.QtCore import Qt

# import posttelemac
from .post_telemac_pluginlayer import SelafinPluginLayer


class SelafinPluginLayerType(QgsPluginLayerType):
    def __init__(self):
        QgsPluginLayerType.__init__(self, SelafinPluginLayer.LAYER_TYPE)
        self.iface = iface

    def createLayer(self):
        return SelafinPluginLayer()

    def showLayerProperties(self, layer):
        self.iface.addDockWidget(Qt.RightDockWidgetArea, layer.propertiesdialog)
        self.iface.mapCanvas().setRenderFlag(True)
        return True

    def setTransformContext(self, transformContext):
        pass
