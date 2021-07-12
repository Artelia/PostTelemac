# -*- coding: utf-8 -*-

# unicode behaviour
from __future__ import unicode_literals

from qgis.core import QgsMapLayerRenderer

from qgis.PyQt.QtGui import QImage


class PostTelemacPluginLayerRenderer(QgsMapLayerRenderer):
    def __init__(self, meshlayer, rendererContext):
        QgsMapLayerRenderer.__init__(self, meshlayer.id())
        self.meshlayer = meshlayer
        self.rendererContext = rendererContext

    def render(self):
        try:
            if (
                self.meshlayer.hydrauparser != None
                and self.meshlayer.hydrauparser.path != None
                and self.meshlayer.meshrenderer != None
            ):
                bool1, image1, image2 = self.meshlayer.meshrenderer.getimage(self.meshlayer, self.rendererContext)
            else:
                image1 = QImage()
                image2 = None
                bool1 = True
            painter = self.rendererContext.painter()
            painter.save()
            painter.drawImage(0, 0, image1)
            if image2:
                painter.drawImage(0, 0, image2)
            painter.restore()
            return bool1

        except Exception as e:
            self.meshlayer.propertiesdialog.errorMessage("Renderer Error : " + str(e))
            return False

    def onTimeout(self):
        pass
