# -*- coding: utf-8 -*-

#unicode behaviour
from __future__ import unicode_literals

import qgis.core
from PyQt4 import QtGui, QtCore

class PostTelemacPluginLayerRenderer(qgis.core.QgsMapLayerRenderer):

    def __init__(self, meshlayer, rendererContext):
        qgis.core.QgsMapLayerRenderer.__init__(self, meshlayer.id())
        self.meshlayer = meshlayer
        self.rendererContext = rendererContext
        

    def render(self):
        try:
            if self.meshlayer.hydrauparser !=None and self.meshlayer.hydrauparser.hydraufile !=None and self.meshlayer.meshrenderer != None :
                bool1,image1,image2 = self.meshlayer.meshrenderer.getimage(self.meshlayer,self.rendererContext)
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
        except Exception, e:
            #self.meshlayer.propertiesdialog.errorMessage('Rendering : ' + str(e))
            self.meshlayer.propertiesdialog.errorMessage('Renderer Error')
            return False
        