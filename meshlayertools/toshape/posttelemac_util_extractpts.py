##[01_Telemac]=group


#*************************************************************************
"""
Versions :
0.0 premier script
0.2 : un seul script pour modeleur ou non

"""
#*************************************************************************

##Type_de_traitement=selection En arriere plan;Modeler;Modeler avec creation de fichiers

##Fichier_resultat_telemac=file
##Temps_a_exploiter_fichier_max_0=number 0.0
##Pas_d_espace_0_si_tous_les_points=number 0.0
##fichier_point_avec_vecteur_vitesse=boolean False
##Parametre_vitesse_X=string UVmax
##Parametre_vitesse_Y=string VVmax
##systeme_de_projection=crs EPSG:2154
##forcage_attribut_fichier_de_sortie=string 

##fichier_de_sortie_points=output vector 

#unicode behaviour
from __future__ import unicode_literals

import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from os import path
import numpy as np
from matplotlib.path import Path
from processing.core.GeoAlgorithmExecutionException import  GeoAlgorithmExecutionException
from processing.tools.vector import VectorWriter
import matplotlib.pyplot as plt
from matplotlib import tri

from qgis.utils import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui

"""
from ..libs_telemac.utils.files import getFileContent
from ..libs_telemac.parsers.parserSortie import getValueHistorySortie
from ..libs_telemac.parsers.parserSELAFIN import getValueHistorySLF,   getValuePolylineSLF,subsetVariablesSLF
from ..libs_telemac.parsers.parserSELAFIN import SELAFIN
from ..libs_telemac.parsers.parserStrings import parseArrayPaires
"""


import threading
from time import ctime
import math
from ...meshlayerparsers.posttelemac_selafin_parser import *

        


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

