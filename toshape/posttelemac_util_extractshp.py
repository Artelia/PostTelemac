from qgis.core import *
from qgis.gui import *
from qgis.utils import *
try:
    from processing.core.GeoAlgorithmExecutionException import  GeoAlgorithmExecutionException
    from processing.tools.vector import VectorWriter
except Exception, e :
    print str(e)
#import numpy
import numpy as np
#import matplotlib
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib import tri
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui

#imports divers
import threading
from time import ctime
import math
from os import path
#from shapely.geometry import Polygon
import sys
import os.path
"""
try:
    #sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'..','libs_telemac'))
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'..','libs_telemac'))
    #import telemac python
    #from utils.files import getFileContent
    #from parsers.parserSortie import getValueHistorySortie
    #from parsers.parserSELAFIN import getValueHistorySLF,   getValuePolylineSLF,subsetVariablesSLF
    #from parsers.parserStrings import parseArrayPaires
    from parsers.parserSELAFIN import SELAFIN
    #print 'import '  + os.path.join(os.path.dirname(os.path.realpath(__file__)),'libs_telemac')


except Exception, e :
    print str(e)
    print 'import '  + os.path.join(os.path.dirname(os.path.realpath(__file__)),'libs_telemac')
"""

from ..posttelemacparsers.posttelemac_selafin_parser import *
debug = False



#*************************************************************************

def isFileLocked(file, readLockCheck=False):
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

def workerFinished(str1):
    #progress.setText(str(ctime()) +" - Fin du thread - Chargement du fichier resultat")
    vlayer = QgsVectorLayer( str1, os.path.basename(str1).split('.')[0],"ogr")
    QgsMapLayerRegistry.instance().addMapLayer(vlayer)



