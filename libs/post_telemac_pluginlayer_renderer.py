# -*- coding: utf-8 -*-

import qgis.core
from PyQt4 import QtGui

class PostTelemacPluginLayerRenderer(qgis.core.QgsMapLayerRenderer):

    def __init__(self, layer, rendererContext):

        qgis.core.QgsMapLayerRenderer.__init__(self, layer.id())
        self.layer = layer
        self.rendererContext = rendererContext



    def render(self):

        if self.layer.hydrauparser !=None and self.layer.hydrauparser.hydraufile !=None :
            bool1,image1,image2 = self.layer.selafinqimage.getimage(self.layer,self.rendererContext)
        else:
            image1 = QtGui.QImage()
            image2 = None
            bool1=True
        
        painter = self.rendererContext.painter()
        painter.save()
        painter.drawImage(0,0,image1)
        if image2:
            painter.drawImage(0,0,image2)
        painter.restore()
        return bool1
        