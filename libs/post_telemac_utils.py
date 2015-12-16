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
#import libs
from posttelemac_util_animation import *
from posttelemac_util_extractshp import *
from posttelemac_util_extractmesh import *
from posttelemac_util_extractpts import *
from posttelemac_util_graphtemp import *
from posttelemac_util_flow import *
from posttelemac_util_get_max import *


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
        self.ouvrages = None                     #class culvert
        self.digues = None                       #class digue
        self.conlim = None                       #class conlim
        self.diguepoint  = None                 #class levee point
        self.digueline = None                 #class levee line
        self.graphtempdatac = []
        self.graphflowdatac = []
        
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
        f = open(os.path.join(os.path.dirname(__file__),'..', 'parametres.txt'), 'r')
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
        return QCoreApplication.translate('PostTelemacUtils', message)
        
    #****************************************************************************************************
    #************* Tools - 2shape***********************************************************
    #****************************************************************************************************
        
    def create_points(self):
        #Mise en forme des donnees d entree
        donnees_d_entree = {'traitementarriereplan' : 0,
                                  'pathselafin' : os.path.normpath(self.selafinlayer.fname),
                                  'temps' : self.selafinlayer.temps_gachette,
                                  'pasdespace' : self.selafinlayer.propertiesdialog.spinBox.value(),
                                  'fichier_point_avec_vecteur_vitesse' : self.selafinlayer.propertiesdialog.checkBox_5.isChecked(),
                                  'paramvalueX' : self.selafinlayer.parametrevx if self.selafinlayer.propertiesdialog.checkBox_5.isChecked() else None,
                                  'paramvalueY' : self.selafinlayer.parametrevy if self.selafinlayer.propertiesdialog.checkBox_5.isChecked() else None,
                                  'crs' : self.selafinlayer.crs().authid(),
                                  'forcage_attribut_fichier_de_sortie' : "",
                                  'fichierdesortie_point' : "",
                                  'mesh' : np.array(self.selafinlayer.slf.IKLE3),
                                  'x' : self.selafinlayer.slf.MESHX,
                                  'y' : self.selafinlayer.slf.MESHY,
                                  'ztri' : [self.selafinlayer.slf.getVALUES(self.selafinlayer.temps_gachette)[i] for i in range(len([param for param in self.selafinlayer.parametres if not param[2]]))]}
                                  
        donnees_d_entree['champs'] = QgsFields()
        for i,name in enumerate(self.selafinlayer.slf.VARNAMES):
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
            #self.selafinlayer.propertiesdialog.textBrowser_main.append(str(ctime()) + self.tr(" - initialization - Error : Shapefile already loaded !!"))
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
                         os.path.normpath(self.selafinlayer.fname),                 #path to selafin file
                         int(self.selafinlayer.temps_gachette),                            #time to process (selafin time iteration)
                         self.selafinlayer.parametres[self.selafinlayer.param_gachette][1],                     #parameter to process name (string) or id (int)
                         self.selafinlayer.lvl_gachette,                       #levels to create
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
                         os.path.normpath(self.selafinlayer.fname),                 #path to selafin file
                         int(self.selafinlayer.temps_gachette),                            #time to process (selafin time iteration)
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
    #************* Tools - temporal anf flow graph ***********************************************************
    #****************************************************************************************************
    
    #******************* Tools - temporal anf flow graph - clicktool*********************************************
    
    def valeurs_click(self,qgspoint):
        if not self.rubberband:
            self.createRubberband()
        self.rubberband.reset(QGis.Point)
        self.selafinlayer.propertiesdialog.textBrowser_3.clear()
        self.selafinlayer.propertiesdialog.textBrowser_3.append(str(self.selafinlayer.identify(qgspoint,True)))
        self.rubberband.addPoint(qgspoint)
        
        
    def graphtemp_click(self,qgspoint):
        if not self.graphtempactive:
            if not self.rubberband:
                self.createRubberband()
            self.graphtodo = 0
            self.selectionmethod = 0
            self.launchThread([[qgspoint.x(),qgspoint.y()]])
    
    
    
    #*************** Button call ***********
    """
    def get_itemname(self):
        getSelected = self.selafinlayer.propertiesdialog.treeWidget_utils.selectedItems()
        try:
            baseNode = getSelected[0]
            position = [self.selafinlayer.propertiesdialog.treeWidget_utils.indexFromItem(baseNode).parent().row(),self.selafinlayer.propertiesdialog.treeWidget_utils.indexFromItem(baseNode).row()]
            indextabtemp=[index[0] for index in self.selafinlayer.propertiesdialog.treewidgettoolsindextab ]
            itemname = self.selafinlayer.propertiesdialog.treewidgettoolsindextab[indextabtemp.index(position)][2]
        except Exception, e:
            itemname = None
        return itemname
    """
    
    def computeGraph(self):
        if not self.rubberband:
            self.createRubberband()
        try:
            self.graphtodo = 0
            self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_2.currentIndex()
            """
            if self.get_itemname() =='Temporal graph':
                self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_2.currentIndex()
            elif self.get_itemname() =='Flow graph' :
                self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_3.currentIndex()
            """
            if self.selectionmethod == 0:
                self.rubberband.reset(QGis.Point)
                self.selafinlayer.canvas.setMapTool(self.clickTool)
                self.clickTool.canvasClicked.connect(self.graphtemp_click)
            elif self.selectionmethod == 1 :
                layer = iface.activeLayer()
                if not (layer.type() == 0 and layer.geometryType()==0):
                    QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a point vector layer"))
                else:
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
                        geom=[geom[0],geom[1]]
                        geomfinal.append(geom)
                    if not self.graphtempactive:
                        self.launchThread(geomfinal)    
        except Exception , e :
            print str(e)

     

     
     
    def computeFlow(self):
        if not self.rubberband:
            self.createRubberband()
        #source = self.selafinlayer.propertiesdialog.sender()
        self.dblclktemp = None
        self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
        self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"
        self.vectorlayerflowids = None
        self.graphtodo = 1
        self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_3.currentIndex()
        """
        if self.get_itemname() =='Temporal graph':
            self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_2.currentIndex()
        elif self.get_itemname() =='Flow graph' :
            self.selectionmethod = self.selafinlayer.propertiesdialog.comboBox_3.currentIndex()
        """
        if self.selectionmethod in [0]:
            layer = iface.activeLayer()
            if self.selectionmethod == 1 and not (layer.type() == 0 and layer.geometryType()==1):
                QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a (poly)line vector layer"))
            else:
                if not self.tool:
                    self.tool = FlowMapTool(self.selafinlayer.canvas,self.selafinlayer.propertiesdialog.pushButton_flow)
                    #self.tool = FlowMapTool(self.selafinlayer.canvas,None)
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
                #layer = iface.activeLayer()
                iter = layer.selectedFeatures()
                if self.selectionmethod == 2 or len(iter)==0:
                    iter = layer.getFeatures()
                geomfinal=[]
                self.vectorlayerflowids = []
                for i,feature in enumerate(iter):
                    try:
                        self.vectorlayerflowids.append(str(feature[0]))
                    except:
                        self.vectorlayerflowids.append(str(feature.id()))
                    geoms=feature.geometry().asPolyline()
                    geoms=[[geom[0],geom[1]] for geom in geoms]
                    geoms = geoms+[geoms[-1]]
                    geomfinal.append(geoms)
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
            #launch analyses
            self.launchThread([self.pointstoDraw])
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
            self.initclass=InitGraphTemp()
        elif self.graphtodo ==1:
            self.initclass=InitComputeFlow()
        self.initclass.status.connect(self.selafinlayer.propertiesdialog.textBrowser_2.append)
        self.initclass.error.connect(self.selafinlayer.propertiesdialog.errorMessage)
        self.initclass.emitpoint.connect(self.addPointRubberband)
        self.initclass.finished1.connect(self.workerFinished)
        if self.graphtodo ==0:
            self.initclass.start(geom,self.selafinlayer)
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
                #self.selafinlayer.propertiesdialog.pushButton_flow.setCheckable(True)
                #self.selafinlayer.propertiesdialog.textBrowser_main.append(str(ctime() + ' - Computing flow finished'))
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
        self.rubberband.addPoint(QgsPoint(x,y))
        
        
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
        self.initclass.start(self.selafinlayer.fname,self.selafinlayer.fname.split('.')[0] + '_Max.res',False,False)
        
        
        

    def chargerSelafin(self, path):
        if path and self.selafinlayer.propertiesdialog.checkBox_8.isChecked():
            slf = QgsPluginLayerRegistry.instance().pluginLayerType('selafin_viewer').createLayer()
            slf.setCrs(iface.mapCanvas().mapSettings().destinationCrs()) 
            slf.load_selafin(path)
            QgsMapLayerRegistry.instance().addMapLayer(slf)
            
            
    #****************************************************************************************************
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('PostTelemacUtils', message, None, QApplication.UnicodeUTF8)
            
    
        
        