#*********************************************************************************************
#*************** Classe de traitement **********************************************************
#********************************************************************************************

        
class SelafinContour2Shp(QtCore.QObject):
    
    def __init__(self,
                 processtype,                 #0 : thread inside qgis plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                 selafinfilepath,                 #path to selafin file
                 time,                            #time to process (selafin time in iteration)
                 parameter,                     #parameter to process name (string) or id (int)
                 levels,                       #levels to create
                 selafincrs = 'EPSG:2154',      #selafin crs
                 selafintransformedcrs = None,   #if no none, specify crs of output file
                 quickprocessing = False,                #quickprocess option - don't make ring
                 outputshpname = None,           #change generic outputname to specific one
                 outputshppath = None,         #if not none, create shp in this directory
                 forcedvalue = None,          #force value for plugin
                 outputprocessing = None):      #case of use in modeler
        
        QtCore.QObject.__init__(self)
        #donnees process
        self.processtype = processtype
        self.quickprocessing = quickprocessing
        #donnes delafin
        self.parserhydrau = PostTelemacSelafinParser()
        self.parserhydrau.loadHydrauFile(os.path.normpath(selafinfilepath))
        
        #slf = SELAFIN(os.path.normpath(selafinfilepath))
        slf = self.parserhydrau.hydraufile
        """
        self.slf_x = slf.MESHX
        self.slf_y = slf.MESHY
        self.slf_mesh = np.array(slf.IKLE3)
        """
        self.slf_x, self.slf_y  = self.parserhydrau.getMesh()
        self.slf_mesh  = np.array( self.parserhydrau.getIkle() )

        if self.processtype==0:
            #self.slf_param = [0,parameter]
            #self.slf_param = [parameter,self.parserhydrau.getVarnames()[parameter].strip()]
            self.slf_param = [parameter,parameter]
        else:
            #self.slf_param = [parameter,slf.VARNAMES[parameter].strip()]
            self.slf_param = [parameter,self.parserhydrau.getVarnames()[parameter].strip()]
        
        
            
        #slf_time = [time,slf.tags["times"][time]]
        slf_time = [time,self.parserhydrau.getTimes()[time]]
        
        if  forcedvalue is None:
            #self.slf_value = slf.getVALUES(slf_time[0])[self.slf_param[0]]
            self.slf_value = self.parserhydrau.getValues(slf_time[0])[self.slf_param[0]]
        else:
            self.slf_value = forcedvalue
            
        #donnees shp
        champs = QgsFields()
        champs.append(QgsField("min",   QVariant.Double))
        champs.append(QgsField("max",   QVariant.Double))
        if self.quickprocessing:
            champs.append(QgsField("int",   QVariant.String))
        
        #donnees shp - outside qgis
        if not outputshpname :
            outputshpname = (os.path.basename(os.path.normpath(selafinfilepath)).split('.')[0]
                             +"_"+str(self.slf_param[1]).translate(None, "?,!.;")
                             +"_t_"+str(slf_time[1])
                             +str('.shp'))
        else:
            outputshpname = (os.path.basename(os.path.normpath(selafinfilepath)).split('.')[0] 
                             + "_"+str(outputshpname)
                             +str('.shp'))
        if  not outputshppath:
            outputshppath=os.path.dirname(os.path.normpath(selafinfilepath))
        self.outputshpfile=os.path.join(outputshppath,outputshpname)
        
        if isFileLocked(self.outputshpfile , True):
            self.raiseError(str(ctime()) + " - Initialisation - Erreur : \
                                    Fichier shape deja charge !!")
        
        
        self.slf_crs = selafincrs
        if  selafintransformedcrs:
            self.slf_shpcrs = selafintransformedcrs
            self.xform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(str(self.slf_crs)),
                                                QgsCoordinateReferenceSystem(str(self.slf_shpcrs)))
        else:
            self.slf_shpcrs = self.slf_crs
            self.xform = None
        
        if self.processtype in [0,1,3,4]:
            self.writerw_shp  = QgsVectorFileWriter(self.outputshpfile, None ,    
                                                                 champs,   
                                                                 QGis.WKBMultiPolygon, 
                                                                 QgsCoordinateReferenceSystem(self.slf_shpcrs ), 
                                                                 "ESRI Shapefile")
            
            
            
        #donnees shp - processing result
        try:
            if self.processtype in [2,3]:
                self.writerw_process  = VectorWriter(outputprocessing, None ,    
                                                            champs,   
                                                            QGis.WKBMultiPolygon, 
                                                            QgsCoordinateReferenceSystem(str(self.slf_shpcrs ) ), 
                                                            "ESRI Shapefile")
        except Exception, e:
            pass
        

        #donnees matplotlib
        self.levels = levels


    def createShp(self):


            #******** Informations de lancement de la tache  *****************************************************
            fet = QgsFeature()
            strtxt=(str(ctime()) + ' - creation shapefile :'+'\n' +str(self.outputshpfile))
            self.writeOutput(strtxt)
            
            #******** Iteration sur les  niveaux *******************************************************************
            for lvltemp in range(len(self.levels)-1):
                lvltemp1=[self.levels[lvltemp],self.levels[lvltemp+1]]
                strtxt = (str(ctime()) + " - "+str(self.slf_param[1] )+ " - lvl "+str(lvltemp1) + " - Matplotlib integration")
                self.writeOutput(strtxt)
                triplotcontourf = plt.tricontourf(self.slf_x,self.slf_y,self.slf_mesh,self.slf_value,lvltemp1)                   #l'outil de matplotlib qui cree la triangulation
                
                # Iteration sur les contours fournis par triplotcontourf  et inclusion des outers et inners dans une table temporaire**************
                vlInnerTemp,vlOuterTemp,vlOuterTempIndex = self.createInnerOutertempLayer(triplotcontourf)
                
                #*********** Debut du traitement des iles************************************************************
                strtxt = (str(ctime()) + " - "+str(self.slf_param[1]  ) + " - lvl "+str(lvltemp1) + " - Ring process")
                self.writeOutput(strtxt)
                

                allfeatures2 = {feature.id(): feature for (feature) in vlOuterTemp.getFeatures()}  #creation d'un index spatial des inners pour aller plus vite
                map(vlOuterTempIndex.insertFeature, allfeatures2.values())
                

                if self.quickprocessing:
                    for f1 in vlInnerTemp.getFeatures(): 
                        fet.setGeometry(f1.geometry())  
                        fet.setAttributes([lvltemp1[0],lvltemp1[1], 'False' ])
                        if self.processtype in[0,2] :
                            self.writerw_shp.addFeature(  fet ) 
                        if self.processtype in [1,2] :
                            self.writerw_process.addFeature(  fet ) 
                    for f2 in vlOuterTemp.getFeatures():
                        fet.setGeometry(f2.geometry())  
                        fet.setAttributes([lvltemp1[0],lvltemp1[1], 'True' ])
                        if self.processtype in[0,2] :
                            self.writerw_shp.addFeature(  fet ) 
                        if self.processtype in [1,2] :
                            self.writerw_process.addFeature(  fet ) 
                

                else:
                    counttotal = int(vlInnerTemp.featureCount())
                    #*Iteration sur tous les outer ***********************************************************************
                    for f1 in vlInnerTemp.getFeatures():
                        if int(f1.id())%50 == 0:
                            self.verboseOutput(self.slf_param[1],lvltemp1,f1.id(),counttotal)
                        fet = self.InsertRinginFeature(f1,allfeatures2,vlOuterTempIndex,lvltemp1,counttotal)

                        if self.processtype in [0,1,3,4] :
                            self.writerw_shp.addFeature(  fet ) 
                        if self.processtype in [2,3] :
                            self.writerw_process.addFeature(  fet ) 

            
            #Clear thongs
            vlInnerTemp = None
            vlOuterTemp = None
            pr1 = None
            pr2 = None
            vlOuterTempIndex = None
            if self.processtype in [0,1,3,4] :
                del self.writerw_shp 
            if self.processtype in [2,3] :
                del self.writerw_process 

            #Emit finish
            if self.processtype in [0,1] :
                self.finished.emit(self.outputshpfile)
            if self.processtype in [2,3]:
               t =  workerFinished(self.outputshpfile)
            if self.processtype in [4]:
                self.writeOutput('Process finished - '+str(self.outputshpfile))
            
    def verboseOutput(self,param,lvl,geomelem=None,geomtot=None,ileelem=None,iletot=None):
        strtxt = str(ctime()) + " - "+str(param ) +" - lvl : " + str(lvl) 
        if geomelem:
            strtxt = strtxt +" - geom : "+str(geomelem)+"/"+str(geomtot )
        if ileelem:
            strtxt = strtxt + " - ring : "+str(ileelem)+"/"+str(iletot)
        self.writeOutput(strtxt)
        
            
    def writeOutput(self,str1):
        if self.processtype in [0,1,2,3]: 
            self.status.emit(str(str1))
        elif self.processtype ==4 : print str1
        
    def raiseError(self,str1):
        self.error.emit(str(str1))

            
    def createInnerOutertempLayer(self,triplotcontourf):
        fet = QgsFeature()
        for collection in triplotcontourf.collections:
            vl1temp1 = QgsVectorLayer("Multipolygon?crs=" + str(self.slf_crs), "temporary_poly_outer ", "memory")
            pr1 = vl1temp1.dataProvider()
            index1 = QgsSpatialIndex()
            vl2temp1 = QgsVectorLayer("Multipolygon?crs=" + str(self.slf_crs), "temporary_poly_inner " , "memory")
            pr2 = vl2temp1.dataProvider()                
            index2 = QgsSpatialIndex()
            vl1temp1.startEditing()
            vl2temp1.startEditing()
            for path in collection.get_paths():
                for polygon in path.to_polygons(): 
                    if len(polygon)>=3 : 
                        fet.setGeometry(self.get_outerinner(polygon)[0])
                        fet.setAttributes([])
                        
                        if  ( np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 >0 ):
                            pr1.addFeatures( [ fet ] )
                            vl1temp1.commitChanges() 
                        else :
                            pr2.addFeatures( [ fet ] )
                            vl2temp1.commitChanges() 
        return (vl1temp1,vl2temp1,index2)
        
    def get_outerinner(self,geom1):
        geomtemp1 = []
        if (str(geom1.__class__) == "<class 'qgis.core.QgsGeometry'>" 
           or str(geom1.__class__) == "<class 'qgis._core.QgsGeometry'>"):
            geompolygon = geom1.asPolygon()
            for i in range(len(geompolygon)):
                geomtemp2 = []
                for j in range(len(geompolygon[i])):
                    geomtemp2.append(QgsPoint(geompolygon[i][j][0],geompolygon[i][j][1]))
                geomcheck = QgsGeometry.fromPolygon([geomtemp2])
                if len(geomcheck.validateGeometry())!=0:
                    geomcheck  = geomcheck.buffer(0.01,5)
                geomtemp1.append( geomcheck)
        else :
            geomtemp2 = []
            for i in range(len(geom1)):
                geomtemp2.append(QgsPoint(geom1[i][0],geom1[i][1]))
            geomtemp1.append(QgsGeometry.fromPolygon([geomtemp2]) )   
        return geomtemp1
     
    def InsertRinginFeature(self,f1,allfeatures2,vlOuterTempIndex,lvltemp1,counttotal):
        #Correction des erreurs de geometrie des outers
        if len(f1.geometry().validateGeometry())!=0:                                           
            f1geom  = f1.geometry().buffer(0.01,5)
        else:
            f1geom = f1.geometry()
            
        # requete spatiale pour avoir les inner dans les outers
        ids = vlOuterTempIndex.intersects(f1geom.boundingBox())                                       

        
        fet1surface=f1geom.area()
        #Iteration sur tous les inners pour les inclures dans les outers ****
        # creation d un tableau pour trier les inners par ordre de S decroissant
        tab=[]
        for id in ids:
            f2geom = allfeatures2[id].geometry()
            if len(f2geom.validateGeometry())!=0:
                f2geom= f2geom.buffer(0.01,5)
            tab.append([f2geom.area(),f2geom])                          
        if len(tab)>0:
            tab.sort(reverse = True)
            #Iteration pour enlever les inner des outers - coeur du script
            for k in range(len(tab)):                                                
                try:
                    if int(k)%100 == 0 and k != 0:
                        self.verboseOutput(self.slf_param[1],lvltemp1,f1.id(),counttotal,k,len(ids))

                    if tab[k][0]>=fet1surface:
                        continue
                    else:
                        ring = self.do_ring(tab[k][1])
                        tt1 = f1geom.addRing(ring)
                        if tt1==5 and f1geom.intersects(tab[k][1]):
                            f1geom=f1geom.difference(tab[k][1])
                except Exception, e:
                    strtxt = (str(ctime()) + " - "+str(self.slf_param[1] )
                                           +" - Thread - Traitement du niveau " + str(lvltemp1)
                                           +" - geometry n "+str(f1.id())+"/"+str(counttotal ) 
                                           +" - ile n "+str(k)+"/"+str(len(ids))
                                           +" - Probleme d integration ******** : "+str(e)+" "
                                           +str( tab[k][0])+" "+str( self.get_outerinner(tab[k][1])))
                    self.writeOutput(strtxt)
        if len(f1geom.validateGeometry())!=0:
            f1geom= f1geom.buffer(0.01,5)
        if self.xform:
            f1geom.transform(self.xform)
        fet = QgsFeature()
        fet.setGeometry(f1geom)  
        fet.setAttributes([lvltemp1[0],lvltemp1[1]])
        
        return fet
     
    def do_ring(self,geom3):        
        ring = []
        polygon = geom3.asPolygon()[0]
        for i in range(len(polygon)):
            ring.append(QgsPoint(polygon[i][0],polygon[i][1]))
        ring.append(QgsPoint(polygon[0][0],polygon[0][1]))
        return ring
     
     
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(str)

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitSelafinContour2Shp(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None


    def start(self, 
                 processtype,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                 selafinfilepath,                 #path to selafin file
                 time,                            #time to process (selafin time in seconds if exist else iteration number)
                 parameter,                     #parameter to process name (string) or id (int)
                 levels,                       #levels to create
                 selafincrs = 'EPSG:2154',      #selafin crs
                 selafintransformedcrs = None,   #if no none, specify crs of output file
                 quickprocessing = False,                #quickprocess option - don't make ring
                 outputshpname = None,           #change generic outputname to specific one
                 outputshppath = None,         #if not none, create shp in this directory
                 forcedvalue = None,          #force value for plugin
                 outputprocessing = None):    #needed for toolbox processing
                 
        #Check validity
        self.processtype = processtype
        try:
            #slf = SELAFIN(os.path.normpath(selafinfilepath))
            parserhydrau = PostTelemacSelafinParser()
            parserhydrau.loadHydrauFile(os.path.normpath(selafinfilepath))
            slf = parserhydrau.hydraufile
        except:
            self.raiseError('fichier selafin n existe pas')
            
        #times = slf.tags["times"]
        times = parserhydrau.getTimes()
        if isinstance(time,int):            #cas des plugins et scripts
            if not time in range(len(times)):
                self.raiseError(str(ctime()) + " Time non trouve dans  "+str(times))
        elif isinstance(time,str):  #cas de la ligne de commande python - utilise time en s
            if time in times:
                time = list(times).index(int(time))
            else:
                self.raiseError(str(ctime()) + " Time non trouve dans  "+str(times))
        
           
        #parameters=[str(slf.VARNAMES[i]).strip() for i in range(len(slf.VARNAMES))]
        parameters=[str(parserhydrau.getVarnames()[i]).strip() for i in range(len(parserhydrau.getVarnames()))]
        if not parameter.isdigit():
            if parameter in parameters:
                #self.slf_param = [parameters.index(parameter), parameter ]
                parameter = parameters.index(parameter)
            else:
                if not self.processtype ==0:
                    self.raiseError( str(parameter) + " parameter pas trouve dans "+str(parameters))
        
        #Launch worker
        self.worker = SelafinContour2Shp(processtype,selafinfilepath,time,parameter,levels,selafincrs,selafintransformedcrs,quickprocessing,outputshpname,outputshppath,forcedvalue,outputprocessing)
        if processtype in [0,1]:
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.createShp)
            self.worker.status.connect(self.writeOutput)
            self.worker.error.connect(self.raiseError)
            self.worker.finished.connect(self.workerFinished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(self.thread.quit)
            champ = QgsFields()
            if processtype in [1]:
                writercontour = VectorWriter(outputprocessing, 
                                                        None, champ, 
                                                        QGis.WKBMultiPolygon, 
                                                        QgsCoordinateReferenceSystem(str(selafincrs) ))
            self.thread.start()
        else :
            self.worker.createShp()
    
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
        
    def workerFinished(self,str1):
        self.finished1.emit(str(str1))

        
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(str)
            

if __name__ == '__main__':
    #unless doesnt work outisde qgis
    qgishome = os.environ['QGIS_PREFIX_PATH']
    app = QgsApplication([], True)
    QgsApplication.setPrefixPath(qgishome, True)
    QgsApplication.initQgis() 
    print len(sys.argv[1:])
    
    initclass=InitSelafinContour2Shp()
    
    if len(sys.argv[1:])==4:
        traitement = initclass.start(4,                    #type de traitement
                                    sys.argv[1],    #path to selafin file
                                    sys.argv[2],    # time of selafin file
                                    str(sys.argv[3]),    # name or id of the parametre
                                    [float(sys.argv[4].split(',')[i]) for i in range(len(sys.argv[4].split(',')))])   # levels
            
    if len(sys.argv[1:])==5:
        traitement = initclass.start(4,                    #type de traitement
                                    sys.argv[1],    #path to selafin file
                                    sys.argv[2],    # time of selafin file
                                    str(sys.argv[3]),    # name or id of the parametre
                                    [float(sys.argv[4].split(',')[i]) for i in range(len(sys.argv[4].split(',')))],   # levels
                                    str(sys.argv[5]))   #selafin crs
                                    
    if len(sys.argv[1:])==6:
        traitement = initclass.start(4,                    #type de traitement
                                    sys.argv[1],    #path to selafin file
                                    sys.argv[2],    # time of selafin file
                                    str(sys.argv[3]),    # name or id of the parametre
                                    [float(sys.argv[4].split(',')[i]) for i in range(len(sys.argv[4].split(',')))],   # levels
                                    str(sys.argv[5]),   #selafin crs
                                    str(sys.argv[6]))   #outputshpcrs 
                                    