#*************************************************************************
"""
def workerFinished(str1):
    progress.setText(str(ctime()) +" - Fin du thread - Chargement du fichier resultat")
    vlayer = QgsVectorLayer( str1, os.path.basename(str1).split('.')[0],"ogr")
    QgsMapLayerRegistry.instance().addMapLayer(vlayer)

"""
        
       
class SelafinContour2Pts(QtCore.QObject):

    #def __init__(self, donnees_d_entree):
    def __init__(self, 
                 processtype,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                 selafinfilepath,                 #path to selafin file
                 time,                            #time to process (selafin time in interation if int, or second if str)
                 spacestep,                     #space step
                 computevelocity,               #bool for comuting velocity
                 paramvx,
                 paramvy,
                 ztri,                          #tab of values
                 selafincrs ,      #selafin crs
                 translatex = 0,
                 translatey = 0,
                 selafintransformedcrs = None,   #if no none, specify crs of output file
                 outputshpname = None,           #change generic outputname to specific one
                 outputshppath = None,         #if not none, create shp in this directory
                 outputprocessing = None):    #needed for toolbox processing
    
        QtCore.QObject.__init__(self)
        
        self.traitementarriereplan = processtype
        """
        slf = SELAFIN(os.path.normpath(selafinfilepath))
        self.x = slf.MESHX
        self.y = slf.MESHY
        self.mesh = np.array(slf.IKLE3)
        """
        #donnes delafin
        self.parserhydrau = PostTelemacSelafinParser()
        self.parserhydrau.loadHydrauFile(os.path.normpath(selafinfilepath))
        
        #slf = SELAFIN(os.path.normpath(selafinfilepath))
        slf = self.parserhydrau.hydraufile
        """
        self.slf_x = slf.MESHX
        self.slf_y = slf.MESHY
        self.mesh = np.array(slf.IKLE3)
        """
        self.x, self.y  = self.parserhydrau.getMesh()
        self.x = self.x + translatex
        self.y = self.y + translatey
        self.mesh  = np.array( self.parserhydrau.getIkle() )
        
        self.time = time
        self.pasespace = spacestep
        self.computevelocity = computevelocity
        self.paramvalueX = paramvx
        self.paramvalueY = paramvy
        self.ztri = ztri
        #self.traitementarriereplan = donnees_d_entree['traitementarriereplan']

        self.crs = selafincrs
        
        #self.pathshp = donnees_d_entree['pathshp'] 
        #donnees shp - outside qgis
        if not outputshpname :
            outputshpname = (os.path.basename(os.path.normpath(selafinfilepath)).split('.')[0]
                             +"_point"
                             +str('.shp'))
        else:
            outputshpname = (os.path.basename(os.path.normpath(selafinfilepath)).split('.')[0] 
                             + "_"+str(outputshpname)
                             +str('.shp'))
        if  not outputshppath:
            outputshppath=os.path.dirname(os.path.normpath(selafinfilepath))
        self.pathshp=os.path.join(outputshppath,outputshpname)
        
        #Fields creation
        test = [False,False]
        tabparam = []
        #donnees_d_entree['champs'] = QgsFields()
        fields = QgsFields()
        #for i,name in enumerate(slf.VARNAMES):
        for i,name in enumerate(self.parserhydrau.getVarnames()):
                self.writeOutput(str(ctime()) +" - Initialisation - Variable dans le fichier res : " 
                                         + name.strip() )
                tabparam.append([i,name.strip()])
                #donnees_d_entree['champs'].append(QgsField(str(name.strip()).translate(None, "?,!.;"),   QVariant.Double))
                #fields.append(QgsField(str(name.strip()).translate(None, "?,!.;"),   QVariant.Double))
                fields.append(QgsField(str(name.strip()),   QVariant.Double))
                #if self.donnees_d_entree['Parametre_vitesse_X']   !=  None:
                """
                if self.paramvalueX   !=  None:
                    #if str(name).strip() == self.donnees_d_entree['Parametre_vitesse_X'].strip():
                    if str(name).strip() == self.paramvalueX.strip():
                        test[0]=True
                        #self.donnees_d_entree['paramvalueX']  = i
                        self.paramvalueX  = i
                    #if str(name).strip() == self.donnees_d_entree['Parametre_vitesse_Y'].strip():
                    if str(name).strip() == self.paramvalueY.strip():
                        test[1]=True
                        #self.donnees_d_entree['paramvalueY'] = i
                        self.paramvalueY = i
                else:
                    
                    #self.donnees_d_entree['paramvalueX']  = None
                    #self.donnees_d_entree['paramvalueY']  = None
                    
                    self.paramvalueX = None
                    self.paramvalueY = None
                """
                    
        #if self.donnees_d_entree['Parametre_vitesse_X']  != None:
        """
        if self.paramvalueX  != None:
            if test == [True,True]:
                self.writeOutput( str(ctime()) + " - Initialisation - Parametre trouvee : " 
                                         +str(tabparam[self.paramvalueX ][1]).strip()+" "
                                         +str(tabparam[self.paramvalueY ][1]).strip())
            else:
                raise GeoAlgorithmExecutionException(str(ctime()) + " - Initialisation - Erreur : \
                                     Parametre vitesse non trouve")
        """
        self.vlayer = ""

        self.vitesse = '0'
 
        
        #fields = donnees_d_entree['champs']
        if self.computevelocity :
            fields.append(QgsField("UV",   QVariant.Double))
            fields.append(QgsField("VV",   QVariant.Double))
            fields.append(QgsField("norme",   QVariant.Double))
            fields.append(QgsField("angle",   QVariant.Double))
            self.vitesse = '1'
            
        if self.traitementarriereplan == 0 or self.traitementarriereplan == 2 :
            self.writerw1  = QgsVectorFileWriter(self.pathshp, 
                                                                 None, 
                                                                 fields ,   
                                                                 QGis.WKBPoint, QgsCoordinateReferenceSystem(str(self.crs) ), 
                                                                 "ESRI Shapefile")
        """                                                         
        if self.traitementarriereplan == 1 or self.traitementarriereplan == 2 :
            self.writerw2 = VectorWriter(donnees_d_entree['fichierdesortie_point'],
                                                      None , fields, 
                                                      QGis.WKBMultiPoint, 
                                                      QgsCoordinateReferenceSystem(str(self.crs) ))
                                                      
        """

    def run(self):
            strtxt = (str(ctime()) + ' - Thread - repertoire : '+os.path.dirname(self.pathshp)
                         +' - fichier : '+os.path.basename(self.pathshp))
            """
            if self.traitementarriereplan == 0 : self.status.emit(strtxt) 
            else : progress.setText(strtxt)
            """
            self.writeOutput(strtxt)
            
            fet = QgsFeature()
            try :
                if True :
                    if self.paramvalueX== None:
                        boolvitesse = False
                    else:
                        boolvitesse = True
                    #------------------------------------- TRaitement de tous les points
                    if self.pasespace == 0:
                        noeudcount = len(self.x)
                        strtxt = (str(ctime()) + " - Thread - Traitement des vitesses - "
                                     +str(noeudcount)+" noeuds")
                        """
                        if self.traitementarriereplan  == 0 : self.status.emit(strtxt) 
                        else : progress.setText(strtxt)
                        """
                        self.writeOutput(strtxt)
                        
                        for k in range (len(self.x)):
                            if k%5000 == 0:
                                strtxt = (str(ctime()) + " - Thread - noeud n "+str(k)+"/"+str(noeudcount))
                                """
                                if self.traitementarriereplan  == 0 : self.status.emit(strtxt) 
                                else : progress.setText(strtxt)
                                """
                                self.writeOutput(strtxt)
                                """
                                
                                if self.traitementarriereplan  == 0 : self.progress.emit(int(100.0*k/noeudcount))
                                else : progress.setPercentage(int(100.0*k/noeudcount))
                                """
                                

                                
                            fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(float(self.x[k]),float(self.y[k]))))
                            #self.writeOutput('temp1')
                            tabattr = []
                            if len(self.ztri)>0:
                                for l in range (len(self.ztri)):
                                    tabattr.append(float(self.ztri[l][k]))
                            #self.writeOutput('temp2')
                            if boolvitesse:
                                norme = ((float(self.ztri[self.paramvalueX][k]))**2.0+(float(self.ztri[self.paramvalueY][k]))**2.0)**(0.5)
                                atanUVVV = math.atan2(float(self.ztri[self.paramvalueY][k]), float(self.ztri[self.paramvalueX][k]))
                                
                                angle = atanUVVV/math.pi*180.0
                                if angle<0:
                                    angle = angle +360
                                
                                #angle YML
                                #angle = atanUVVV*180.0/math.pi+min(atanUVVV,0)/atanUVVV*360.0
                                tabattr.append(float(self.ztri[self.paramvalueX][k]))
                                tabattr.append(float(self.ztri[self.paramvalueY][k]))
                                tabattr.append(norme)
                                tabattr.append(angle)
                            #self.writeOutput('temp3')
                            fet.setAttributes(tabattr)
                            if self.traitementarriereplan  == 0 or self.traitementarriereplan  == 2:
                                self.writerw1.addFeature(  fet )
                            if self.traitementarriereplan  == 1 or self.traitementarriereplan  == 2:
                                self.writerw2.addFeature(  fet ) 
                    #------------------------------------- Traitement  du pas d'espace des points
                    else :
                        triangul = tri.Triangulation(self.x,self.y,self.mesh)
                        lineartri = []
                        if len(self.ztri)>0:
                            for i in range (len(self.ztri)):
                                lineartri.append(tri.LinearTriInterpolator(triangul, self.ztri[i]))

                        xmin = np.min(self.x) 
                        xmax = np.max(self.x)
                        ymin = np.min(self.y)
                        ymax = np.max(self.y)
                        pasx = int((xmax-xmin)/self.pasespace)
                        pasy = int((ymax-ymin)/self.pasespace)
                        
                        strtxt = (str(ctime()) + " - Thread - Traitement des vitesses - pas d espace : "
                                     +str(self.pasespace)+"m - nombre de points : "
                                     +str(pasx)+"*"+str(pasy)+"="+str(pasx*pasy))
                        """             
                        if self.traitementarriereplan  == 0 : self.status.emit(strtxt) 
                        else : progress.setText(strtxt)
                        """
                        self.writeOutput(strtxt)
                        
                        compt = 0
                        for x2 in range(pasx):
                            xtemp=float(xmin+x2*self.pasespace)

                            for y2 in range(pasy):
                                compt = compt + 1
                                if (compt)%5000 == 0:
                                    strtxt = (str(ctime()) + " - Thread -  noeud n "+str(compt)+ "/" +str(pasx*pasy))
                                    """
                                    if self.traitementarriereplan  == 0 : self.status.emit(strtxt) 
                                    else : progress.setText(strtxt)
                                    
                                    if self.traitementarriereplan  == 0 : self.progress.emit(int(100.0*compt/(pasy*pasx)))
                                    else : progress.setPercentage(int(100.0*compt/(pasy*pasx)))
                                    """
                                    self.writeOutput(strtxt)
                                    
                                ytemp = float(ymin+y2*self.pasespace)
                                fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(xtemp,ytemp)))
                                tabattr1 = []
                                if str(float(lineartri[0].__call__(xtemp,ytemp))) == 'nan':
                                    continue
                                
                                for j in range(len(lineartri)):
                                    tabattr1.append(float(lineartri[j].__call__(xtemp,ytemp)))
                                if boolvitesse:
                                    VX=float(lineartri[self.paramvalueX].__call__(xtemp,ytemp))
                                    VY=float(lineartri[self.paramvalueY].__call__(xtemp,ytemp))
                                    norme = ((VX)**2.0+(VY)**2.0)**(0.5)
                                    angle = math.atan2(VY,VX)/math.pi*180.0
                                    if angle<0:
                                        angle = angle +360
                                    tabattr1.append(VX)
                                    tabattr1.append(VY)
                                    tabattr1.append(norme)
                                    tabattr1.append(angle)
                                fet.setAttributes(tabattr1)
                                if self.traitementarriereplan  == 0 or self.traitementarriereplan  == 2:
                                    self.writerw1.addFeature(  fet )
                                if self.traitementarriereplan  == 1 or self.traitementarriereplan  == 2:
                                    self.writerw2.addFeature(  fet ) 
                        
                    #del self.writerw
            except Exception, e:
                strtxt = (str(ctime()) + " ************ PROBLEME CALCUL DES VITESSES : " + str(e))
                """
                if self.traitementarriereplan  == 0 : self.status.emit(strtxt) 
                else : progress.setText(strtxt)
                """
                self.writeOutput(strtxt)
 
            """
            if self.traitementarriereplan == 0: self.progress.emit(int(100.0))
            else : progress.setPercentage(int(100.0))
            """
            if self.traitementarriereplan  == 0 or self.traitementarriereplan  == 2 :
                del self.writerw1
            if self.traitementarriereplan  == 1 or self.traitementarriereplan  == 2 :
                del self.writerw2
            strtxt = (str(ctime()) +" - Thread - fichier " + self.pathshp + " cree")
            """
            if self.traitementarriereplan   == 0 : self.status.emit(strtxt) 
            else : progress.setText(strtxt)
            """
            self.writeOutput(strtxt)
            #self.status.emit("Fichier " + self.nomrept+ '\ '.strip()+ self.nomfilet + " cree")
            if self.traitementarriereplan   == 0 : 
                self.finished.emit(self.pathshp)
            if self.traitementarriereplan   == 2 : 
                t =  workerFinished(self.pathshp)
                
    def writeOutput(self,str1):
        if self.traitementarriereplan in [0,1,2,3]: 
            self.status.emit(str(str1))
        elif self.traitementarriereplan ==4 : print str1
        
    def raiseError(self,str1):
        self.error.emit(str(str1))
                

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(str)  
      
    

