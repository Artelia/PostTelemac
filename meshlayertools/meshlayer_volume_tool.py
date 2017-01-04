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

import scipy
import processing
import shapely
"""
from matplotlib import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
except :
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
"""

import matplotlib
import numpy as np

from ..meshlayerlibs.mpldatacursor import datacursor

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'VolumeTool.ui'))



class VolumeTool(AbstractMeshLayerTool,FORM_CLASS):

    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        
#*********************************************************************************************
#***************Imlemented functions  **********************************************************
#********************************************************************************************
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Line_Graph_48x48.png' )
        
        #self.clickTool = qgis.gui.QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        self.rubberband = None
        self.graphtempactive = False
        self.graphtempdatac = []
        self.vectorlayerflowids = None
        self.maptool = None
        self.pointstoDraw = []
        
        
        self.rubberbandpoint = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QGis.Point)
        #self.rubberbandpoint.setWidth(2)
        self.rubberbandpoint.setColor(QtGui.QColor(QtCore.Qt.red))
        
        
        #Tools tab - temporal graph
        self.figure1 = matplotlib.pyplot.figure(self.meshlayer.instancecount + 3)
        font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
        matplotlib.rc('font', **font)
        self.canvas1 = matplotlib.backends.backend_qt4agg.FigureCanvasQTAgg(self.figure1)
        self.ax = self.figure1.add_subplot(111)
        layout = QtGui.QVBoxLayout()
        try:
            self.toolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.canvas1, self.frame,True)
            layout.addWidget(self.toolbar)
        except Exception, e:
            pass
        layout.addWidget(self.canvas1)
        self.canvas1.draw()
        self.frame.setLayout(layout)
        #Signals connection
        """
        self.comboBox_2.currentIndexChanged.connect(self.activateMapTool)
        self.pushButton_limni.clicked.connect(self.computeGraphTemp)
        self.pushButton_graphtemp_pressepapier.clicked.connect(self.copygraphclipboard)
        """
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.comboBox_volumemethod.currentIndexChanged.connect(self.volumemethodchanged)
        
        self.comboBox_4.currentIndexChanged.connect(self.activateMapTool)
        self.pushButton_5.clicked.connect(self.copygraphclipboard)
        self.pushButton_volume.clicked.connect(self.computeVolume)
        
        self.propertiesdialog.meshlayerschangedsignal.connect(self.layerChanged)
        

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""            
        self.activateMapTool()
        
    def onDesactivation(self):
        self.resetRubberband()
            
#*********************************************************************************************
#***************Behaviour functions  **********************************************************
#********************************************************************************************

    def layerChanged(self):
        #enable volume tool if freesurface and bottom are present in parser params
        if (self.meshlayer.hydrauparser.paramfreesurface == None or self.meshlayer.hydrauparser.parambottom == None):
            self.groupBox_volume1.setEnabled(False)
            self.groupBox_volume2.setEnabled(False)
        else:
            self.groupBox_volume1.setEnabled(True)
            self.groupBox_volume2.setEnabled(True) 


    def volumemethodchanged(self, int1):
        if int1 in [0,1]:
            self.comboBox_volumeparam.setEnabled(False)
        else:
            self.comboBox_volumeparam.setEnabled(True)
        self.activateMapTool()

    
    def activateMapTool(self):
        if self.comboBox_4.currentIndex() == 0:
            self.pushButton_volume.setEnabled(False)
            self.computeVolume()
        else:
            self.pushButton_volume.setEnabled(True)
            try:
                self.deactivateTool()
            except Exception, e:
                pass
    
        
    def updateParams(self):

        self.comboBox_volumeparam.clear()
        for i in range(len(self.meshlayer.hydrauparser.parametres)):
            temp1 = [str(self.meshlayer.hydrauparser.parametres[i][0])+" : "+str(self.meshlayer.hydrauparser.parametres[i][1])]
            self.comboBox_volumeparam.addItems(temp1)
            
    def createRubberband(self):
        self.rubberband = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QGis.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
            
    def resetRubberband(self):
        if self.rubberband:
            self.rubberband.reset(qgis.core.QGis.Line)
        if self.rubberbandpoint:
            self.rubberbandpoint.reset(qgis.core.QGis.Point)
            
            
