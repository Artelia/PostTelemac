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


#Qt
from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QVBoxLayout
except:
    from qgis.PyQt.QtWidgets import QVBoxLayout
    
try:
    import shapely
except:
    pass
import math
import qgis
import numpy as np


import matplotlib, sys


#local import
from .meshlayer_abstract_tool import *

from ..meshlayerlibs import pyqtgraph as pg
pg.setConfigOption('background', 'w')

try:
    from ..meshlayerparsers.libs_telemac.samplers.meshes import *
except:
    pass

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'FlowTool.ui'))



class FlowTool(AbstractMeshLayerTool,FORM_CLASS):

    NAME = 'FLOWTOOL'
    SOFTWARE = ['TELEMAC','ANUGA']

    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        
#*********************************************************************************************
#***************Imlemented functions  **********************************************************
#********************************************************************************************
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Line_Graph_48x48.png' )
        
        #self.clickTool = qgis.gui.QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        #self.rubberband = None
        self.graphtempactive = False
        self.graphtempdatac = []
        self.vectorlayerflowids = None
        self.maptool = None
        self.pointstoDraw = []
        
        
        #self.rubberbandpoint = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QGis.Point)
        #self.rubberbandpoint.setWidth(2)
        #self.rubberbandpoint.setColor(QtGui.QColor(QtCore.Qt.red))
        self.meshlayer.rubberband.createRubberbandFace()
        self.meshlayer.rubberband.createRubberbandFaceNode()
        
        #Tools tab - temporal graph
        self.pyqtgraphwdg = pg.PlotWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.pyqtgraphwdg)
        self.vb = self.pyqtgraphwdg.getViewBox()
        self.frame.setLayout(layout)
        #Signals connection
        self.comboBox_3.currentIndexChanged.connect(self.activateMapTool)
        self.pushButton_4.clicked.connect(self.copygraphclipboard)
        self.pushButton_flow.clicked.connect(self.computeFlow)
        
        self.propertiesdialog.meshlayerschangedsignal.connect(self.layerChanged)
        self.plotitem = []
        
        self.timeline = pg.InfiniteLine(0, pen=pg.mkPen('b',  width=2) )
        self.pyqtgraphwdg.addItem(self.timeline)
        
        self.datavline = pg.InfiniteLine(0, angle=90 ,pen=pg.mkPen('r',  width=1)  )
        self.datahline = pg.InfiniteLine(0, angle=0 , pen=pg.mkPen('r',  width=1) )
        
        self.appendCursor()
        
        

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""            
        self.activateMapTool()
        
        self.timeChanged(self.meshlayer.time_displayed)
        self.meshlayer.timechanged.connect(self.timeChanged)
        
    def onDesactivation(self):
        if False and self.rubberband:
            self.rubberband.reset(qgis.core.QGis.Point)
        self.meshlayer.rubberband.reset()
        try:
            self.meshlayer.timechanged.connect(self.timeChanged)
        except:
            pass
            
#*********************************************************************************************
#***************Behaviour functions  **********************************************************
#********************************************************************************************


    def appendCursor(self):

        self.pyqtgraphwdg.addItem(self.datavline)
        self.pyqtgraphwdg.addItem(self.datahline)
        
    def removeCursor(self):
        self.pyqtgraphwdg.removeItem(self.datavline)
        self.pyqtgraphwdg.removeItem(self.datahline)


    def layerChanged(self):
        #enable  flow if depth, veolocuty are present in parser params 
        if self.meshlayer.hydrauparser.parametreh != None and self.meshlayer.hydrauparser.parametrevx != None and self.meshlayer.hydrauparser.parametrevy != None:
            self.setEnabled(True)
        else:
            self.setEnabled(False)
            
            
    
    def activateMapTool(self):
        if self.comboBox_3.currentIndex() == 0:
            self.pushButton_flow.setEnabled(False)
            self.computeFlow()
        else:
            self.pushButton_flow.setEnabled(True)
            try:
                self.deactivateTool()
            except Exception as e:
                pass

    """
    def createRubberband(self):
        self.rubberband = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QGis.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
            
    def resetRubberband(self):
        if self.rubberband:
            self.rubberband.reset(qgis.core.QGis.Point)
    """
            