#****************************************************************************
#*************** Classe de lancement du thread ***********************************
#****************************************************************************

class InitSelafinMesh2Pts(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None


    def start(self, 
                 processtype,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                 selafinfilepath,                 #path to selafin file
                 time,                            #time to process (selafin time in interation if int, or second if str)
                 spacestep,                     #space step
                 computevelocity,               #bool for comuting velocity
                 paramvx,
                 paramvy,
                 ztri,                          #tab of values
                 selafincrs ,      #selafin crs
                 translatex = 0,
                 translatey = 0,
                 selafintransformedcrs = None,   #if no none, specify crs of output file
                 outputshpname = None,           #change generic outputname to specific one
                 outputshppath = None,         #if not none, create shp in this directory
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
        
        #check time
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
        
        #check velocity creation
        
        
            
        """
        if parameter is not None:
            parameters=[str(slf.VARNAMES[i]).strip() for i in range(len(slf.VARNAMES))]
            if not parameter.isdigit():
                if parameter in parameters:
                    #self.slf_param = [parameters.index(parameter), parameter ]
                    parameter = parameters.index(parameter)
                else:
                    self.raiseError( str(parameter) + " parameter pas trouve dans "+str(parameters))
            else : 
                parameter = int(parameter)
        """
        self.worker = SelafinContour2Pts(processtype,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                                         selafinfilepath,                 #path to selafin file
                                         time,                            #time to process (selafin time in interation if int, or second if str)
                                         spacestep,                     #space step
                                         computevelocity,               #bool for comuting velocity
                                         paramvx,
                                         paramvy,
                                         ztri,                          #tab of values
                                         selafincrs ,      #selafin crs
                                         translatex = translatex ,
                                         translatey = translatey ,
                                         selafintransformedcrs = selafintransformedcrs,   #if no none, specify crs of output file
                                         outputshpname = outputshpname,           #change generic outputname to specific one
                                         outputshppath = outputshppath,         #if not none, create shp in this directory
                                         outputprocessing = outputprocessing)    #needed for toolbox processing
                                         
                                         
                                         
                                         
        if processtype in [0,1]:
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
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







class InitSelafinMesh2Pts2():
    def __init__(self,donnees_d_entree):
        self.donnees_d_entree = donnees_d_entree
        self.thread = QtCore.QThread()

        if donnees_d_entree['forcage_attribut_fichier_de_sortie']=="":
            if self.donnees_d_entree['pasdespace']==0:
                self.donnees_d_entree['pathshp'] =os.path.join(os.path.dirname(self.donnees_d_entree['pathselafin']),
                                                                                           os.path.basename(self.donnees_d_entree['pathselafin']).split('.')[0]
                                                                                           +"_points_t_"+str(int(self.donnees_d_entree['temps']))+str('.shp'))  
            else:
                self.donnees_d_entree['pathshp']=os.path.join(os.path.dirname(self.donnees_d_entree['pathselafin']),
                                                                                           os.path.basename(self.donnees_d_entree['pathselafin']).split('.')[0]
                                                                                           +"_points_"+str(int(self.donnees_d_entree['pasdespace']))
                                                                                           +"m_t_"+str(int(self.donnees_d_entree['temps']))+str('.shp'))  
        else:
                self.donnees_d_entree['pathshp']=os.path.join(os.path.dirname(self.donnees_d_entree['pathselafin']),
                                                                                           os.path.basename(self.donnees_d_entree['pathselafin']).split('.')[0]
                                                                                           +"_"+str(self.donnees_d_entree['forcage_attribut_fichier_de_sortie'])
                                                                                           +str('.shp'))

        if self.donnees_d_entree['fichier_point_avec_vecteur_vitesse']:
            self.donnees_d_entree['Parametre_vitesse_X'] = donnees_d_entree['Parametre_vitesse_X']
            self.donnees_d_entree['Parametre_vitesse_Y'] = donnees_d_entree['Parametre_vitesse_Y']
        else:
            self.donnees_d_entree['Parametre_vitesse_X'] = None
            self.donnees_d_entree['Parametre_vitesse_Y'] = None

        self.worker = ""


    def main1(self):
        progress.setPercentage(0)
        progress.setText(str(ctime()) + " - Initialisation - Debut du script")
        #Chargement du fichier .res****************************************
        slf = SELAFIN(self.donnees_d_entree['pathselafin'])
        
        #Recherche du temps a traiter ***********************************************
        test = False
        for i,time in enumerate(slf.tags["times"]):
            progress.setText(str(ctime()) + " - Initialisation - Temps present dans le fichier : "
                                    +str(np.float64(time)))
            #print str(i) +" "+ str(time) + str(type(time))
            if float(time) == float(self.donnees_d_entree['temps']) :
                test=True
                values = slf.getVALUES(i)
        if test:
            progress.setText(str(ctime()) + " - Initialisation - Temps traite : "
                                    +str(np.float64(self.donnees_d_entree['temps'])))
        else:
            raise GeoAlgorithmExecutionException(str(ctime()) + " - Initialisation - Erreur : \
                                   Temps non trouve")


        #Recherche de la variable a traiter ****************************************
        test = [False,False]
        tabparam = []
        donnees_d_entree['champs'] = QgsFields()
        for i,name in enumerate(slf.VARNAMES):
                progress.setText(str(ctime()) +" - Initialisation - Variable dans le fichier res : " 
                                         + name.strip() )
                tabparam.append([i,name.strip()])
                donnees_d_entree['champs'].append(QgsField(str(name.strip()).translate(None, "?,!.;"),   QVariant.Double))
                if self.donnees_d_entree['Parametre_vitesse_X']   !=  None:
                    if str(name).strip() == self.donnees_d_entree['Parametre_vitesse_X'].strip():
                        test[0]=True
                        self.donnees_d_entree['paramvalueX']  = i
                    if str(name).strip() == self.donnees_d_entree['Parametre_vitesse_Y'].strip():
                        test[1]=True
                        self.donnees_d_entree['paramvalueY'] = i
                else:
                    self.donnees_d_entree['paramvalueX']  = None
                    self.donnees_d_entree['paramvalueY']  = None
        if self.donnees_d_entree['Parametre_vitesse_X']  != None:
            if test == [True,True]:
                progress.setText(str(ctime()) + " - Initialisation - Parametre trouvee : " 
                                         +str(tabparam[self.donnees_d_entree['paramvalueX'] ][1]).strip()+" "
                                         +str(tabparam[self.donnees_d_entree['paramvalueY'] ][1]).strip())
            else:
                raise GeoAlgorithmExecutionException(str(ctime()) + " - Initialisation - Erreur : \
                                     Parametre vitesse non trouve")
        


        #Chargement de la topologie du .res ********************************************
        self.donnees_d_entree['mesh']  = np.array(slf.IKLE3)
        self.donnees_d_entree['x']  = slf.MESHX
        self.donnees_d_entree['y']  = slf.MESHY

        #Verifie que le shp n existe pas
        if isFileLocked(self.donnees_d_entree['pathshp'], True):
            raise GeoAlgorithmExecutionException(str(ctime()) + " - Initialisation - Erreur :\
                                   Fichier shape deja charge !!")

        #Chargement des donnees  ***********************************
        self.donnees_d_entree['ztri']  = []
        for i in range (len(tabparam)):
            self.donnees_d_entree['ztri'] .append(values[i])
 
        #Lancement du thread **************************************************************************************

        self.worker = Worker(donnees_d_entree)
        if donnees_d_entree['traitementarriereplan']== 0:
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.progress.connect(progress.setPercentage)
            self.worker.status.connect(progress.setText)
            self.worker.finished.connect(workerFinished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(self.thread.quit)
            champ = QgsFields()
            writercontour = VectorWriter(self.donnees_d_entree['fichierdesortie_point'], 
                                                       None, champ, 
                                                       QGis.WKBMultiPoint, 
                                                       QgsCoordinateReferenceSystem(str(self.donnees_d_entree['crs']) ))
            self.thread.start()
        else :
            self.worker.run()

    
#*************************************************************************   
# ************** Initialisation des variables ****************************************
#*************************************************************************   



    