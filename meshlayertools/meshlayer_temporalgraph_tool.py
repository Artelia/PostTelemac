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

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'TemporalGraphTool.ui'))



class TemporalGraphTool(AbstractMeshLayerTool,FORM_CLASS):

    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        
#*********************************************************************************************
#***************Imlemented functions  **********************************************************
#********************************************************************************************
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Line_Graph_48x48_time.png' )
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.clickTool = qgis.gui.QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        self.rubberband = None
        self.graphtempactive = False
        self.graphtempdatac = []
        self.vectorlayerflowids = None
        #Tools tab - temporal graph
        self.figure1 = matplotlib.pyplot.figure(self.meshlayer.instancecount + 1)
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
        self.comboBox_2.currentIndexChanged.connect(self.activateMapTool)
        self.pushButton_limni.clicked.connect(self.computeGraphTemp)
        self.pushButton_graphtemp_pressepapier.clicked.connect(self.copygraphclipboard)
        

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""
        self.resetRubberband()
        try : 
            self.clickTool.canvasClicked.disconnect()
        except Exception, e : 
            pass
        
        self.activateMapTool()
        
    def onDesactivation(self):
        if self.rubberband:
            self.rubberband.reset(qgis.core.QGis.Point)
            
#*********************************************************************************************
#***************Behaviour functions  **********************************************************
#********************************************************************************************

        
    def activateMapTool(self):
        if self.comboBox_2.currentIndex() == 0:
            self.propertiesdialog.canvas.setMapTool(self.clickTool)
            self.clickTool.canvasClicked.connect(self.computeGraphTemp)
            self.pushButton_limni.setEnabled(False)
        else:
            self.pushButton_limni.setEnabled(True)
            try:
                self.clickTool.canvasClicked.disconnect(self.computeGraphTemp)
            except Exception, e:
                pass
                
        
    def updateParams(self):

        self.comboBox_parametreschooser.clear()
        for i in range(len(self.meshlayer.hydrauparser.parametres)):
            temp1 = [str(self.meshlayer.hydrauparser.parametres[i][0])+" : "+str(self.meshlayer.hydrauparser.parametres[i][1])]
            self.comboBox_parametreschooser.addItems(temp1)
            
    def createRubberband(self):
        self.rubberband = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QGis.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
            
    def resetRubberband(self):
        if self.rubberband:
            self.rubberband.reset(qgis.core.QGis.Point)
            
            
#*********************************************************************************************
#***************Main functions  **********************************************************
#********************************************************************************************
        
        
    def computeGraphTemp(self,qgspointfromcanvas=None):
        """
        Activated with temporal graph tool - points from layer
        """
        if not self.rubberband:
            self.createRubberband()
        try:
            self.vectorlayerflowids = None
            self.selectionmethod = self.comboBox_2.currentIndex()
            if self.selectionmethod == 0:       #temporary point
                if not self.graphtempactive:
                    xformutil = self.meshlayer.xform
                    qgspointtransformed = xformutil.transform(qgspointfromcanvas,qgis.core.QgsCoordinateTransform.ReverseTransform)
                    self.launchThread([[qgspointtransformed.x(),qgspointtransformed.y()]])
                
            elif self.selectionmethod == 1 :
                layer = qgis.utils.iface.activeLayer()
                if not (layer.type() == 0 and layer.geometryType()==0):
                    QMessageBox.warning(qgis.utils.iface.mainWindow(), "PostTelemac", self.tr("Select a point vector layer"))
                else:
                    xformutil = qgis.core.QgsCoordinateTransform(self.meshlayer.realCRS, layer.crs() )
                    self.rubberband.reset(qgis.core.QGis.Point)
                    self.ax.cla()
                    self.checkBox.setChecked(True)
                    layer = qgis.utils.iface.activeLayer()
                    iter = layer.getFeatures()
                    geomfinal=[]
                    self.vectorlayerflowids = []
                    for i,feature in enumerate(iter):
                        try:
                            self.vectorlayerflowids.append(str(feature[0]))
                        except:
                            self.vectorlayerflowids.append(str(feature.id()))
                        geom=feature.geometry().asPoint()
                        temp1 = xformutil.transform(qgis.core.QgsPoint(geom[0],geom[1]),qgis.core.QgsCoordinateTransform.ReverseTransform)
                        geom=[temp1.x(),temp1.y()]
                        
                        geomfinal.append(geom)
                    if not self.graphtempactive:
                        self.launchThread(geomfinal)    
        except Exception , e :
            print str(e)
            

    def launchThread(self,geom):
        #if self.graphtodo ==0:
        #self.rubberbandpoint.reset(qgis.core.QGis.Point)
        if not self.checkBox.isChecked() and self.rubberband :
            self.rubberband.reset(qgis.core.QGis.Point)
        self.initclass=InitGraphTemp()
        #self.initclass = self.initclassgraphtemp

            
        self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
        self.initclass.error.connect(self.propertiesdialog.errorMessage)
        self.initclass.emitpoint.connect(self.addPointRubberband)
        self.initclass.emitprogressbar.connect(self.updateProgressBar)
        self.initclass.finished1.connect(self.workerFinished)
        
        self.initclass.start(self.meshlayer, self, geom)
        self.graphtempactive = True
        self.pushButton_limni.setEnabled(False)
        
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
        self.label_max.setText('Max : ' + str('{:,}'.format(maxtemp).replace(',', ' ') ))
        self.label_min.setText('Min : ' + str('{:,}'.format(mintemp).replace(',', ' ') ))
        self.canvas1.draw()
        if self.selectionmethod == 1 :
            self.checkBox.setChecked(False)
        self.graphtempactive = False
        if self.comboBox_2.currentIndex() != 0:
            self.pushButton_limni.setEnabled(True)

                
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
                self.rubberband.addGeometry(QgsGeometry.fromPolygon([points]), None)
            else:
                qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPoint(x[0],y[0]))
                #self.rubberband.addPoint(qgspoint)
                #self.rubberbandpoint.addPoint(qgspoint)
                self.rubberband.addGeometry(QgsGeometry.fromPolygon([[qgspoint]]), None)
        else:
            qgspoint = self.meshlayer.xform.transform(qgis.core.QgsPoint(x,y))
            self.rubberband.addPoint(qgspoint)
            
    def updateProgressBar(self,float1):
        self.propertiesdialog.progressBar.setValue(int(float1))
        
        