#*********************************************************************************************
#***************Main functions  **********************************************************
#********************************************************************************************
        
        

    def computeFlow(self):
        """
        Activated with flow graph tool
        """
        
        
        
        """
        if not self.rubberband:
            self.createRubberband()
        """
        self.dblclktemp = None
        self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
        self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"
        self.vectorlayerflowids = None
        self.graphtodo = 1
        self.selectionmethod = self.comboBox_3.currentIndex()
        
        if self.selectionmethod in [0]:
            # print('sel0')
            # layer = qgis.utils.iface.activeLayer()
            if not self.maptool:
                self.maptool = FlowMapTool(self.meshlayer.canvas,self.pushButton_flow)
            #Listeners of mouse
            self.connectTool()
            #init the mouse listener comportement and save the classic to restore it on quit
            self.meshlayer.canvas.setMapTool(self.maptool)
            #init the temp layer where the polyline is draw
            #self.rubberband.reset(qgis.core.QGis.Line)
            self.meshlayer.rubberband.reset()
            #init the table where is saved the poyline
            self.pointstoDraw = []
            self.pointstoCal = []
            self.lastClicked = [[-9999999999.9,9999999999.9]]
            # The last valid line we drew to create a free-hand profile
            self.lastFreeHandPoints = []
        elif self.selectionmethod in [1,2]:
            layer = qgis.utils.iface.activeLayer()
            if not (layer.type() == 0 and layer.geometryType()==1):
                QMessageBox.warning(qgis.utils.iface.mainWindow(), "PostTelemac", self.tr("Select a (poly)line vector layer"))
            elif self.selectionmethod==1 and len(layer.selectedFeatures())==0:
                QMessageBox.warning(qgis.utils.iface.mainWindow(), "PostTelemac", self.tr("Select a line in a (poly)line vector layer"))
            else:
                #self.ax.cla()
                #grid2 = self.ax.grid(color='0.5', linestyle='-', linewidth=0.5)
                #self.canvas1.draw()
                self.initclass1=[]
                self.checkBox.setChecked(True)
                iter = layer.selectedFeatures()
                if self.selectionmethod == 2 or len(iter)==0:
                    iter = layer.getFeatures()
                geomfinal=[]
                self.vectorlayerflowids = []
                if sys.version_info.major == 2:
                    xformutil = qgis.core.QgsCoordinateTransform(self.meshlayer.realCRS, layer.crs() )
                elif sys.version_info.major == 3:
                    xformutil = qgis.core.QgsCoordinateTransform(self.meshlayer.realCRS, layer.crs(), qgis.core.QgsProject.instance() )
                for i,feature in enumerate(iter):
                    try:
                        self.vectorlayerflowids.append(str(feature[0]))
                    except:
                        self.vectorlayerflowids.append(str(feature.id()))
                    geoms=feature.geometry().asPolyline()
                    geoms=[[geom[0],geom[1]] for geom in geoms]
                    geoms = geoms+[geoms[-1]]
                    geomstemp=[]
                    for geom in geoms:
                        if sys.version_info.major == 2:
                            qgspoint = xformutil.transform(qgis.core.QgsPoint(geom[0],geom[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
                        elif sys.version_info.major == 3:
                            qgspoint = xformutil.transform(qgis.core.QgsPointXY(geom[0], geom[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
                        geomstemp.append([qgspoint.x(),qgspoint.y()])
                    geomfinal.append(geomstemp)
                    
                self.launchThread(geomfinal)
                
            

    def launchThread(self,geom):
        if True:
            self.initclass=InitComputeFlow()


            self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
            self.initclass.error.connect(self.propertiesdialog.errorMessage)
            self.initclass.emitpoint.connect(self.addPointRubberband)
            self.initclass.emitprogressbar.connect(self.updateProgressBar)
            self.initclass.finished1.connect(self.workerFinished)

            #self.rubberbandpoint.reset(qgis.core.QGis.Point)

            self.meshlayer.rubberband.reset()
            """
            if self.comboBox_flowmethod.currentIndex()==0:
                self.rubberband.reset(qgis.core.QGis.Line)
            elif self.comboBox_flowmethod.currentIndex()==1:
                self.rubberband.reset(qgis.core.QGis.Point)
            """
            #self.selafinlayer.propertiesdialog.textBrowser_main.append(str(ctime() + ' - Computing flow'))
            self.propertiesdialog.normalMessage('Start computing flow')
            #self.initclass.start(self.meshlayer,self,geom)
            self.initclass.start(self.meshlayer,self.comboBox_flowmethod.currentIndex(),geom)

            self.pushButton_flow.setEnabled(False)
        else:
            self.comptute = computeFlow(self.meshlayer,self.comboBox_flowmethod.currentIndex(),geom)
            self.comptute.status.connect(print)
            self.comptute.error.connect(print)
            self.comptute.computeFlowMain()

        
    def workerFinished(self,list1,list2,list3 = None):
        print('workerFinished', list1, list2)
        #ax = self.ax
        if not self.checkBox.isChecked():
            if len(self.plotitem)>0:
                for plot in self.plotitem:
                    self.pyqtgraphwdg.removeItem(plot[0])
            self.plotitem = []

        maxtemp=None
        mintemp = None
        self.pyqtgraphwdg.showGrid(True,True,0.5)

        for i in range(len(list1)):

            self.plotitem.append([self.pyqtgraphwdg.plot(list1[i], list2[i], pen=pg.mkPen('b',  width=2) ),list1[i], list2[i] ] )
            if not maxtemp:
                maxtemp = max(np.array(list2[i]))
            else:
                if max(np.array(list2[i]))>maxtemp:
                    maxtemp = max(np.array(list2[i]))
            if not mintemp:
                mintemp = min(np.array(list2[i]))
            else:
                if min(np.array(list2[i]))<mintemp:
                    mintemp = min(np.array(list2[i]))

        if maxtemp is not None and mintemp is not None:
            self.label_flow_resultmax.setText('Max : ' + str(round(maxtemp,3)))
            self.label__flow_resultmin.setText('Min : ' + str(round(mintemp,3)))
        
        self.propertiesdialog.normalMessage('Computing volume finished')
        if self.comboBox_3.currentIndex() != 0:
            self.pushButton_flow.setEnabled(True)

                
        self.propertiesdialog.progressBar.reset()
        
        self.pyqtgraphwdg.scene().sigMouseMoved.connect(self.mouseMoved)
            
    
    
    def mouseMoved(self, pos): # si connexion directe du signal "mouseMoved" : la fonction reçoit le point courant

            if self.pyqtgraphwdg.sceneBoundingRect().contains(pos): # si le point est dans la zone courante
                    mousePoint = self.vb.mapSceneToView(pos) # récupère le point souris à partir ViewBox

                    datax = self.plotitem[-1][1]
                    datay = self.plotitem[-1][2]
                    nearestindex = np.argmin( abs(np.array(datax)-mousePoint.x()) )
                    x = datax[nearestindex]
                    y = datay[nearestindex]
                    if True:
                        self.datavline.setPos(x)
                        self.datahline.setPos(y)
                    if True:
                        self.label_X.setText(str(round(x,3)))
                        self.label_Y.setText(str(round(y,3)))
                    
                    
    def timeChanged(self,nb):
            
        self.timeline.setPos(self.meshlayer.hydrauparser.getTimes()[nb])
    
    def copygraphclipboard(self):

        #ax = self.ax
        
        self.clipboard = QApplication.clipboard()
        strtemp=''
        datatemp=[]
        max=0
        
        for plotitem in self.plotitem:
            datax = plotitem[1]
            datay = plotitem[2]
            data = np.array([[datax[i],datay[i]] for i in range(len(datax))   ] )
            
            if len(data)>0:
                datatemp.append(data)
                maxtemp = len(data)
                if maxtemp>max:
                    max = maxtemp
                    
        if self.vectorlayerflowids:
            for flowid in self.vectorlayerflowids:
                strtemp = strtemp + 'id : '+str(flowid)+ "\t"+ "\t"
                
        for i in range(maxtemp):
            for j in range(len(datatemp)):
                strtemp += str(datatemp[j][i][0])+ "\t" +str(datatemp[j][i][1])+"\t"
            strtemp += "\n"
                

        self.clipboard.setText(strtemp)
    
    
    
    def addPointRubberband(self,x,y):

        if isinstance(x,list):
            points = []
            if len(x)>1:
                for i in range(len(x)):
                    if sys.version_info.major == 2:
                        points.append(self.meshlayer.xform.transform(qgis.core.QgsPoint(x[i],y[i])))
                    elif sys.version_info.major == 3:
                        points.append(self.meshlayer.xform.transform(qgis.core.QgsPointXY(x[i], y[i])))
                #self.rubberband.addGeometry(qgis.core.QgsGeometry.fromPolygon([points]), None)
                if sys.version_info.major == 2:
                    self.meshlayer.rubberband.rubberbandface.addGeometry(qgis.core.QgsGeometry.fromPolygon([points]), None)
                elif sys.version_info.major == 3:
                    self.meshlayer.rubberband.rubberbandface.addGeometry(qgis.core.QgsGeometry.fromPolygonXY([points]), None)
            else:
                if sys.version_info.major == 2:
                    qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPoint(x[0],y[0]))
                elif sys.version_info.major == 3:
                    qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPointXY(x[0], y[0]))
                #self.rubberband.addPoint(qgspoint)
                #self.rubberbandpoint.addPoint(qgspoint)
                #self.rubberband.addGeometry(qgis.core.QgsGeometry.fromPolygon([[qgspoint]]), None)
                self.meshlayer.rubberband.rubberbandface.addPoint(qgspoint)
                self.meshlayer.rubberband.rubberbandfacenode.addPoint(qgspoint)
        else:
            if sys.version_info.major == 2:
                qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPoint(x,y))
            elif sys.version_info.major == 3:
                qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPointXY(x, y))
            #self.rubberband.addPoint(qgspoint)
            self.meshlayer.rubberband.rubberbandface.addPoint(qgspoint)
            
    def updateProgressBar(self,float1):
        self.propertiesdialog.progressBar.setValue(int(float1))
        
        
#*********************************************************************************************
#*************** Map Tool  **********************************************************
#********************************************************************************************
        
    def connectTool(self):

        self.maptool.moved.connect(self.moved)
        self.maptool.rightClicked.connect(self.rightClicked)
        self.maptool.leftClicked.connect(self.leftClicked)
        self.maptool.doubleClicked.connect(self.doubleClicked)
        self.maptool.desactivate.connect(self.deactivateTool)

    def deactivateTool(self):		#enable clean exit of the plugin

        self.maptool.moved.disconnect(self.moved)
        self.maptool.rightClicked.disconnect(self.rightClicked)
        self.maptool.leftClicked.disconnect(self.leftClicked)
        self.maptool.doubleClicked.disconnect(self.doubleClicked)
        self.maptool.desactivate.disconnect(self.deactivateTool)
        
        

    def moved(self,position):			#draw the polyline on the temp layer (rubberband)
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                #Get mouse coords
                mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
                #Draw on temp layer

                self.meshlayer.rubberband.reset()
                for i in range(0,len(self.pointstoDraw)):

                    if sys.version_info.major == 2:
                        self.meshlayer.rubberband.rubberbandface.addPoint(qgis.core.QgsPoint(self.pointstoDraw[i][0],self.pointstoDraw[i][1]))
                    elif sys.version_info.major == 3:
                        self.meshlayer.rubberband.rubberbandface.addPoint(qgis.core.QgsPointXY(self.pointstoDraw[i][0], self.pointstoDraw[i][1]))

                if sys.version_info.major == 2:
                    self.meshlayer.rubberband.rubberbandface.addPoint(qgis.core.QgsPoint(mapPos.x(), mapPos.y()))
                elif sys.version_info.major == 3:
                    self.meshlayer.rubberband.rubberbandface.addPoint(qgis.core.QgsPointXY(mapPos.x(),mapPos.y()))
        """
        if self.selectionmethod == 1:
            return
        """

    def rightClicked(self,position):	#used to quit the current action
        if self.selectionmethod == 0:
            mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            #if newPoints == self.lastClicked: return # sometimes a strange "double click" is given
            if len(self.pointstoDraw) > 0:
                self.pointstoDraw = []
                self.pointstoCal = []
                #self.rubberband.reset(qgis.core.QGis.Line)
                self.meshlayer.rubberband.reset()
            else:
                self.cleaning()
        """
        if self.selectionmethod == 1:
            try:
                self.previousLayer.removeSelection( False )
            except:
                self.iface.mainWindow().statusBar().showMessage("error right click")
            self.cleaning()
        """

    def leftClicked(self,position):		#Add point to analyse
        mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
        newPoints = [[mapPos.x(), mapPos.y()]]

        if self.selectionmethod == 0:
            if newPoints == self.dblclktemp:
                self.dblclktemp = None
                if self.comboBox_3.currentIndex() != 0:
                    self.cleaning()
                #return
            else :
                if len(self.pointstoDraw) == 0:
                    #self.rubberband.reset(qgis.core.QGis.Line)
                    self.meshlayer.rubberband.reset()
                    #self.rubberbandpoint.reset(qgis.core.QGis.Point)
                self.pointstoDraw += newPoints
        """
        if self.selectionmethod == 1:
            print 'ok'
            result = SelectLineTool().getPointTableFromSelectedLine(iface, self.tool, newPoints, self.layerindex, self.previousLayer , self.pointstoDraw)
            self.pointstoDraw = result[0]
            self.layerindex = result[1]
            self.previousLayer = result[2]
            self.launchThread([self.pointstoDraw])
            self.pointstoDraw = []
        """


    def doubleClicked(self,position):
        if self.selectionmethod == 0:
            #Validation of line
            mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            self.pointstoDraw += newPoints
            #convert points to pluginlayer crs
            xform = self.meshlayer.xform
            pointstoDrawfinal=[]
            for point in self.pointstoDraw:
                if sys.version_info.major == 2:
                    qgspoint = xform.transform(qgis.core.QgsPoint(point[0],point[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
                elif sys.version_info.major == 3:
                    qgspoint = xform.transform(qgis.core.QgsPointXY(point[0],point[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
                pointstoDrawfinal.append([qgspoint.x(),qgspoint.y()])
            #launch analyses
            self.launchThread([pointstoDrawfinal])
            #Reset
            self.lastFreeHandPoints = self.pointstoDraw
            self.pointstoDraw = []
            #temp point to distinct leftclick and dbleclick
            self.dblclktemp = newPoints
            #iface.mainWindow().statusBar().showMessage(self.textquit0)
        """
        if self.selectionmethod == 1:
            return
        """
        
        
    def cleaning(self):     #used on right click
        self.meshlayer.canvas.setMapTool(self.propertiesdialog.maptooloriginal)
        qgis.utils.iface.mainWindow().statusBar().showMessage( "" )
        
        
class FlowMapTool(qgis.gui.QgsMapTool):

    def __init__(self, canvas,button):
        qgis.gui.QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QtGui.QCursor(QtCore.Qt.CrossCursor)
        self.button = button

    def canvasMoveEvent(self,event):
        #self.emit( QtCore.SIGNAL("moved"), {'x': event.pos().x(), 'y': event.pos().y()} )
        self.moved.emit( {'x': event.pos().x(), 'y': event.pos().y()} )

    def canvasReleaseEvent(self,event):
        if event.button() == QtCore.Qt.RightButton:
            #self.emit( QtCore.SIGNAL("rightClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )
            self.rightClicked.emit( {'x': event.pos().x(), 'y': event.pos().y()} )
        else:
            #self.emit( QtCore.SIGNAL("leftClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )
            self.leftClicked.emit( {'x': event.pos().x(), 'y': event.pos().y()} )

    def canvasDoubleClickEvent(self,event):
        #self.emit( QtCore.SIGNAL("doubleClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )
        self.doubleClicked.emit( {'x': event.pos().x(), 'y': event.pos().y()} )

    def activate(self):
        qgis.gui.QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)
        #print  'activate'
        #self.button.setEnabled(False)
        #self.button.setCheckable(True)
        #self.button.setChecked(True)



    def deactivate(self):
        #self.emit( QtCore.SIGNAL("deactivate") )
        self.desactivate.emit()
        #self.button.setCheckable(False)
        #self.button.setEnabled(True)
        #print  'deactivate'
        qgis.gui.QgsMapTool.deactivate(self)


    def setCursor(self,cursor):
        self.cursor = QtGui.QCursor(cursor)
        
    moved = QtCore.pyqtSignal(dict)
    rightClicked = QtCore.pyqtSignal(dict)
    leftClicked = QtCore.pyqtSignal(dict)
    doubleClicked = QtCore.pyqtSignal(dict)
    desactivate = QtCore.pyqtSignal()
        
        
#*********************************************************************************************
#*************** Thread **********************************************************
#********************************************************************************************



class computeFlow(QtCore.QObject):

    def __init__(self,                
                selafin,method,line):
        
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.polyline = line
        #self.fig = matplotlib.pyplot.figure(0)
        self.fig = matplotlib.pyplot.figure(self.selafinlayer.instancecount +4)
        #self.tool = tool
        self.method = method
        
        
    def computeFlowMain(self):
        """
        Main method
        
        """
        
        DEBUG = True
        
        list1 = []
        list2 = []
        list3 = []
        #METHOD = self.tool.comboBox_flowmethod.currentIndex()
        METHOD = self.method
        
        if DEBUG : self.status.emit('polyline raw '+str(self.polyline))
        
        try:
        #if True:
            for lineelement in self.polyline:
                temp3 = self.getLines(lineelement,METHOD)
                self.status.emit('temp3 : ' + str(temp3))
                result=[]
                parameterh = self.selafinlayer.hydrauparser.parametreh
                parameteruv = self.selafinlayer.hydrauparser.parametrevx
                parametervv = self.selafinlayer.hydrauparser.parametrevy 
                #self.slf = self.selafinlayer.slf
                
                if METHOD == 0 :
                    if self.selafinlayer.hydrauparser.networkxgraph == None:
                        self.selafinlayer.hydrauparser.createNetworkxGraph()
                    #G = self.selafinlayer.hydrauparser.networkxgraph
                    
                """
                if isinstance(temp3,shapely.geometry.linestring.LineString):
                    temp3 = [temp3]
                """

                    
                if METHOD == 0:         #Method0 : shortest path and vector computation
                
                    shortests = []       #list of shortests path
                    
                    for line in temp3:
                        #linetemp = np.array([[point[0],point[1]] for point in line.coords ])
                        linetemp = line
                        resulttemp=[]
                        self.status.emit('line : ' + str(linetemp))
                
                        #find shortests path
                        for points in range(len(linetemp)-1):
                            try:
                                #triangle = self.selafinlayer.hydrauparser.trifind.__call__(linetemp[points][0],linetemp[points][1])
                                triangle = self.selafinlayer.hydrauparser.triangulation.get_trifinder().__call__(linetemp[points][0],linetemp[points][1])
                                if triangle != -1:
                                    enumpointdebut = self.getNearestPointEdge(linetemp[points][0],linetemp[points][1],triangle)
                                #triangle = self.selafinlayer.hydrauparser.trifind.__call__(linetemp[points + 1][0],linetemp[points + 1][1])
                                triangle = self.selafinlayer.hydrauparser.triangulation.get_trifinder().__call__(linetemp[points + 1][0],linetemp[points + 1][1])
                                if triangle != -1:
                                    enumpointfin = self.getNearestPointEdge(linetemp[points + 1][0],linetemp[points + 1][1],triangle)

                                #shortest = nx.shortest_path(G, enumpointdebut, enumpointfin)
                                #self.status.emit('enumpointdebut : ' + str(enumpointdebut)+ ' ' + 'enumpointfin : ' + str(enumpointfin))
                                shortests.append( self.selafinlayer.hydrauparser.getShortestPath(enumpointdebut, enumpointfin) )
                                
                            except Exception as e :
                                self.status.emit('method 0 : ' + str(e))
                        
                    totalpointsonshortest = len(sum(shortests,[]))
                    compteur1 = 0
                    
                    self.status.emit('shortests : ' + str(shortests))
                    
                    for shortest in shortests:
                        #flow = None
                        if False:
                            results = np.array(self.selafinlayer.hydrauparser.getTimeSerie((np.array(shortest) +1).tolist(),[parameterh,parameteruv,parametervv],self.selafinlayer.hydrauparser.parametres) )
                        for i,elem in enumerate(shortest):
                            self.emitprogressbar.emit(float(compteur1 + i)/float(totalpointsonshortest-1)*100.0)
                            try:
                                if True:
                                    if i==0:    #init
                                        try:
                                            h2 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([elem ],[parameterh],self.selafinlayer.hydrauparser.parametres)[0][0])
                                        except Exception as e :
                                            self.status.emit('method 011 : ' + str(e))
                                        uv2 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([elem ],[parameteruv],self.selafinlayer.hydrauparser.parametres)[0][0])
                                        uv2 = np.array([[value,0.0] for value in uv2])
                                        vv2 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([elem ],[parametervv],self.selafinlayer.hydrauparser.parametres)[0][0])
                                        vv2 = np.array([[0.0,value] for value in vv2])
                                        v2vect = uv2 + vv2
                                        #xy2 = [self.slf.MESHX[elem],self.slf.MESHY[elem]]
                                        #xy2 = list( self.selafinlayer.hydrauparser.getXYFromNumPoint([elem])[0] )
                                        xy2 = list( self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0] )
                                    else:
                                        h1 = h2
                                        v1vect = v2vect
                                        xy1 = xy2
                                        h2 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([elem ],[parameterh],self.selafinlayer.hydrauparser.parametres)[0][0])
                                        uv2 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([elem ],[parameteruv],self.selafinlayer.hydrauparser.parametres)[0][0])
                                        uv2 = np.array([[value,0.0] for value in uv2])
                                        vv2 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([elem ],[parametervv],self.selafinlayer.hydrauparser.parametres)[0][0])
                                        vv2 = np.array([[0.0,value] for value in vv2])
                                        v2vect = uv2 + vv2
                                        #xy2 = [self.slf.MESHX[elem],self.slf.MESHY[elem]]
                                        #xy2 = list( self.selafinlayer.hydrauparser.getXYFromNumPoint([elem])[0] )
                                        xy2 = list( self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0] )
                                        if 'flow' in locals():
                                            flow = flow + self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                        else:
                                            flow = self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                else:
                                    try:
                                        if i==0:    #init
                                            h2 = results[0,i]
                                            uv2 = np.array([[value,0.0] for value in results[1,i]])
                                            vv2 = np.array([[0.0,value] for value in results[2,i]])
                                            v2vect = uv2 + vv2
                                            #xy2 = list( self.selafinlayer.hydrauparser.getXYFromNumPoint([elem])[0] )
                                            xy2 = list( self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0] )
                                        else:
                                            h1 = h2
                                            v1vect = v2vect
                                            xy1 = xy2
                                            h2 = results[0,i]
                                            uv2 = np.array([[value,0.0] for value in results[1,i]])
                                            vv2 = np.array([[0.0,value] for value in results[2,i]])
                                            v2vect = uv2 + vv2
                                            #xy2 = list( self.selafinlayer.hydrauparser.getXYFromNumPoint([elem])[0] )
                                            xy2 = list( self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0] )
                                            if 'flow' in locals():
                                                flow = flow + self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                            else:
                                                flow = self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                    except Exception as e :
                                        self.status.emit('method 011 : ' + str(e))
                                    
                                    
                                    
                                    
                            except Exception as e :
                                self.status.emit('method 01 : ' + str(e))
                            #x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([elem])[0]
                            x,y  =  self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0] 
                            self.emitpoint.emit(x,y)

                            #result.append([line,flow])
                        compteur1 += len(shortest)
                        result.append([None,flow])
                    

                if METHOD == 1 :
                    for line in temp3:
                        linetemp = np.array([[point[0],point[1]] for point in line.coords ])
                        resulttemp=[]
                
                        flow=None
                        temp_edges,temp_point,temp_bary = self.getCalcPointsSlice(line)
                        
                        for i in range(len(temp_point)):
                            if i ==0:
                                h2  = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameterh)
                                uv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameteruv)
                                uv2 = np.array([[value,0.0] for value in uv2])
                                vv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parametervv)
                                vv2 = np.array([[0.0,value] for value in vv2])
                                v2vect = uv2 + vv2
                                xy2 = temp_point[i]
                                self.emitpoint.emit(temp_point[i][0],temp_point[i][1])
                                """
                                self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][0]],self.selafinlayer.slf.MESHY[temp_edges[i][0]])
                                self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][1]],self.selafinlayer.slf.MESHY[temp_edges[i][1]])
                                """
                                #x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([temp_edges[i][0]])[0] 
                                x,y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][0]])[0] 
                                self.emitpoint.emit( x,y )
                                #x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([temp_edges[i][1]])[0]
                                x,y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][1]])[0] 
                                self.emitpoint.emit( x,y )
                                
                            else:
                                h1 = h2
                                v1vect = v2vect
                                xy1 = xy2
                                h2  = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameterh)
                                uv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameteruv)
                                uv2 = np.array([[value,0.0] for value in uv2])
                                vv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parametervv)
                                vv2 = np.array([[0.0,value] for value in vv2])
                                v2vect = uv2 + vv2
                                xy2 = temp_point[i]
                                #vectorface = np.array([xy2[0]-xy1[0],xy2[1]-xy1[1]])
                                lenght = np.linalg.norm(np.array([xy2[0]-xy1[0],xy2[1]-xy1[1]]))
                                if lenght > 0 : 
                                    if flow != None:
                                        flow = flow + self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                    else:
                                        flow = self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                    self.emitpoint.emit(temp_point[i][0],temp_point[i][1])
                                    """
                                    self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][0]],self.selafinlayer.slf.MESHY[temp_edges[i][0]])
                                    self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][1]],self.selafinlayer.slf.MESHY[temp_edges[i][1]])
                                    """
                                    #x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([temp_edges[i][0]])[0] 
                                    x,y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][0]])[0] 
                                    self.emitpoint.emit( x,y )
                                    #x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([temp_edges[i][1]])[0]
                                    x,y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][1]])[0]
                                    self.emitpoint.emit( x,y )
                                    
                        result.append([line,flow])
                        
                        

                flow = None
                for i in range(len(result)):
                            if i == 0:
                                flow = result[i][1]
                            else:
                                flow = flow + result[i][1]
                
                #self.status.emit(flow.tolist())
                
                #list1.append( self.selafinlayer.slf.tags["times"].tolist() )
                list1.append( self.selafinlayer.hydrauparser.getTimes().tolist() )
                list2.append( flow.tolist() )
                list3.append( result )
                
        except Exception as e :
            self.error.emit('flow calculation error : ' + str(e))
                
        print(list1,list2,list3)
        self.finished.emit(list1,list2,list3)
     
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
    emitprogressbar = QtCore.pyqtSignal(float)
    
    

    
         
    def getLines(self,polyline1,METHOD):
        """
        Line input traitment in order to be only in the area of the modelisation
        Method0 : line slighlty inside the area of modelisation
        Method1 : line slighlty outside
        """
        DEBUG = True

        if sys.version_info.major == 2:
            templine2 = qgis.core.QgsGeometry.fromPolyline([ qgis.core.QgsPoint(i[0],i[1])  for i in polyline1[:-1] ])
        elif sys.version_info.major == 3:
            templine2 = qgis.core.QgsGeometry.fromPolylineXY([qgis.core.QgsPointXY(i[0], i[1]) for i in polyline1[:-1]])
        
        if DEBUG : self.status.emit('templine2' +str(templine2.asPolyline()))
        
        temp3_in = []
        temp3_out = []
        
        meshx,meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        triplotcontourf = self.fig.gca().tricontourf(meshx,meshy,ikle,self.selafinlayer.value,[-1.0E20,1.0E20])
        
        if METHOD==0 : buffervalue = 0.05
        elif METHOD == 1 : buffervalue = -0.05
        
        for collection in triplotcontourf.collections:
            for path in collection.get_paths():
                for polygon in path.to_polygons():
                    if sys.version_info.major == 2:
                        polygons2 = qgis.core.QgsGeometry.fromPolygon([[ qgis.core.QgsPoint(i[0],i[1])  for i in polygon]])
                    elif sys.version_info.major == 3:
                        # if DEBUG: self.status.emit('polygon' + str(polygon))
                        polygons2 = qgis.core.QgsGeometry.fromPolygonXY([[qgis.core.QgsPointXY(i[0], i[1]) for i in polygon]])
                    #if DEBUG : self.status.emit('polygons2' +str(polygons2.asPolygon()))
                    
                    if templine2.intersects(polygons2):
                        if  ( np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 >0 ):     #outer polygon

                            inter = templine2.intersection(polygons2.buffer(-buffervalue,12))
                            #if DEBUG : self.status.emit('inter' +str(inter.asMultiPolyline()))
                            #if DEBUG : self.status.emit('inter' +str(inter.asPolyline()))
                            #if DEBUG : self.status.emit('inter' +str(type( inter.asPolyline())) )
                            #if DEBUG : self.status.emit('inter' +str(inter.type()))
                            if inter.type() == 1 :
                                #if len(inter.asMultiPolyline()) == 0:
                                if not inter.isMultipart():
                                    temp3_out.append(inter)
                                else:
                                    for line3 in  inter.asMultiPolyline():
                                        if sys.version_info.major == 2:
                                            temp3_out.append(qgis.core.QgsGeometry.fromPolyline([ qgis.core.QgsPoint(i[0],i[1])  for i in line3 ]))
                                        elif sys.version_info.major == 3:
                                            temp3_out.append(qgis.core.QgsGeometry.fromPolylineXY( [qgis.core.QgsPointXY(i[0], i[1]) for i in line3]))

                        else:                                                                        #inner polygon
                            inter = templine2.intersection(polygons2.buffer(buffervalue,12))
                            if DEBUG : self.status.emit('inter' +str(inter.asMultiPolyline()))
                            if DEBUG : self.status.emit('inter' +str(inter.asPolyline()))
                            if DEBUG : self.status.emit('inter' +str(inter.type()))
                            if inter.type() == 1 :
                                if len(inter.asMultiPolyline()) == 0:
                                    temp3_out.append(inter)
                                else:
                                    for line3 in  inter.asMultiPolyline():      
                                        temp3_out.append(qgis.core.QgsGeometry.fromPolyline([ qgis.core.QgsPoint(i[0],i[1])  for i in line3 ]))
                                

            
        temp3out_line = temp3_out
        temp3in_line = temp3_in
        
        
        if DEBUG : self.status.emit('temp3out_line' +str([line.asPolyline() for line in temp3out_line]))
        if DEBUG : self.status.emit('temp3in_line' +str([line.asPolyline() for line in temp3in_line]))
        
        linefinal2 = []    
        
        
        for lineout in temp3out_line:
            templine = lineout
            for linein in temp3in_line:
                linein  = linein
                if lineout.length() > linein.length() and lineout.intersects(linein.buffer(0.01,12)):
                    templine = templine.difference(linein.buffer(0.02,12))
            if templine.type() == 1 :
                # if len(templine.asMultiPolyline()) == 0:
                if not templine.isMultipart():
                    linefinal2.append(templine)
                else:
                    for line3 in  templine.asMultiPolyline():
                        if sys.version_info.major == 2:
                            linefinal2.append(qgis.core.QgsGeometry.fromPolyline([ qgis.core.QgsPoint(i[0],i[1])  for i in line3 ]))
                        elif sys.version_info.major == 3:
                            linefinal2.append( qgis.core.QgsGeometry.fromPolylineXY([qgis.core.QgsPointXY(i[0], i[1]) for i in line3]))

                        
        if DEBUG : self.status.emit('linefinal2' +str([line.asPolyline() for line in linefinal2]))

        #to keep line direction qgis
        if sys.version_info.major == 2:
            geomtemp=[ [ qgis.core.QgsPoint(i[0],i[1]) for i in line.asPolyline() ] for line in linefinal2    ]
            multitemp = qgis.core.QgsGeometry.fromMultiPolyline(geomtemp)
        elif sys.version_info.major == 3:
            geomtemp=[ [ qgis.core.QgsPointXY(i[0],i[1]) for i in line.asPolyline() ] for line in linefinal2    ]
            multitemp = qgis.core.QgsGeometry.fromMultiPolylineXY(geomtemp)
        multidef2 =  templine2.intersection(multitemp.buffer(0.01,12))
        
        if DEBUG : self.status.emit('multidef2' +str(multidef2))
        
        
        #qgis
        # if len(multidef2.asMultiPolyline()) == 0:
        if not multidef2.isMultipart():
            result = np.array([multidef2.asPolyline()])
        else:
            result = np.array(multidef2.asMultiPolyline())
        

        return result
    
    
    
    
         
    def getLines2(self,polyline1,METHOD):
        """
        Line input traitment in order to be only in the area of the modelisation
        Method0 : line slighlty inside the area of modelisation
        Method1 : line slighlty outside
        """
        
        DEBUG = True
        
        if DEBUG : self.status.emit('getLines - polylin : ' + str(polyline1))
        templine1 = shapely.geometry.linestring.LineString([(i[0],i[1]) for i in polyline1[:-1]])
        
        templine2 = qgis.core.QgsGeometry.fromPolyline([ qgis.core.QgsPoint(i[0],i[1])  for i in polyline1[:-1] ])
        
        temp2_in = []
        temp2_out = []
        
        temp3_in = []
        temp3_out = []
        
        meshx,meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        triplotcontourf = self.fig.gca().tricontourf(meshx,meshy,ikle,self.selafinlayer.value,[-1.0E20,1.0E20])
        
        if METHOD==0 : buffervalue = 0.05
        elif METHOD == 1 : buffervalue = -0.05
        
        for collection in triplotcontourf.collections:
            for path in collection.get_paths():
                for polygon in path.to_polygons(): 
                    tuplepoly = [(i[0],i[1]) for i in polygon]
                    polygons = shapely.geometry.polygon.Polygon(tuplepoly)
                    polygons2 = qgis.core.QgsGeometry.fromPolygon([[ qgis.core.QgsPoint(i[0],i[1])  for i in polygon]])
                    
                    #shapely
                    
                    if templine1.intersects(polygons):
                        if  ( np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 >0 ):     #outer polygon
                            inter = templine1.intersection(polygons.buffer(-buffervalue))
                            if isinstance(inter,shapely.geometry.linestring.LineString):
                                temp2_out.append(inter)
                            else:
                                for line3 in   inter:      
                                    temp2_out.append(line3)
                        else:                                                                        #inner polygon
                            inter = templine1.intersection(polygons.buffer(buffervalue))
                            if isinstance(inter,shapely.geometry.linestring.LineString):
                                temp2_in.append(inter)
                            else:
                                for line3 in   inter:      
                                    temp2_in.append(line3)
                                    
                    #qgis
                    
                    if templine2.intersects(polygons2):
                        if  ( np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 >0 ):     #outer polygon
                            inter = templine2.intersection(polygons2.buffer(-buffervalue,12))
                            if True:
                                if inter.type() == 1 :
                                    if len(inter.asMultiPolyline()) == 1:
                                        temp3_out.append(inter)
                                    else:
                                        for line3 in   inter.asMultiPolyline():      
                                            temp3_out.append(line3)
                        else:                                                                        #inner polygon
                            inter = templine2.intersection(polygons2.buffer(buffervalue,12))
                            if True:
                                if inter.type() == 1 :
                                    if len(inter.asMultiPolyline()) == 1:
                                        temp3_in.append(inter)
                                    else:
                                        for line3 in   inter.asMultiPolyline():      
                                            temp3_in.append(line3)
                                    
                                    
                                    
                                    
        
        temp2out_line = shapely.geometry.multilinestring.MultiLineString(temp2_out)
        temp2in_line = shapely.geometry.multilinestring.MultiLineString(temp2_in)


        temp3out_line = [qgis.core.QgsGeometry.fromMultiPolyline([[ qgis.core.QgsPoint(i[0],i[1])  for i in line ]]) for line in temp3_out ]
        temp3in_line = [qgis.core.QgsGeometry.fromMultiPolyline([[ qgis.core.QgsPoint(i[0],i[1])  for i in line ]]) for line in temp3_in ]
        
        if False:
            self.status.emit('temp2out_line : ' + str(temp2out_line))
            self.status.emit('temp3out_line : ' + str([line.asMultiPolyline() for line in temp3out_line]))
            
            self.status.emit('temp2in_line : ' + str(temp2in_line))
            self.status.emit('temp3in_line : ' + str([line.asMultiPolyline() for line in temp3in_line]))
            
            
        

        linefinal = []    
        linefinal2 = []    
        
        #shapely
        
        for lineout in temp2out_line:
            templine = lineout
            for linein in temp2in_line:
                if lineout.length > linein.length and lineout.intersects(linein.buffer(0.01)):
                    templine = templine.difference(linein.buffer(0.02))
            if isinstance(templine,shapely.geometry.linestring.LineString):
                linefinal.append(templine)
            else:
                for line3 in   templine:      
                    linefinal.append(line3)
                    
        #qgis
        
        for lineout in temp3out_line:
            templine = lineout
            for linein in temp3in_line:
                linein  = linein
                if lineout.length() > linein.length() and lineout.intersects(linein.buffer(0.01,12)):
                    templine = templine.difference(linein.buffer(0.02,12))
            if templine.type() == 1 :
                if len(templine.asMultiPolyline()) == 1:
                    linefinal2.append(templine)
                else:
                    for line3 in   templine.asMultiPolyline():      
                        linefinal2.append(line3)
                    
        
        if True:
            self.status.emit('linefinal : ' + str(linefinal))
            self.status.emit('linefinal2 : ' + str([line.asMultiPolyline() for line in linefinal2]))

        #to keep line direction shapely
        multitemp = shapely.geometry.multilinestring.MultiLineString(linefinal)
        multidef =  templine1.intersection(multitemp.buffer(0.01))
        
        #to keep line direction qgis
        geomtemp=[]
        for multiline in linefinal2:
            for line    in multiline.asMultiPolyline():
                geomtemp.append([ qgis.core.QgsPoint(i[0],i[1]) for i in line ])
        
        multitemp = qgis.core.QgsGeometry.fromMultiPolyline(geomtemp)
        multidef2 =  templine2.intersection(multitemp.buffer(0.01,12))
        
        
        self.status.emit(str(multidef))
        self.status.emit(str(multidef2.asMultiPolyline()))
        
        
        #shapely
        
        if isinstance(multidef,shapely.geometry.linestring.LineString):
            multidef = [multidef]
        
        result=[]
        for line in multidef:
            result.append(np.array([[point[0],point[1]] for point in line.coords ]))
        result = np.array(result)
        
        
        #qgis
        result2 = np.array(multidef2.asMultiPolyline())
        
        
        self.status.emit('result '+str(result))
        self.status.emit('result2 '+str(result2))
        

        return result
        
    def getCalcPointsSlice(self,line):
        linetemp = np.array([[point[0],point[1]] for point in line.coords ])
        #print str(line)
        temp_point_final=[]
        temp_edges_final=[]
        temp_bary_final = []
        for i in range(len(linetemp)-1) :
            resulttemp=[]
            lintemp1=np.array([[linetemp[i][0],linetemp[i][1]],[linetemp[i+1][0],linetemp[i+1][1]]])
            lintemp1shapely=shapely.geometry.linestring.LineString([(linetemp[i][0],linetemp[i][1]),(linetemp[i+1][0],linetemp[i+1][1])])
            meshx,meshy = self.selafinlayer.hydrauparser.getFacesNodes()
            ikle = self.selafinlayer.hydrauparser.getElemFaces()
            
            quoi = sliceMesh(lintemp1,np.asarray(ikle),np.asarray(meshx),np.asarray(meshy))
            """
            quoi[0][0] is list of points of intersection
            quoi[0][1] is list of egdes intersected by line
            quoi[0][2] is kind of (not exactly) barycentric thing
            """

            temp_point=[]
            temp_edges=[]
            temp_bary = []

            #linebuf = line.buffer(1.0)
            
            for i, edgestemp in enumerate(quoi[0][1]):  #slicemesh - quoi[0][1] is list of egdes intersected by line
                #line4 : line of edge
                """
                x1,y1 = self.selafinlayer.hydrauparser.getXYFromNumPoint([edgestemp[0]])[0]
                x2,y2 = self.selafinlayer.hydrauparser.getXYFromNumPoint([edgestemp[1]])[0]
                """
                x1,y1 = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edgestemp[0]])[0]
                x2,y2 = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edgestemp[1]])[0]
                
                #line4 = LineString([(self.selafinlayer.slf.MESHX[edgestemp[0]],self.selafinlayer.slf.MESHY[edgestemp[0]]),(self.selafinlayer.slf.MESHX[edgestemp[1]],self.selafinlayer.slf.MESHY[edgestemp[1]])])
                line4 = shapely.geometry.linestring.LineString([(x1,y1),(x2,y2)])
                if line4.crosses(lintemp1shapely):
                    temp_edges.append(edgestemp)
                    temp_point.append([quoi[0][0][i][0],quoi[0][0][i][1]])
                    temp_bary.append(quoi[0][2][i])
            
            #check direction
            dir1 = lintemp1shapely.coords[1][0]-lintemp1shapely.coords[0][0]
            dir2 = temp_point[1][0]-temp_point[0][0]
            
            if dir1>0 and dir2 >0:
                pass
                #self.status.emit('line direction ok' + str(dir1) + ' ' +str(dir2))
            elif dir1<0 and dir2 <0:
                pass
                #self.status.emit('line direction ok'+ str(dir1) + ' ' +str(dir2))
            else:
                #self.status.emit('line direction pas ok '+ str(dir1) + ' ' +str(dir2))
                temp_edges = temp_edges[::-1]
                temp_point = temp_point[::-1]
                temp_bary = temp_bary[::-1]
                
            temp_point_final=temp_point_final + temp_point
            temp_edges_final = temp_edges_final + temp_edges
            temp_bary_final = temp_bary_final + temp_bary

        return temp_edges_final,temp_point_final,temp_bary_final
        
        

    

    def computeFlowBetweenPoints(self,xy1,h1,v1vect,xy2,h2,v2vect):
        vectorface = np.array([xy2[0]-xy1[0],xy2[1]-xy1[1]])
        lenght = np.linalg.norm(vectorface)
        if lenght == 0.0:
            return None
        vectorfacenorm = vectorface/np.linalg.norm(vectorface)
        perp = np.array([0,0,-1.0])
        vectorfacenormcrosstemp = np.cross(vectorfacenorm,perp)
        #vectorfacenormcross = np.array([vectorfacenormcrosstemp[0],vectorfacenormcrosstemp[1]]*len(self.selafinlayer.slf.getSERIES([temp_edges[i][1]],[parametervv],False)[0][0]))
        vectorfacenormcross = np.array([vectorfacenormcrosstemp[0],vectorfacenormcrosstemp[1]])


        v1 = np.array([np.dot(vectorfacenormcross,temp) for temp in v1vect ])
        v2 = np.array([np.dot(vectorfacenormcross,temp) for temp in v2vect ])

        """
        v1 et v2 normal à la face
        loi lineaire :
        h = ax+b 
        h1 = b (x=0)
        h2 = axlenght + b 
        b= h1
        a = (h2-h1)/lenght
        
        q = int ( (ah * x + bh) * (av * x + bv )   dx ,0,lenght)
        q = int ( (ah x av)  x^2 + (  ah x bv  + av x bh    ) x + bh x bv   dx ,0,lenght)
        q = ( 1/3 x (ah x av)  x^3 + 1/2 (  ah x bv  + av x bh    ) x^2 + (bh x bv ) * x   ,0,lenght)
        
        q = 1/3 x (ah x av)  lenght^3 + 1/2 (  ah x bv  + av x bh    ) lenght^2 + (bh x bv ) x lenght
        """
        
        deltah = h2-h1
        ah = deltah/lenght
        bh = h1
        deltav = v2 - v1
        av = deltav/lenght
        bv = v1

        #self.status.emit( 'ah : '+str(ah.shape)+'  bh : '+str(bh.shape)+' av :  '+str(av.shape)+' bv : '+str(bv.shape))
        flow = 1.0/3.0*(ah*av)*math.pow(lenght,3) + 1.0/2.0*(ah*bv+av*bh)*math.pow(lenght,2) + (bh*bv)*lenght
        if np.isnan(flow).any():
            self.status.emit(' vecor ' + str(vectorface) + 'lenght ' + str(np.linalg.norm(vectorface)) +  ' norm ' + str(vectorfacenormcross))
            #self.status.emit( 'ah : '+str(ah)+'  bh : '+str(bh)+' av :  '+str(av)+' bv : '+str(bv)+' flow : '+str(flow))
            #self.status.emit( 'flow ' + str(flow) + ' - norm ' +str(vectorfacenormcross) + ' - edges '+str(edges1) + 'x ' +str(self.selafinlayer.slf.MESHX[edges1[0]]) + ' '+str(edges2) + ' - h1 '+str(h1) + ' - h2 ' + str(h2) + ' - v1temp : '+str(v1temp)+  ' - v1 ' + str(v1) + ' v2temp ' + str(v2temp) +  ' - v2 ' + str(v2))
            #self.status.emit( 'flow ' + str(flow[0]) + ' - norm ' +str(vectorfacenormcross) + ' - edges '+str(edges1) + 'x ' +str(self.selafinlayer.slf.MESHX[edges1[0]]) + ' '+str(edges2) + ' - h1 '+str(h1[0]) + ' - h2 ' + str(h2[0]) + ' - v1temp : '+str(v1temp[0])+  ' - v1 ' + str(v1[0]) + ' v2temp ' + str(v2temp[0]) +  ' - v2 ' + str(v2[0]))
        return flow
    

        
    def valuebetweenEdges(self,xy,edges,param):
        xytemp = np.array(xy)
        h11 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([edges[0] + 1],[param],self.selafinlayer.hydrauparser.parametres)[0][0])   #getseries begins at  1 
        h12 = np.array(self.selafinlayer.hydrauparser.getTimeSerie([edges[1] + 1 ],[param],self.selafinlayer.hydrauparser.parametres)[0][0])
        """
        e1 = np.array([self.selafinlayer.slf.MESHX[edges[0]],self.selafinlayer.slf.MESHY[edges[0]]])
        e2 = np.array([self.selafinlayer.slf.MESHX[edges[1]],self.selafinlayer.slf.MESHY[edges[1]]])
        """
        """
        e1 = np.array(self.selafinlayer.hydrauparser.getXYFromNumPoint([edges[0]]))
        e2 = np.array(self.selafinlayer.hydrauparser.getXYFromNumPoint([edges[1]]))
        """
        e1 = np.array(self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edges[0]]))
        e2 = np.array(self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edges[1]]))
        
        rap=np.linalg.norm(xytemp-e1)/np.linalg.norm(e2-e1)
        return (1.0-rap)*h11 + (rap)*h12
        
        
    def getNearest(self,x,y,triangle):
        numfinal=None
        distfinal = None
        meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        for num in np.array(ikle)[triangle]:
            dist = math.pow(math.pow(float(meshx[num])-float(x),2)+math.pow(float(meshy[num])-float(y),2),0.5)
            if distfinal:
                if dist<distfinal:
                    distfinal = dist
                    numfinal=num
            else:
                distfinal = dist
                numfinal=num
        return numfinal
        
    def getNearestPointEdge(self,x,y,triangle):
        numfinal1=None
        trianglepoints=[]
        point = np.array([x,y])
        distedge = None
        meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        for num in np.array(ikle)[triangle]:
            trianglepoints.append(np.array([np.array([meshx[num],meshy[num]]),num]))
        num1 = np.array(ikle)[triangle][0]
        trianglepoints.append(np.array([np.array([meshx[num1],meshy[num1]]),num1]))
            
        for i in range(len(trianglepoints)-1):
            #d = np.linalg.norm(np.cross(l2-l1, l1-p))/np.linalg.norm(l2-l1)
            dist = np.linalg.norm(np.cross(trianglepoints[i+1][0]-trianglepoints[i][0], trianglepoints[i][0]-point))/np.linalg.norm(trianglepoints[i+1][0]-trianglepoints[i][0])
            if distedge:
                if dist<distedge:
                    distedge = dist
                    numfinal1=[trianglepoints[i][1],trianglepoints[i+1][1]]
            else:
                distedge = dist
                numfinal1=[trianglepoints[i][1],trianglepoints[i+1][1]]
        numfinal2=None
        distfinal = None
        
        for num in numfinal1:
            distpoint = math.pow(math.pow(float(meshx[num])-float(x),2)+math.pow(float(meshy[num])-float(y),2),0.5)
            #d = norm(np.cross(l2-l1, l1-p))/norm(l2-l1)
            if distfinal:
                if distpoint<distfinal:
                    distfinal = distpoint
                    numfinal2=num
            else:
                distfinal = distpoint
                numfinal2=num
        return numfinal2
        
        
        

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitComputeFlow(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None
        self.processtype = 0

    def start(self,                 
                 selafin,method,
                 line):
        #Launch worker
        self.worker = computeFlow(selafin,method,line)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.computeFlowMain)
        self.worker.status.connect(self.writeOutput)
        self.worker.emitpoint.connect(self.emitPoint)
        self.worker.error.connect(self.raiseError)
        self.worker.emitprogressbar.connect(self.updateProgressBar)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        

    
    def raiseError(self,str):
        if self.processtype ==0:
            self.error.emit(str)
        elif self.processtype in [1,2,3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print(str)
            sys.exit(0)
            
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self,list1,list2,list3):
        self.finished1.emit(list1,list2,list3)

    def emitPoint(self,x,y):
        self.emitpoint.emit(x,y)
        
    def updateProgressBar(self,float1):
        self.emitprogressbar.emit(float1)
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
    emitprogressbar = QtCore.pyqtSignal(float)
    

    