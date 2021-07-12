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

from qgis.PyQt.QtCore import QObject, Qt
from qgis.PyQt.QtGui import QColor

from qgis.core import QgsGeometry, QgsWkbTypes, QgsPointXY
from qgis.gui import QgsRubberBand

import numpy as np


class MeshLayerRubberband(QObject):
    def __init__(self, meshlayer):
        QObject.__init__(self)
        self.meshlayer = meshlayer

        self.rubberbandelem = None
        self.rubberbandfacenode = None
        self.rubberbandface = None

        self.pointcolor = QColor(Qt.red)
        self.elemcolor = QColor(Qt.blue)
        self.facecolor = QColor(Qt.darkGreen)

    def drawFromNum(self, num, type):
        if type == 0:
            geomtemp = self.meshlayer.hydrauparser.getElemXYFromNumElem(num)[0]
            elemqgisgeom = QgsGeometry.fromPolygon(
                [[self.meshlayer.xform.transform(QgsPointXY(coord[0], coord[1])) for coord in geomtemp]]
            )
            if not self.rubberbandelem:
                self.createRubberbandElem()
            self.rubberbandelem.reset(QgsWkbTypes.PolygonGeometry)
            self.rubberbandelem.addGeometry(elemqgisgeom, None)

        if type == 1:
            x, y = self.meshlayer.hydrauparser.getFaceNodeXYFromNumPoint(num)[0]
            qgspointfromcanvas = self.meshlayer.xform.transform(QgsPointXY(x, y))
            if not self.rubberbandfacenode:
                self.createRubberbandFaceNode()
            self.rubberbandfacenode.reset(QgsWkbTypes.PointGeometry)
            self.rubberbandfacenode.addPoint(qgspointfromcanvas)

        if type == 2:
            geomtemp = self.meshlayer.hydrauparser.getFaceXYFromNumFace(num)[0]
            faceqgisgeom = QgsGeometry.fromPolyline(
                [self.meshlayer.xform.transform(QgsPointXY(coord[0], coord[1])) for coord in geomtemp]
            )
            if not self.rubberbandface:
                self.createRubberbandFace()
            self.rubberbandface.reset(QgsWkbTypes.LineGeometry)
            self.rubberbandface.addGeometry(faceqgisgeom, None)

    def reset(self):
        if self.rubberbandelem != None:
            self.rubberbandelem.reset(QgsWkbTypes.PolygonGeometry)
        if self.rubberbandfacenode != None:
            self.rubberbandfacenode.reset(QgsWkbTypes.PointGeometry)
        if self.rubberbandface != None:
            self.rubberbandface.reset(QgsWkbTypes.LineGeometry)

    def createRubberbandFaceNode(self):
        self.rubberbandfacenode = QgsRubberBand(self.meshlayer.canvas, QgsWkbTypes.PointGeometry)
        self.rubberbandfacenode.setWidth(2)
        self.rubberbandfacenode.setColor(self.pointcolor)

    def createRubberbandElem(self):
        self.rubberbandelem = QgsRubberBand(self.meshlayer.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberbandelem.setWidth(2)
        color = QColor(self.elemcolor)
        color.setAlpha(100)
        self.rubberbandelem.setColor(color)

    def createRubberbandFace(self):
        self.rubberbandface = QgsRubberBand(self.meshlayer.canvas, QgsWkbTypes.LineGeometry)
        self.rubberbandface.setWidth(5)
        self.rubberbandface.setColor(self.facecolor)