#*********************************************************************************************
#***************Main functions  **********************************************************
#********************************************************************************************
        
        
    def computeVolume(self):
        """
        Activated with volume graph tool
        """
        if not self.rubberband:
            self.createRubberband()
        self.dblclktemp = None
        self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
        self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"
        self.vectorlayerflowids = None
        #self.graphtodo = 2
        self.selectionmethod = self.comboBox_4.currentIndex()
        
        if self.selectionmethod in [0]:
            layer = qgis.utils.iface.activeLayer()
            if not self.maptool:
                self.maptool = VolumeMapTool(self.meshlayer.canvas,self.pushButton_volume)
            #Listeners of mouse
            self.connectTool()
            #init the mouse listener comportement and save the classic to restore it on quit
            self.meshlayer.canvas.setMapTool(self.maptool)
            #init the temp layer where the polyline is draw
            self.rubberband.reset(qgis.core.QGis.Line)
            #init the table where is saved the poyline
            self.pointstoDraw = []
            self.pointstoCal = []
            self.lastClicked = [[-9999999999.9,9999999999.9]]
            # The last valid line we drew to create a free-hand profile
            self.lastFreeHandPoints = []
        elif self.selectionmethod in [1,2]:
            layer = qgis.utils.iface.activeLayer()
            if not (layer.type() == 0 and layer.geometryType()==2):
                QMessageBox.warning(qgis.utils.iface.mainWindow(), "PostTelemac", self.tr("Select a polygone vector layer"))
            elif self.selectionmethod==1 and len(layer.selectedFeatures())==0:
                QMessageBox.warning(qgis.utils.iface.mainWindow(), "PostTelemac", self.tr("Select a polygon in a polygon vector layer"))
            else:
                self.ax.cla()
                grid2 = self.ax.grid(color='0.5', linestyle='-', linewidth=0.5)
                self.canvas1.draw()
                self.initclass1=[]
                self.checkBox_12.setChecked(True)
                iter = layer.selectedFeatures()
                if self.selectionmethod == 2 or len(iter)==0:
                    iter = layer.getFeatures()
                geomfinal=[]
                self.vectorlayerflowids = []
                xformutil = qgis.core.QgsCoordinateTransform(self.meshlayer.realCRS, layer.crs() )
                for i,feature in enumerate(iter):
                    try:
                        self.vectorlayerflowids.append(str(feature[0]))
                    except:
                        self.vectorlayerflowids.append(str(feature.id()))
                    geomss=feature.geometry().asPolygon()
                    
                    for geoms in geomss:
                        geoms=[[geom[0],geom[1]] for geom in geoms]
                        #geoms = geoms+[geoms[-1]]
                        geomstemp=[]
                        for geom in geoms:
                            qgspoint = xformutil.transform(QgsPoint(geom[0],geom[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
                            geomstemp.append([qgspoint.x(),qgspoint.y()])
                        geomfinal.append(geomstemp)
                self.launchThread(geomfinal)
                
            

    def launchThread(self,geom):
    
        self.initclass=InitComputeVolume()

            
        self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
        self.initclass.error.connect(self.propertiesdialog.errorMessage)
        self.initclass.emitpoint.connect(self.addPointRubberband)
        self.initclass.emitprogressbar.connect(self.updateProgressBar)
        self.initclass.finished1.connect(self.workerFinished)
        
        self.rubberbandpoint.reset(qgis.core.QGis.Point)
        self.rubberband.reset(qgis.core.QGis.Line)
        #self.selafinlayer.propertiesdialog.textBrowser_main.append(str(ctime() + ' - Computing flow'))
        self.propertiesdialog.normalMessage('Start computing volume')
        self.initclass.start(self.meshlayer,self,geom)
        self.pushButton_volume.setEnabled(False)
        
    def workerFinished(self,list1,list2,list3 = None):
        
        ax = self.ax
        if not self.checkBox.isChecked():
            ax.cla()
            if  len(self.graphtempdatac)>0:
                for datacu in self.graphtempdatac:
                    datacu.hide()
                    datacu.disable()
                self.graphtempdatac = []

        maxtemp=None
        mintemp = None

        grid2 = ax.grid(color='0.5', linestyle='-', linewidth=0.5)
        for i in range(len(list1)):
            test2 = ax.plot(list1[i], list2[i], linewidth = 3, visible = True)
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

        self.graphtempdatac.append(datacursor(test2,formatter="temps:{x:.0f}\nparametre:{y:.2f}".format,bbox=dict(fc='white'),arrowprops=dict(arrowstyle='->', fc='white', alpha=0.5)))
        self.label_volume_resultmax.setText('Max : ' + str('{:,}'.format(maxtemp).replace(',', ' ') ))
        self.label_volume_resultmin.setText('Min : ' + str('{:,}'.format(mintemp).replace(',', ' ') ))
        self.canvas1.draw()
        self.propertiesdialog.normalMessage('Computing volume finished')
        if self.comboBox_4.currentIndex() != 0:
            self.pushButton_volume.setEnabled(True)

                
        self.propertiesdialog.progressBar.reset()
            
    
    def copygraphclipboard(self):

        ax = self.ax
        
        self.clipboard = QtGui.QApplication.clipboard()
        strtemp=''
        datatemp=[]
        max=0
        for line in ax.get_lines():
            data = line.get_xydata()
            if len(data)>0:
                datatemp.append(data)
                maxtemp = len(data)
                if maxtemp>max:
                    max = maxtemp
        if self.vectorlayerflowids:
            for flowid in self.vectorlayerflowids:
                strtemp = strtemp + 'id : '+str(flowid)+ "\t"+ "\t"
            strtemp += "\n"
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
                    points.append(self.meshlayer.xform.transform(qgis.core.QgsPoint(x[i],y[i])))
                self.rubberband.addGeometry(qgis.core.QgsGeometry.fromPolygon([points]), None)
            else:
                qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPoint(x[0],y[0]))
                #self.rubberband.addPoint(qgspoint)
                self.rubberbandpoint.addPoint(qgspoint)
                #self.rubberband.addGeometry(qgis.core.QgsGeometry.fromPolygon([[qgspoint]]), None)
        else:
            qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPoint(x,y))
            self.rubberband.addPoint(qgspoint)
            
    def updateProgressBar(self,float1):
        self.propertiesdialog.progressBar.setValue(int(float1))
        
        
#*********************************************************************************************
#*************** Map Tool  **********************************************************
#********************************************************************************************
        
    def connectTool(self):
        QtCore.QObject.connect(self.maptool, QtCore.SIGNAL("moved"), self.moved)
        QtCore.QObject.connect(self.maptool, QtCore.SIGNAL("rightClicked"), self.rightClicked)
        QtCore.QObject.connect(self.maptool, QtCore.SIGNAL("leftClicked"), self.leftClicked)
        QtCore.QObject.connect(self.maptool, QtCore.SIGNAL("doubleClicked"), self.doubleClicked)
        QtCore.QObject.connect(self.maptool, QtCore.SIGNAL("deactivate"), self.deactivateTool)

    def deactivateTool(self):		#enable clean exit of the plugin
        QtCore.QObject.disconnect(self.maptool, QtCore.SIGNAL("moved"), self.moved)
        QtCore.QObject.disconnect(self.maptool, QtCore.SIGNAL("leftClicked"), self.leftClicked)
        QtCore.QObject.disconnect(self.maptool, QtCore.SIGNAL("rightClicked"), self.rightClicked)
        QtCore.QObject.disconnect(self.maptool, QtCore.SIGNAL("doubleClicked"), self.doubleClicked)

    def moved(self,position):			#draw the polyline on the temp layer (rubberband)
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                #Get mouse coords
                mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
                #Draw on temp layer
                self.rubberband.reset(qgis.core.QGis.Line)
                for i in range(0,len(self.pointstoDraw)):
                    self.rubberband.addPoint(qgis.core.QgsPoint(self.pointstoDraw[i][0],self.pointstoDraw[i][1]))
                self.rubberband.addPoint(qgis.core.QgsPoint(mapPos.x(),mapPos.y()))
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
                self.rubberband.reset(qgis.core.QGis.Line)
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
                if self.comboBox_4.currentIndex() != 0:
                    self.cleaning()
                #return
            else :
                if len(self.pointstoDraw) == 0:
                    self.rubberband.reset(qgis.core.QGis.Line)
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
                qgspoint = xform.transform(qgis.core.QgsPoint(point[0],point[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
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
        
        
class VolumeMapTool(qgis.gui.QgsMapTool):

    def __init__(self, canvas,button):
        qgis.gui.QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QtGui.QCursor(QtCore.Qt.CrossCursor)
        self.button = button

    def canvasMoveEvent(self,event):
        self.emit( QtCore.SIGNAL("moved"), {'x': event.pos().x(), 'y': event.pos().y()} )


    def canvasReleaseEvent(self,event):
        if event.button() == QtCore.Qt.RightButton:
            self.emit( QtCore.SIGNAL("rightClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )
        else:
            self.emit( QtCore.SIGNAL("leftClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )

    def canvasDoubleClickEvent(self,event):
        self.emit( QtCore.SIGNAL("doubleClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )

    def activate(self):
        qgis.gui.QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)
        #print  'activate'
        #self.button.setEnabled(False)
        #self.button.setCheckable(True)
        #self.button.setChecked(True)



    def deactivate(self):
        self.emit( QtCore.SIGNAL("deactivate") )
        #self.button.setCheckable(False)
        #self.button.setEnabled(True)
        #print  'deactivate'
        qgis.gui.QgsMapTool.deactivate(self)


    def setCursor(self,cursor):
        self.cursor = QtGui.QCursor(cursor)
        
        
#*********************************************************************************************
#*************** Thread **********************************************************
#********************************************************************************************


class computeVolume(QtCore.QObject):

    def __init__(self,                
                selafin, tool,line):

        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.polygons = line
        self.qgspolygone =  None
        self.tool = tool
        
    def computeVolumeMain(self):
        """
        Main method
        
        """
        
        METHOD = self.tool.comboBox_volumemethod.currentIndex()
        
        if METHOD in [0,2] :
            list1 = []
            list2 = []
            list3 = []
            
            try:
                for i, polygon in enumerate(self.polygons):
                    listpoly = [qgis.core.QgsPoint(polygon[i][0], polygon[i][1]) for i in range(len(polygon)) ]
                    self.qgspolygone =  qgis.core.QgsGeometry.fromPolygon([listpoly])
                    indextriangles = self.getTrianglesWithinPolygon(polygon)
                    
                    if len(indextriangles)==0:
                        continue
                    else:
                        volume = self.computeVolumeMesh(METHOD, indextriangles)
                        if len(list2) ==  0:
                            list1.append( self.selafinlayer.hydrauparser.getTimes().tolist() )
                            list2.append(volume)
                        else:
                            list2[0] += volume
                self.finished.emit(list1,list2,list3)
                
            except Exception, e :
                self.error.emit('volume calculation error : ' + str(e))
                self.finished.emit([],[],[])
                
        elif METHOD in [1,3] :
            list1 = []
            list2 = []
            list3 = []
            
            try:
                for i, polygon in enumerate(self.polygons):
                    listpoly = [qgis.core.QgsPoint(polygon[i][0], polygon[i][1]) for i in range(len(polygon)) ]
                    self.qgspolygone =  qgis.core.QgsGeometry.fromPolygon([listpoly])
                    #self.qgspolygone =  qgis.core.QgsGeometry.fromMultiPolygon([listpoly])
                    indexpoints,points = self.getPointsinPolygon(polygon)
                    indexpoints,points = self.getPointsOutsidePolygon(polygon,indexpoints,points)
                    
                    
                    for point in points.tolist() :
                        self.emitpoint.emit( [point[0]], [point[1]])
                    
                    if len(indexpoints)==0:
                        continue
                    else:
                        volume = self.computeVolumeVoronoiQGis(METHOD, points, indexpoints)
                        if len(list2) ==  0:
                            list1.append( self.selafinlayer.hydrauparser.getTimes().tolist() )
                            list2.append(volume)
                        else:
                            list2[0] += volume
                self.finished.emit(list1,list2,list3)
                
            except Exception, e :
                self.error.emit('volume calculation error : ' + str(e))
                self.finished.emit([],[],[])
                
        else:
            self.finished.emit([],[],[])
            
            
    def computeVolumeVoronoiScipy(self, METHOD , points, indexpoints):
        """
        Voronoi with scipy  method - not fully working
        """
        #getvoronoi table
        voronoi = scipy.spatial.Voronoi(points, furthest_site = False)
        vertices = voronoi.vertices
        regions = voronoi.regions
        #regions = [region for region in regions if (-1 not in region and len(region) > 0)]
        
        tempforresult = []  #contain point index and voronoi area
        for i, region in enumerate(regions):
            if (-1 not in region and len(region) > 0) :
                listpoly = [ qgis.core.QgsPoint(vertices[reg,0], vertices[reg,1]) for reg in region ]
                qgspolygonvoronoi =  qgis.core.QgsGeometry.fromPolygon([listpoly])
                if qgspolygonvoronoi.within(self.qgspolygone):
                    #draw reg
                    x = [vertices[reg,0] for reg in region]
                    y = [vertices[reg,1] for reg in region]
                    self.emitpoint.emit( x, y)
                    
                    area = qgspolygonvoronoi.area()
                    linkedpoint = indexpoints[voronoi.point_region.tolist().index(i)]
                    self.status.emit('Region : ' + str(region) + ' - Point lie : ' + str(linkedpoint) + ' - surface : ' +str(area))
                    tempforresult.append([linkedpoint, area])
        
        
        volume = None
        paramfreesurface = self.selafinlayer.hydrauparser.paramfreesurface
        parambottom = self.selafinlayer.hydrauparser.parambottom
        
        for i, result in enumerate(tempforresult):
            self.emitprogressbar.emit(float(float(i)/float(len(tempforresult))*100.0))
            if METHOD == 1:
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[parambottom, paramfreesurface]))
                if volume == None :
                    volume = result[1]*(h[1,0]-h[0,0])
                else:
                    volume += result[1]*(h[1,0]-h[0,0])
            elif METHOD == 3 :
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[self.selafinlayer.propertiesdialog.comboBox_volumeparam.currentIndex()]))
                if volume == None :
                    volume = result[1]*(h[0,0])
                else:
                    volume += result[1]*(h[0,0])
        return volume
            
            

            
            
    def computeVolumeVoronoiQGis(self, METHOD , points, indexpoints):
        """
        Voronoi with qgis method
        """
        self.status.emit('***** Nouveau calcul *****************')
        
        pointsdico = [shapely.geometry.Point(point[0], point[1]) for point in points ]
        c = processing.algs.qgis.voronoi.Context()
        sl = processing.algs.qgis.voronoi.SiteList(pointsdico)
        voropv = processing.algs.qgis.voronoi.voronoi(sl, c)
        self.status.emit(str(voropv))
        
        if False:
            self.status.emit(str('context *********'))
            self.status.emit(str(points))
            self.status.emit(str(c.vertices))
            self.status.emit(str(c.edges))
            self.status.emit(str(c.polygons))
            self.status.emit(str(' *********'))
            
        verticess = c.vertices
        voronoipolyg = []
        
        for (site, edges) in list(c.polygons.items()):
            #edges or not in he good order - order it
            edgesonly = [[edge[1], edge[2]]   for edge in edges]
            npedges = np.array(edgesonly)
            if -1 in npedges:       #edges with -1 are infinite line in polygon
                continue
            
            #fill goodph with first line
            goodpath = []
            goodpath.append(edges[0][1])
            goodpath.append(edges[0][2])
            
            #then add point in path
            i=3
            for i in range(len(edges) -2  ):
                temps = np.argwhere(npedges == goodpath[-1])
                for temp in temps:
                    if temp[1] == 0 :
                        if npedges[temp[0], 1 ] == goodpath[-2] :
                            continue
                        else:
                            goodpath.append(npedges[temp[0], 1 ])
                            break
                    elif temp[1] == 1 :
                        if npedges[temp[0], 0 ] == goodpath[-2] :
                            continue
                        else:
                            goodpath.append(npedges[temp[0], 0 ])
                            break

            listpoly = [qgis.core.QgsPoint(verticess[path][0], verticess[path][1]) for path in goodpath ]
            qgsvoropolygone =  qgis.core.QgsGeometry.fromPolygon([listpoly])
            
            
            #keep voronoi strictly within entry polygon
            if not qgsvoropolygone.within(self.qgspolygone):
                intersectedpolyg = qgis.core.QgsGeometry.fromPolygon( qgsvoropolygone.intersection(self.qgspolygone).asPolygon() )
            else:
                intersectedpolyg = qgis.core.QgsGeometry.fromPolygon( qgsvoropolygone.asPolygon() )
                
            voronoipolyg.append([indexpoints[site],intersectedpolyg])
            intersectedpolygtab = intersectedpolyg.asPolygon()
            if len(intersectedpolygtab)>0:
                x = [point[0] for point in intersectedpolygtab[0]]
                y = [point[1] for point in intersectedpolygtab[0]]
                self.emitpoint.emit( x, y)

        #volume compuation
        volume = None
        paramfreesurface = self.selafinlayer.hydrauparser.paramfreesurface
        parambottom = self.selafinlayer.hydrauparser.parambottom
        
        for i, result in enumerate( voronoipolyg ):
            self.emitprogressbar.emit(float(float(i)/float(len(voronoipolyg))*100.0))
            if METHOD == 1:
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[parambottom, paramfreesurface]))
                
                if volume == None :
                    volume = result[1].area()*(h[1,0]-h[0,0])
                else:
                    volume += result[1].area()*(h[1,0]-h[0,0])
                    
            elif METHOD == 3 :
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[self.selafinlayer.propertiesdialog.comboBox_volumeparam.currentIndex()]))
                
                if volume == None :
                    volume = result[1].area()*(h[0,0])
                else:
                    volume += result[1].area()*(h[0,0])
            
        
        
        return volume
            
            
            
    def getPointsinPolygon(self,polygon):
    
        #first get triangles in linebounding box ************************************************************
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 

        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()

        valtabx = np.where(np.logical_and(xMesh>rect[0], xMesh< rect[1]))
        valtaby = np.where(np.logical_and(yMesh>rect[2], yMesh< rect[3]))
        
        goodnums = np.intersect1d(valtabx[0],valtaby[0])
        
        #second get triangles inside line  ************************************************************
        goodnums2=[]
        for goodnum in goodnums:
            if qgis.core.QgsGeometry.fromPoint(qgis.core.QgsPoint(xMesh[goodnum],yMesh[goodnum])).within(self.qgspolygone):
                goodnums2.append(goodnum)
                
        points = np.array([[xMesh[i], yMesh[i]] for i in goodnums2 ])
        
        
        return goodnums2,points
        
    def getPointsOutsidePolygon(self,polygon,indexpoints, points):
        """
        return a new triangulation based on triangles visbles in the canvas. 
        return index of selafin points correspondind to the new triangulation
        """
        
        #first get triangles in linebounding box ************************************************************
        
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        
        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()

        trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
        triany = np.transpose(triany)
        
        valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
        valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))
        #index of triangles in canvas
        goodnums = np.intersect1d(valtabx[0],valtaby[0])
        #goodikle = mesh[goodnums]
        #goodpointindex = np.unique(goodikle)
        
        #second get triangles intersecting contour of polygon  ************************************************************
        goodnums2=[]
        qgspolygontoline = self.qgspolygone.convertToType(1)
        for goodnum in goodnums:
            if qgis.core.QgsGeometry.fromPolygon([[qgis.core.QgsPoint(xMesh[i],yMesh[i]) for i in mesh[goodnum]    ]]).intersects(qgspolygontoline):
                goodnums2.append(goodnum)
        
        pointstemp = points.tolist()
        
        for goodnum in goodnums2:
            for indexpoint in mesh[goodnum]:
                if not indexpoint in indexpoints:
                    indexpoints.append(indexpoint)
                    pointstemp.append([xMesh[indexpoint], yMesh[indexpoint]])
        
        
        return indexpoints,np.array(pointstemp)
            
    
    
    
        
    def getTrianglesWithinPolygon(self,polygon):
        """
        return a new triangulation based on triangles visbles in the canvas. 
        return index of selafin points correspondind to the new triangulation
        """
        
        #first get triangles in linebounding box ************************************************************
        
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        
        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()

        trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
        triany = np.transpose(triany)
        
        valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
        valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))
        #index of triangles in canvas
        goodnums = np.intersect1d(valtabx[0],valtaby[0])
        #goodikle = mesh[goodnums]
        #goodpointindex = np.unique(goodikle)
        
        #second get triangles inside line  ************************************************************
        goodnums2=[]
        for goodnum in goodnums:
            if qgis.core.QgsGeometry.fromPolygon([[qgis.core.QgsPoint(xMesh[i],yMesh[i]) for i in mesh[goodnum]    ]]).within(self.qgspolygone):
                goodnums2.append(goodnum)
                
        
        for goodnum in goodnums2:
            xtoprint = [xMesh[i] for i in mesh[goodnum]  ]
            ytoprint = [yMesh[i] for i in mesh[goodnum]  ]
            #self.status.emit(str(xtoprint)+' ' +str(ytoprint))
            self.emitpoint.emit( xtoprint,ytoprint)
            
        return goodnums2
        
    def computeVolumeMesh(self,METHOD,indextriangles):
        #self.status.emit('surf calc ')
        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        paramfreesurface = self.selafinlayer.hydrauparser.paramfreesurface
        parambottom = self.selafinlayer.hydrauparser.parambottom
        volume = None
        
        #self.status.emit(str(indextriangles))
        
        
        
        for i, indextriangle in enumerate(indextriangles):
            
            self.emitprogressbar.emit(float(float(i)/float(len(indextriangles))*100.0))
                
            #surface calculus
            p1 = np.array( [ xMesh[mesh[indextriangle,0]], yMesh[mesh[indextriangle,0]] ] )
            p2 = np.array( [ xMesh[mesh[indextriangle,1]], yMesh[mesh[indextriangle,1]] ] )
            p3 = np.array( [ xMesh[mesh[indextriangle,2]], yMesh[mesh[indextriangle,2]] ] )

            
            surface = float(np.linalg.norm(np.cross((p2-p1),(p3-p1))))/2.0
            
            
            if METHOD == 0 :
                h = np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1,mesh[indextriangle,1] + 1,mesh[indextriangle,2] + 1],[parambottom, paramfreesurface]))
                
                if False and i == 0 :
                    self.status.emit('interm')
                    self.status.emit(str(h.shape))
                    self.status.emit(str(h))
                    self.status.emit(str(h1.shape))
                    self.status.emit(str(h1))
                    
                if volume == None :
                    #volume = surface*(h1+h2+h3)/3
                    volume = surface*((h[1,0] - h[0,0])+(h[1,1] - h[0,1] )+(h[1,2] - h[0,2]))/3
                else:
                    #volume += surface*(h1+h2+h3)/3
                    volume += surface*((h[1,0] - h[0,0])+(h[1,1] - h[0,1] )+(h[1,2] - h[0,2]))/3
                    
            elif METHOD == 2 :
                h = np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1,mesh[indextriangle,1] + 1,mesh[indextriangle,2] + 1],[self.selafinlayer.propertiesdialog.comboBox_volumeparam.currentIndex()]))
                
                if volume == None :
                    #volume = surface*(h1+h2+h3)/3
                    volume = surface*((h[0,0])+( h[0,1] )+( h[0,2]))/3
                else:
                    #volume += surface*(h1+h2+h3)/3
                    volume += surface*((h[0,0])+( h[0,1] )+(h[0,2]))/3
        
        return volume

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(list,list)
    emitprogressbar = QtCore.pyqtSignal(float)

        

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitComputeVolume(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None
        self.processtype = 0

    def start(self,                 
                 selafin, tool,
                 line):
        #Launch worker
        self.worker = computeVolume(selafin,tool,line)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.computeVolumeMain)
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
            print str
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
    emitpoint = QtCore.pyqtSignal(list,list)
    emitprogressbar = QtCore.pyqtSignal(float)
    

    