#*********************************************************************************************
#*************** Thread **********************************************************
#********************************************************************************************
        
class GraphTemp(QtCore.QObject):
    
    def __init__(self, selafin, graphtemptool, qgspoints, compare):
        
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.points = qgspoints
        #self.skdtree = None
        self.compare = compare
        self.graphtemptool = graphtemptool


    def createGraphTemp(self):
        try:
            list1=[]
            list2=[]
            for i in range(len(self.points)):
                abscisse = []
                ordonnees=[]
                #triangle = self.selafinlayer.trifind.__call__(self.points[i][0],self.points[i][1])
                #if triangle != -1:
                #enumpoint = self.getNearest(self.points[i])
                enumpoint = self.selafinlayer.hydrauparser.getNearestPoint(self.points[i][0],self.points[i][1] )
                if enumpoint:
                    x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([enumpoint])[0]
                    
                    self.emitpoint.emit(x,y)
                    #abscisse = self.selafinlayer.slf.tags["times"].tolist()
                    abscisse = self.selafinlayer.hydrauparser.getTimes().tolist()
                    
                    param = self.graphtemptool.comboBox_parametreschooser.currentIndex()

                    if self.compare :
                        triangles,numpointsfinal,pointsfinal,coef = self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getInterpFactorInTriangleFromPoint([x],[y])
                        self.status.emit(str(triangles)+' ' +str(numpointsfinal)+' ' +str(pointsfinal)+' ' +str(coef))
                        layer2serie = 0
                        #print str(numpointsfinal[0])
                        for i, numpoint in enumerate(numpointsfinal[0]):
                            #layer2serie += float(coef[0][i]) * self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getTimeSerie([numpoint],[self.selafinlayer.parametres[param[0]][3]],self.selafinlayer.parametres)
                            layer2serie += float(coef[0][i]) * self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getTimeSerie([numpoint +1],[self.selafinlayer.hydrauparser.parametres[param][3]],self.selafinlayer.hydrauparser.parametres)
                        #print 'ok1'
                        layer1serie = self.selafinlayer.hydrauparser.getTimeSerie([enumpoint + 1],[param],self.selafinlayer.hydrauparser.parametres)
                        tempordonees =  layer2serie  - layer1serie
                    else:
                        tempordonees =  self.selafinlayer.hydrauparser.getTimeSerie([enumpoint + 1],[param],self.selafinlayer.hydrauparser.parametres)
                    
                    ordonnees = tempordonees[0][0].tolist()
                    list1.append(abscisse)
                    list2.append(ordonnees)
            self.finished.emit(list1,list2)
        except Exception, e:
            self.status.emit('graph temp ' + str(e))
            self.finished.emit([],[])

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
    emitprogressbar = QtCore.pyqtSignal(float)

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitGraphTemp(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = None
        self.worker = None
        self.processtype = 0
        #self.selafin = selafin
        #self.graphtemp = graphTemp(selafin)
        self.compare = False

    def start(self, selafin, graphtemptool,qgspoints ):
                 
        #Launch worker
        self.thread = QtCore.QThread()
        self.worker = GraphTemp(selafin, graphtemptool, qgspoints, self.compare)
        #self.graphtemp.points = qgspoints
        #self.worker = self.graphtemp
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.createGraphTemp)
        self.worker.status.connect(self.writeOutput)
        self.worker.error.connect(self.raiseError)
        self.worker.emitpoint.connect(self.emitPoint)
        self.worker.emitprogressbar.connect(self.updateProgressBar)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        

    
    def raiseError(self,str):
        if self.processtype ==0:
            self.status.emit(str)
        elif self.processtype in [1,2,3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print str
            sys.exit(0)
            
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self,list1,list2):
        self.finished1.emit(list1,list2)
        
    def emitPoint(self,x,y):
        self.emitpoint.emit(x,y)
        
    def updateProgressBar(self,float1):
        self.emitprogressbar.emit(float1)

        
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
    emitprogressbar = QtCore.pyqtSignal(float)