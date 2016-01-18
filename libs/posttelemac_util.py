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
 Class for tool activation, link the property dialog and the tools libs
 and provide basic functions
 
Versions :
0.0 : debut

 ***************************************************************************/
"""


#import PyQT
from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
#import numpy
import numpy as np
#import time
from time import ctime
#import divers
from ..mpldatacursor import datacursor
from selectlinetool import SelectLineTool
#import local libs
from posttelemac_util_animation import *
from posttelemac_util_extractshp import *
from posttelemac_util_extractmesh import *
from posttelemac_util_extractpts import *
from posttelemac_util_graphtemp import *
from posttelemac_util_flow import *
from posttelemac_util_get_max import *
from posttelemac_util_getcomparevalue import *


class PostTelemacUtils():

    def __init__(self,layer):
        self.selafinlayer = layer
        self.graphtempactive = False
        self.datac = []
        self.rubberband = QgsRubberBand(self.selafinlayer.canvas, QGis.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QColor(Qt.red))
        self.clickTool = QgsMapToolEmitPoint(self.selafinlayer.canvas)
        self.tool = None                        #the activated map tool
        self.layerindex = None                  #for selection mode
        self.previousLayer = None               #for selection mode
        self.vectorlayerflowids = None
        self.graphtodo = None       #0 for limni, 1 for flow
        self.composition = None                 #the composer choosen for movie
        self.graphtempdatac = []
        self.graphflowdatac = []
        self.skdtree = None                   #Object that enables nearest point query
        self.compareprocess = None
        self.initclassgraphtemp = InitGraphTemp()
        #self.xformutil = None   #for vector crs transformation

        
        
    #****************************************************************************************************
    #************* Values***********************************************************
    #****************************************************************************************************

    def valeurs_click(self,qgspointfromcanvas):
        """
        Called in PostTelemacPropertiesDialog by value tool
        fill the tablewidget
        """
        #qgspointtransformed = self.selafinlayer.xform.transform(qgspoint,QgsCoordinateTransform.ReverseTransform)
        if self.selafinlayer.propertiesdialog.comboBox_values_method.currentIndex() == 0 :
            numnearest = self.getNearest([qgspointfromcanvas.x(),qgspointfromcanvas.y()])
            x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint([numnearest])[0]
            qgspointfromcanvas = self.selafinlayer.xform.transform( QgsPoint(x,y) )

        if not self.rubberband:
            self.createRubberband()
        self.rubberband.reset(QGis.Point)
        bool1, values = self.selafinlayer.identify(qgspointfromcanvas)
        strident = ''
        i = 0
        for name, value in values.items():
            self.selafinlayer.propertiesdialog.tableWidget_values.setItem(i, 1, QtGui.QTableWidgetItem(str(round(value,3))))
            i += 1
        self.rubberband.addPoint(qgspointfromcanvas)
        
        
    #****************************************************************************************************
    #************* Tools - temporal anf flow graph ***********************************************************
    #****************************************************************************************************
    
    #******************* Tools - temporal anf flow graph - clicktool*********************************************
    
    def computeGraphTemp(self,qgspointfromcanvas=None):
        """
        Activated with temporal graph tool - points from layer
        """
        if not self.rubberband:
            self.createRubberband()
        try:
            self.graphtodo = 0
            self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_2.currentIndex()
            if self.selectionmethod == 0:       #temporary point
                if not self.graphtempactive:
                    xformutil = self.selafinlayer.xform
                    qgspointtransformed = xformutil.transform(qgspointfromcanvas,QgsCoordinateTransform.ReverseTransform)
                    self.launchThread([[qgspointtransformed.x(),qgspointtransformed.y()]])
                
            elif self.selectionmethod == 1 :
                layer = iface.activeLayer()
                if not (layer.type() == 0 and layer.geometryType()==0):
                    QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a point vector layer"))
                else:
                    xformutil = QgsCoordinateTransform(self.selafinlayer.realCRS, layer.crs() )
                    self.rubberband.reset(QGis.Point)
                    self.selafinlayer.propertiesdialog.ax.cla()
                    self.selafinlayer.propertiesdialog.checkBox.setChecked(True)
                    layer = iface.activeLayer()
                    iter = layer.getFeatures()
                    geomfinal=[]
                    self.vectorlayerflowids = []
                    for i,feature in enumerate(iter):
                        try:
                            self.vectorlayerflowids.append(str(feature[0]))
                        except:
                            self.vectorlayerflowids.append(str(feature.id()))
                        geom=feature.geometry().asPoint()
                        temp1 = xformutil.transform(QgsPoint(geom[0],geom[1]),QgsCoordinateTransform.ReverseTransform)
                        geom=[temp1.x(),temp1.y()]
                        
                        geomfinal.append(geom)
                    if not self.graphtempactive:
                        self.launchThread(geomfinal)    
        except Exception , e :
            print str(e)

    def computeFlow(self):
        """
        Activated with flow graph tool
        """
        if not self.rubberband:
            self.createRubberband()
        self.dblclktemp = None
        self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
        self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"
        self.vectorlayerflowids = None
        self.graphtodo = 1
        self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_3.currentIndex()
        
        if self.selectionmethod in [0]:
            layer = iface.activeLayer()
            if not self.tool:
                self.tool = FlowMapTool(self.selafinlayer.canvas,self.selafinlayer.propertiesdialog.pushButton_flow)
            #Listeners of mouse
            self.connectTool()
            #init the mouse listener comportement and save the classic to restore it on quit
            self.selafinlayer.canvas.setMapTool(self.tool)
            #init the temp layer where the polyline is draw
            self.rubberband.reset(QGis.Line)
            #init the table where is saved the poyline
            self.pointstoDraw = []
            self.pointstoCal = []
            self.lastClicked = [[-9999999999.9,9999999999.9]]
            # The last valid line we drew to create a free-hand profile
            self.lastFreeHandPoints = []
        elif self.selectionmethod in [1,2]:
            layer = iface.activeLayer()
            if not (layer.type() == 0 and layer.geometryType()==1):
                QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a (poly)line vector layer"))
            elif self.selectionmethod==1 and len(layer.selectedFeatures())==0:
                QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a line in a (poly)line vector layer"))
            else:
                self.selafinlayer.propertiesdialog.ax2.cla()
                grid2 = self.selafinlayer.propertiesdialog.ax2.grid(color='0.5', linestyle='-', linewidth=0.5)
                self.selafinlayer.propertiesdialog.canvas2.draw()
                self.initclass1=[]
                self.selafinlayer.propertiesdialog.checkBox_7.setChecked(True)
                iter = layer.selectedFeatures()
                if self.selectionmethod == 2 or len(iter)==0:
                    iter = layer.getFeatures()
                geomfinal=[]
                self.vectorlayerflowids = []
                xformutil = QgsCoordinateTransform(self.selafinlayer.realCRS, layer.crs() )
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
                        qgspoint = xformutil.transform(QgsPoint(geom[0],geom[1]),QgsCoordinateTransform.ReverseTransform)
                        geomstemp.append([qgspoint.x(),qgspoint.y()])
                    geomfinal.append(geomstemp)
                    
                self.launchThread(geomfinal)
                

    # **************Flow map tool*******************************
                
    def connectTool(self):
        QObject.connect(self.tool, SIGNAL("moved"), self.moved)
        QObject.connect(self.tool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.connect(self.tool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.connect(self.tool, SIGNAL("doubleClicked"), self.doubleClicked)
        QObject.connect(self.tool, SIGNAL("deactivate"), self.deactivate)

    def deactivate(self):		#enable clean exit of the plugin
        QObject.disconnect(self.tool, SIGNAL("moved"), self.moved)
        QObject.disconnect(self.tool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.disconnect(self.tool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.disconnect(self.tool, SIGNAL("doubleClicked"), self.doubleClicked)

    def moved(self,position):			#draw the polyline on the temp layer (rubberband)
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                #Get mouse coords
                mapPos = self.selafinlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
                #Draw on temp layer
                self.rubberband.reset(QGis.Line)
                for i in range(0,len(self.pointstoDraw)):
                    self.rubberband.addPoint(QgsPoint(self.pointstoDraw[i][0],self.pointstoDraw[i][1]))
                self.rubberband.addPoint(QgsPoint(mapPos.x(),mapPos.y()))
        """
        if self.selectionmethod == 1:
            return
        """

    def rightClicked(self,position):	#used to quit the current action
        if self.selectionmethod == 0:
            mapPos = self.selafinlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            #if newPoints == self.lastClicked: return # sometimes a strange "double click" is given
            if len(self.pointstoDraw) > 0:
                self.pointstoDraw = []
                self.pointstoCal = []
                self.rubberband.reset(QGis.Line)
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
        mapPos = self.selafinlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
        newPoints = [[mapPos.x(), mapPos.y()]]

        if self.selectionmethod == 0:
            if newPoints == self.dblclktemp:
                self.dblclktemp = None
                if self.selafinlayer.propertiesdialog.comboBox_3.currentIndex() != 0:
                    self.cleaning()
                #return
            else :
                if len(self.pointstoDraw) == 0:
                    self.rubberband.reset(QGis.Line)
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
            mapPos = self.selafinlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            self.pointstoDraw += newPoints
            #convert points to pluginlayer crs
            xform = self.selafinlayer.xform
            pointstoDrawfinal=[]
            for point in self.pointstoDraw:
                qgspoint = xform.transform(QgsPoint(point[0],point[1]),QgsCoordinateTransform.ReverseTransform)
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

    #*****************Thread Launcher********************************

    def launchThread(self,geom):
        if self.graphtodo ==0:
            if not self.selafinlayer.propertiesdialog.checkBox.isChecked() and self.rubberband :
                self.rubberband.reset(QGis.Point)
            #self.initclass=InitGraphTemp()
            self.initclass = self.initclassgraphtemp
        elif self.graphtodo ==1:
            self.initclass=InitComputeFlow()
        self.initclass.status.connect(self.selafinlayer.propertiesdialog.textBrowser_2.append)
        self.initclass.error.connect(self.selafinlayer.propertiesdialog.errorMessage)
        self.initclass.emitpoint.connect(self.addPointRubberband)
        self.initclass.finished1.connect(self.workerFinished)
        
        if self.graphtodo ==0:
            self.initclass.start(self.selafinlayer,  geom)
            self.graphtempactive = True
            self.selafinlayer.propertiesdialog.pushButton_limni.setEnabled(False)
        elif self.graphtodo ==1:
            if self.selafinlayer.propertiesdialog.comboBox_flowmethod.currentIndex()==0:
                self.rubberband.reset(QGis.Line)
            elif self.selafinlayer.propertiesdialog.comboBox_flowmethod.currentIndex()==1:
                self.rubberband.reset(QGis.Point)
            #self.selafinlayer.propertiesdialog.textBrowser_main.append(str(ctime() + ' - Computing flow'))
            self.selafinlayer.propertiesdialog.normalMessage('Start computing flow')
            self.initclass.start(self.selafinlayer,geom)
            self.selafinlayer.propertiesdialog.pushButton_flow.setEnabled(False)
    
    
    def workerFinished(self,list1,list2,list3 = None):
    
        if self.graphtodo ==0:
            ax = self.selafinlayer.propertiesdialog.ax
            if not self.selafinlayer.propertiesdialog.checkBox.isChecked():
                ax.cla()
                if  len(self.graphtempdatac)>0:
                    for datacu in self.graphtempdatac:
                        datacu.hide()
                        datacu.disable()
                    self.graphtempdatac = []
        elif self.graphtodo ==1:
            ax = self.selafinlayer.propertiesdialog.ax2
            if not self.selafinlayer.propertiesdialog.checkBox_7.isChecked():
                ax.cla()
                if  len(self.graphflowdatac)>0:
                    for datacu in self.graphflowdatac:
                        datacu.hide()
                        datacu.disable()
                    self.graphflowdatac = []

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
        if self.graphtodo ==0:
            self.graphtempdatac.append(datacursor(test2,formatter="temps:{x:.0f}\nparametre:{y:.2f}".format,bbox=dict(fc='white'),arrowprops=dict(arrowstyle='->', fc='white', alpha=0.5)))
            self.selafinlayer.propertiesdialog.label_21.setText('Max : ' + str(maxtemp))
            self.selafinlayer.propertiesdialog.label_20.setText('Min : ' + str(mintemp))
            self.selafinlayer.propertiesdialog.canvas1.draw()
            if self.selectionmethod == 1 :
                self.selafinlayer.propertiesdialog.checkBox.setChecked(False)
            self.graphtempactive = False
            if self.selafinlayer.propertiesdialog.comboBox_2.currentIndex() != 0:
                self.selafinlayer.propertiesdialog.pushButton_limni.setEnabled(True)
        elif self.graphtodo ==1:
            self.graphflowdatac.append(datacursor(test2,formatter="temps:{x:.0f}\ndebit{y:.2f}".format,bbox=dict(fc='white'),arrowprops=dict(arrowstyle='->', fc='white', alpha=0.5)))
            self.selafinlayer.propertiesdialog.label_flow_resultmax.setText('Max : ' + str(maxtemp))
            self.selafinlayer.propertiesdialog.label__flow_resultmin.setText('Min : ' + str(mintemp))
            self.selafinlayer.propertiesdialog.canvas2.draw()
            if self.selafinlayer.propertiesdialog.comboBox_3.currentIndex() != 0:
                self.selafinlayer.propertiesdialog.normalMessage('Computing flow finished')
                self.selafinlayer.propertiesdialog.pushButton_flow.setEnabled(True)
            
    
    def copygraphclipboard(self):
        source = self.selafinlayer.propertiesdialog.sender()
        if source == self.selafinlayer.propertiesdialog.pushButton_graphtemp_pressepapier:
            ax = self.selafinlayer.propertiesdialog.ax
        elif source == self.selafinlayer.propertiesdialog.pushButton_4:
            ax = self.selafinlayer.propertiesdialog.ax2
        
        self.clipboard = QApplication.clipboard()
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
        

    def cleaning(self):     #used on right click
        self.selafinlayer.canvas.setMapTool(self.selafinlayer.propertiesdialog.maptooloriginal)
        iface.mainWindow().statusBar().showMessage( "" )
            
    def addPointRubberband(self,x,y):
        qgspoint = self.selafinlayer.xform.transform(QgsPoint(x,y))
        self.rubberband.addPoint(qgspoint)
        
        
    #****************************************************************************************************
    #************* Tools - compare***********************************************************
    #****************************************************************************************************
    
    def compareselafin(self):
        self.compareprocess = getCompareValue(self.selafinlayer)
        self.getCorrespondingParameters()
        self.selafinlayer.propertiesdialog.checkBox_6.setEnabled(True)
        
        
    def getCorrespondingParameters(self):
        for var in self.selafinlayer.parametres:
            for param in self.compareprocess.hydrauparsercompared.getVarnames() :
                if var[1] in param.strip()  :
                    self.selafinlayer.parametres[var[0]][3] = self.compareprocess.hydrauparsercompared.getVarnames().index(param)
                    break
                else:
                    self.selafinlayer.parametres[var[0]][3] = None
        self.selafinlayer.propertiesdialog.lineEdit.setText(str([[param[0],param[3]] for param in self.selafinlayer.parametres]))
        
    def reinitCorrespondingParameters(self):
        for i, var in enumerate(self.selafinlayer.parametres):
                self.selafinlayer.parametres[i][3] = i
        
    def compare1(self,int1):
        try:
            #if int1 == 2 :
            if self.selafinlayer.propertiesdialog.checkBox_6.checkState() == 2 :
                self.getCorrespondingParameters()
                #change signals
                try:
                    self.selafinlayer.updatevalue.disconnect(self.selafinlayer.updateSelafinValues1)
                    self.selafinlayer.updatevalue.connect(self.compareprocess.updateSelafinValue)
                except Exception, e:
                    pass
                self.initclassgraphtemp.compare = True
                self.selafinlayer.triinterp = None
                #desactive non matching parameters
                for i in range(len(self.selafinlayer.parametres)):
                    if self.selafinlayer.parametres[i][3] == None:
                        self.selafinlayer.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsSelectable)
                self.compareprocess.comparetime = None
                self.selafinlayer.forcerefresh = True
                self.selafinlayer.updateSelafinValues()
                self.selafinlayer.triggerRepaint()
            elif self.selafinlayer.propertiesdialog.checkBox_6.checkState() == 0 :
                #change signals
                try:
                    self.selafinlayer.updatevalue.disconnect(self.compareprocess.updateSelafinValue)
                    self.selafinlayer.updatevalue.connect(self.selafinlayer.updateSelafinValues1)
                except Exception, e:
                    pass
                self.initclassgraphtemp.compare = False
                self.selafinlayer.triinterp = None
                self.selafinlayer.forcerefresh = True
                self.reinitCorrespondingParameters()
                self.selafinlayer.propertiesdialog.populatecombobox_param()
                self.selafinlayer.propertiesdialog.setTreeWidgetIndex(self.selafinlayer.propertiesdialog.treeWidget_parameters,0,self.selafinlayer.param_displayed)
                self.selafinlayer.updateSelafinValues()
                self.selafinlayer.triggerRepaint()
        except Exception, e:
            print str(e)
        
    #****************************************************************************************************
    #************* Tools - Movie***********************************************************
    #****************************************************************************************************

    def makeAnimation(self):
        self.initclass = PostTelemacAnimation(self.selafinlayer)
        self.initclass.makeFilm()

    def filmEstimateLenght(self,int=None):
        lenght = (self.selafinlayer.propertiesdialog.spinBox_3.value() - self.selafinlayer.propertiesdialog.spinBox_2.value())/self.selafinlayer.propertiesdialog.spinBox_4.value()/self.selafinlayer.propertiesdialog.spinBox_fps.value()
        self.selafinlayer.propertiesdialog.label_tempsvideo.setText(str(lenght))
        
        
    #****************************************************************************************************
    #************* Tools - max res ***********************************************************
    #****************************************************************************************************
    def calculMaxRes(self):
        self.initclass=initRunGetMax()
        self.initclass.status.connect(self.selafinlayer.propertiesdialog.textBrowser_2.append)
        self.initclass.finished1.connect(self.chargerSelafin)
        self.initclass.start(self.selafinlayer,
                             self.selafinlayer.propertiesdialog.checkBox_11.isChecked(),
                             self.selafinlayer.propertiesdialog.checkBox_11.isChecked(),
                             self.selafinlayer.propertiesdialog.doubleSpinBox_4.value() if self.selafinlayer.propertiesdialog.checkBox_9.isChecked() else -1,
                             self.selafinlayer.propertiesdialog.doubleSpinBox_5.value() if self.selafinlayer.propertiesdialog.checkBox_10.isChecked() else -1)
        
        
        

    def chargerSelafin(self, path):
        if path and self.selafinlayer.propertiesdialog.checkBox_8.isChecked():
            slf = QgsPluginLayerRegistry.instance().pluginLayerType('selafin_viewer').createLayer()
            #slf.setRealCrs(iface.mapCanvas().mapSettings().destinationCrs()) 
            slf.setRealCrs(self.selafinlayer.crs())
            slf.load_selafin(path)
            QgsMapLayerRegistry.instance().addMapLayer(slf)
        
        
    #****************************************************************************************************
    #************* Tools - 2shape***********************************************************
    #****************************************************************************************************
        
    def create_points(self):
        #Mise en forme des donnees d entree
        meshx, meshy = self.selafinlayer.hydrauparser.getMesh()
        donnees_d_entree = {'traitementarriereplan' : 0,
                                  'pathselafin' : os.path.normpath(self.selafinlayer.hydraufilepath),
                                  'temps' : self.selafinlayer.time_displayed,
                                  'pasdespace' : self.selafinlayer.propertiesdialog.spinBox.value(),
                                  'fichier_point_avec_vecteur_vitesse' : self.selafinlayer.propertiesdialog.checkBox_5.isChecked(),
                                  'paramvalueX' : self.selafinlayer.parametrevx if self.selafinlayer.propertiesdialog.checkBox_5.isChecked() else None,
                                  'paramvalueY' : self.selafinlayer.parametrevy if self.selafinlayer.propertiesdialog.checkBox_5.isChecked() else None,
                                  'crs' : self.selafinlayer.crs().authid(),
                                  'forcage_attribut_fichier_de_sortie' : "",
                                  'fichierdesortie_point' : "",
                                  'mesh' : np.array(self.selafinlayer.hydrauparser.getIkle()),
                                  'x' : meshx,
                                  'y' : meshy,
                                  'ztri' : [self.selafinlayer.hydrauparser.getValues(self.selafinlayer.time_displayed)[i] for i in range(len([param for param in self.selafinlayer.parametres if not param[2]]))]}
                                  
        donnees_d_entree['champs'] = QgsFields()
        for i,name in enumerate(self.selafinlayer.hydrauparser.getVarnames()):
            donnees_d_entree['champs'].append(QgsField(str(name.strip()).translate(None, "?,!.;"),   QVariant.Double))
                  
                                  
        if donnees_d_entree['forcage_attribut_fichier_de_sortie']=="":
            if donnees_d_entree['pasdespace']==0:
                donnees_d_entree['pathshp'] =os.path.join(os.path.dirname(donnees_d_entree['pathselafin']),
                                                                                           os.path.basename(donnees_d_entree['pathselafin']).split('.')[0]
                                                                                           +"_points_t_"+str(int(donnees_d_entree['temps']))+str('.shp'))  
            else:
                donnees_d_entree['pathshp']=os.path.join(os.path.dirname(donnees_d_entree['pathselafin']),
                                                                                           os.path.basename(donnees_d_entree['pathselafin']).split('.')[0]
                                                                                           +"_points_"+str(int(donnees_d_entree['pasdespace']))
                                                                                           +"m_t_"+str(int(donnees_d_entree['temps']))+str('.shp'))  
        else:
                donnees_d_entree['pathshp']=os.path.join(os.path.dirname(donnees_d_entree['pathselafin']),
                                                                                           os.path.basename(donnees_d_entree['pathselafin']).split('.')[0]
                                                                                           +"_"+str(donnees_d_entree['forcage_attribut_fichier_de_sortie'])
                                                                                           +str('.shp'))
        #Verifie que le shp n existe pas
        if self.isFileLocked(donnees_d_entree['pathshp'] , True):
            self.selafinlayer.propertiesdialog.errorMessage(self.tr(" - initialization - Error : Shapefile already loaded !!"))
            #pass
        else:
            #Lancement du thread *************************************************************************
            self.selafinlayer.propertiesdialog.normalMessage(self.tr("2Shape - point creation launched - watch progress on log tab"))
            worker = Worker_pts(donnees_d_entree)
            thread = QtCore.QThread()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.status.connect(self.selafinlayer.propertiesdialog.textBrowser_2.append)
            worker.error.connect(self.selafinlayer.propertiesdialog.errorMessage)
            worker.finished.connect(self.workershapePointFinished)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            worker.finished.connect(thread.quit)
            thread.start()
            self.thread = thread
            self.worker = worker
        

    def create_shp(self):
        self.initclass=InitSelafinContour2Shp()
        self.initclass.status.connect(self.selafinlayer.propertiesdialog.textBrowser_2.append)
        self.initclass.finished1.connect(self.workershapeFinished)
        self.selafinlayer.propertiesdialog.normalMessage(self.tr("2Shape - coutour creation launched - watch progress on log tab"))
        self.initclass.start(0,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                         os.path.normpath(self.selafinlayer.hydraufilepath),                 #path to selafin file
                         int(self.selafinlayer.time_displayed),                            #time to process (selafin time iteration)
                         self.selafinlayer.parametres[self.selafinlayer.param_displayed][1],                     #parameter to process name (string) or id (int)
                         self.selafinlayer.lvl_contour,                       #levels to create
                         self.selafinlayer.crs().authid(),      #selafin crs
                         self.selafinlayer.propertiesdialog.pushButton_contourcrs.text() if self.selafinlayer.propertiesdialog.checkBox_contourcrs.isChecked() else None,   #if no none, specify crs of output file
                         False,                #quickprocess option - don't make ring
                          str(self.selafinlayer.propertiesdialog.lineEdit_contourname.text()),           #change generic outputname to specific one
                          None,         #if not none, create shp in this directory
                         self.selafinlayer.value,          #force value for plugin
                          None)
        
        

            
    def create_shp_maillage(self):
        self.initclass=InitSelafinMesh2Shp()
        self.initclass.status.connect(self.selafinlayer.propertiesdialog.textBrowser_2.append)
        if self.selafinlayer.propertiesdialog.checkBox_3.isChecked():
            self.initclass.finished1.connect(self.workerFinishedHillshade)
        else:
            self.initclass.finished1.connect(self.workershapeFinished)
        self.selafinlayer.propertiesdialog.normalMessage(self.tr("2Shape - mesh creation launched - watch progress on log tab"))
        self.initclass.start(0,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                         os.path.normpath(self.selafinlayer.hydraufilepath),                 #path to selafin file
                         int(self.selafinlayer.time_displayed),                            #time to process (selafin time iteration)
                         str(self.getParameterName('BATHYMETRIE')[0]) if self.selafinlayer.propertiesdialog.checkBox_3.isChecked() else None,     #parameter to process name (string) or id (int)
                         self.selafinlayer.propertiesdialog.doubleSpinBox.value(),                 #z amplify
                         self.selafinlayer.propertiesdialog.doubleSpinBox_3.value(),                    #azimuth for hillshade
                         self.selafinlayer.propertiesdialog.doubleSpinBox_2.value(),                    #zenith for hillshade
                         self.selafinlayer.crs().authid(),      #selafin crs
                         self.selafinlayer.propertiesdialog.pushButton_7.text() if self.selafinlayer.propertiesdialog.checkBox_2.isChecked() else None,   #if no none, specify crs of output file
                          None,           #change generic outputname to specific one
                          None,         #if not none, create shp in this directory
                          None)
            
            
    def workershapeFinished(self,strpath):
        vlayer = QgsVectorLayer( strpath, os.path.basename(strpath).split('.')[0],"ogr")
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)
        #self.selafinlayer.propertiesdialog.textBrowser_main.append(ctime() + " - "+ str(os.path.basename(strpath).split('.')[0]) + self.tr(" created"))
        self.selafinlayer.propertiesdialog.normalMessage(str(os.path.basename(strpath).split('.')[0]) + self.tr(" created"))
        
    def workershapePointFinished(self,strpath):
        vlayer = QgsVectorLayer( strpath, os.path.basename(strpath).split('.')[0],"ogr")
        pathpointvelocityqml = os.path.join(os.path.dirname(__file__), '..','styles', '00_Points_Vmax_vecteur_champ_vectoriel.qml')
        vlayer.loadNamedStyle(pathpointvelocityqml)
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)
        #self.selafinlayer.propertiesdialog.textBrowser_main.append(ctime() + " - "+ str(os.path.basename(strpath).split('.')[0]) + self.tr(" created"))
        self.selafinlayer.propertiesdialog.normalMessage(str(os.path.basename(strpath).split('.')[0]) + self.tr(" created"))
        

    def workerFinishedHillshade(self,strpath):
        vlayer = QgsVectorLayer( strpath, os.path.basename(strpath).split('.')[0],"ogr")
        pathhillshadeqml = os.path.join(os.path.dirname(__file__), '..','styles', '00_Polygon_Hillshade.qml')
        vlayer.loadNamedStyle(pathhillshadeqml)
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)
        #self.selafinlayer.propertiesdialog.textBrowser_main.append(ctime() + " - "+ str(os.path.basename(strpath).split('.')[0]) + self.tr(" created"))
        self.selafinlayer.propertiesdialog.normalMessage(str(os.path.basename(strpath).split('.')[0]) + self.tr(" created"))

    


    #****************************************************************************************************
    #************* Basic functions***********************************************************
    #****************************************************************************************************
        
    def createRubberband(self):
        self.rubberband = QgsRubberBand(self.selafinlayer.canvas, QGis.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QColor(Qt.red))
        
        
        
    def isFileLocked(self,file, readLockCheck=False):
        '''
        Checks to see if a file is locked. Performs three checks
            1. Checks if the file even exists
            2. Attempts to open the file for reading. This will determine if the file has a write lock.
                Write locks occur when the file is being edited or copied to, e.g. a file copy destination
            3. If the readLockCheck parameter is True, attempts to rename the file. If this fails the
                file is open by some other process for reading. The file can be read, but not written to
                or deleted.
        @param file:
        @param readLockCheck:
        '''
        if(not(os.path.exists(file))):
            return False
        try:
            f = open(file, 'r')
            f.close()
        except IOError:
            return True
       
        if(readLockCheck):
            lockFile = file + ".lckchk"
            if(os.path.exists(lockFile)):
                os.remove(lockFile)
            try:
                os.rename(file, lockFile)
                time.sleep(1)
                os.rename(lockFile, file)
            except WindowsError:
                return True
              
        return False   
        
    def getParameterName(self,param):
        trouve = False
        f = open(os.path.join(os.path.dirname(__file__),'..', 'config','parametres.txt'), 'r')
        for line in f:
            #print str(param) + ' ' + str(line.split("=")[0])
            if  param == line.split("=")[0]:
                tabtemp=[]
                for txt in line.split("=")[1].split("\n")[0].split(";"):
                    tabtemp.append(str(txt))
                for paramtemp in self.selafinlayer.parametres:
                    #print str(paramtemp[1]) + ' ' +str(tabtemp)
                    if paramtemp[1] in tabtemp:
                        trouve = True
                        return paramtemp
                if not trouve:
                    return None
        if not trouve:
            return None
            
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('PostTelemacUtils', message, None, QApplication.UnicodeUTF8)
        
    ""
        
    def getNearest(self,pointfromcanvas):
        """
        Get the nearest point in selafin mesh
        point is an array [x,y]
        return num of selafin MESH point
        """
        qgspoint= self.selafinlayer.xform.transform(QgsPoint(pointfromcanvas[0],pointfromcanvas[1]),QgsCoordinateTransform.ReverseTransform)
        point1 = [[qgspoint.x(),qgspoint.y()]]
        if not self.skdtree :
            meshx, meshy = self.selafinlayer.hydrauparser.getMesh()
            self.arraymesh = np.array([[meshx[i], meshy[i] ] for i in range(self.selafinlayer.hydrauparser.pointcount) ])
            self.skdtree = cKDTree(self.arraymesh,leafsize=100)
        numfinal = self.skdtree.query(point1,k=1)[1][0]
        return numfinal
        
        
    
class ThreadLaucnher(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = None
        self.worker = None
        self.processtype = 0
        #self.selafin = selafin
        #self.graphtemp = graphTemp(selafin)
        self.compare = False
        self.method = None

    def start(self, selafin, method,
                 qgspoints ):
                 
        #Launch worker
        self.thread = QtCore.QThread()
        self.worker = graphTemp(selafin, qgspoints,self.compare)
        #self.graphtemp.points = qgspoints
        #self.worker = self.graphtemp
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.createGraphTemp)
        self.worker.status.connect(self.writeOutput)
        self.worker.error.connect(self.raiseError)
        self.worker.emitpoint.connect(self.emitPoint)
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

        
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
