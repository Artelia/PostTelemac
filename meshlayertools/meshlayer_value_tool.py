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


from PyQt4 import uic, QtCore, QtGui
from meshlayer_abstract_tool import *
import qgis

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ValueTool.ui'))



class ValueTool(AbstractMeshLayerTool,FORM_CLASS):


    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        #self.setupUi(self)
        
    def initTool(self):
        self.setupUi(self)
        self.clickTool = qgis.gui.QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        self.rubberband = None
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Information_48x48.png' )
        #self.qtreewidgetitem.setIcon(0,QtGui.QIcon(os.path.join(os.path.dirname(__file__),'..','icons','tools','Information_48x48.png' )))
        

        
    def onActivation(self):
        if self.meshlayer.hydrauparser != None:
            self.propertiesdialog.canvas.setMapTool(self.clickTool)
            try:
                self.clickTool.canvasClicked.disconnect()
            except Exception: 
                pass
            self.clickTool.canvasClicked.connect(self.valeurs_click)
            self.valeurs_click(qgis.core.QgsPoint(0.0,0.0))

    def onDesactivation(self):
        try:
            self.clickTool.canvasClicked.disconnect()
        except Exception: 
            pass
        if self.rubberband != None:
            self.rubberband.reset(qgis.core.QGis.Point)
        
    def valeurs_click(self,qgspointfromcanvas):
        """
        Called in PostTelemacPropertiesDialog by value tool
        fill the tablewidget
        """
        #qgspointtransformed = self.selafinlayer.xform.transform(qgspoint,QgsCoordinateTransform.ReverseTransform)
        if self.comboBox_values_method.currentIndex() == 0 :
            qgspoint= self.meshlayer.xform.transform(qgis.core.QgsPoint(qgspointfromcanvas[0],qgspointfromcanvas[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
            point1 = [[qgspoint.x(),qgspoint.y()]]
            numnearest = self.meshlayer.hydrauparser.getNearestPoint(point1[0][0], point1[0][1])
            x,y = self.meshlayer.hydrauparser.getXYFromNumPoint([numnearest])[0]
            qgspointfromcanvas = self.meshlayer.xform.transform( qgis.core.QgsPoint(x,y) )

        if not self.rubberband:
            self.createRubberband()
        self.rubberband.reset(qgis.core.QGis.Point)
        bool1, values = self.meshlayer.identify(qgspointfromcanvas)
        strident = ''
        i = 0
        for name, value in values.items():
            self.tableWidget_values.setItem(i, 1, QtGui.QTableWidgetItem(str(round(value,3))))
            i += 1
        self.rubberband.addPoint(qgspointfromcanvas)
        
        
    def createRubberband(self):
        self.rubberband = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QGis.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
        
    def updateParams(self):
        self.tableWidget_values.clearContents()
        self.tableWidget_values.setRowCount(len(self.meshlayer.hydrauparser.parametres))
        for i, param in enumerate(self.meshlayer.hydrauparser.parametres):
            self.tableWidget_values.setItem(i, 0, QtGui.QTableWidgetItem(param[1]))
        self.tableWidget_values.setFixedHeight((self.tableWidget_values.rowHeight(0) - 1)*(len(self.meshlayer.hydrauparser.parametres) + 1) + 1)
        
        
        