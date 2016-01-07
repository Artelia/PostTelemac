##[01_Telemac]=group


#*************************************************************************
"""
Versions :
0.0 : debut
0.1 : un seul script pour modeleur ou non


"""
#*************************************************************************


##Type_de_traitement=selection En arriere plan;Modeler;Modeler avec creation de fichiers

##Fichier_resultat_telemac=file
##Temps_a_exploiter_fichier_max_0=number 0.0
##Ajout_des_z=boolean False
##Traitement_hillshade=boolean True
##Zenith_si_hillshade=number 30.0
##Azimuth_si_hillshade=number 0.0
##Facteurz_si_hillshade=number 10.0
##Variable=selection FOND
##Autre_variable=string 
##systeme_de_projection=crs EPSG:27562
##forcage_attribut_fichier_de_sortie=string 


##fichier_de_sortie_maillage=output vector 


#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from processing.core.GeoAlgorithmExecutionException import  GeoAlgorithmExecutionException
from processing.tools.vector import VectorWriter
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
#import telemac python

from ..libs_telemac.utils.files import getFileContent
from ..libs_telemac.parsers.parserSortie import getValueHistorySortie
from ..libs_telemac.parsers.parserSELAFIN import getValueHistorySLF,   getValuePolylineSLF,subsetVariablesSLF
#from ..libs_telemac.parsers.parserSELAFIN import SELAFIN

from ..libs_telemac.parsers.parserStrings import parseArrayPaires
#imports divers
import threading
from time import ctime
import math
from os import path
from shapely.geometry import Polygon
import sys
import os.path
from matplotlib import tri
from posttelemac_selafin_parser import *

#*************************************************************************


class getCompareValue(QtCore.QObject):

    def __init__(self,layer,var_corresp):
        QtCore.QObject.__init__(self)
        self.layer = layer
        #self.slf1 = layer.slf
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.toPlainText())
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.text())
        self.selafinparsercompared = PostTelemacSelafinParser()
        self.selafinparsercompared.loadSelafin(layer.propertiesdialog.lineEdit_5.text())
        #layer.compare = True
        layer.updatevalue.connect(self.updateSelafinValue)
        self.triinterp=None
        self.comparetime = None
        self.values = None
        self.transmitvalues = False
        self.var_corresp = var_corresp
        """
        self.var_corresp = []
        for var in self.slf1.VARNAMES:
            if var in self.slf2.VARNAMES:
                self.var_corresp.append([self.slf1.VARNAMES.index(var),self.slf2.VARNAMES.index(var)])
            else:
                self.var_corresp.append([self.slf1.VARNAMES.index(var),None])
        self.layer.propertiesdialog.lineEdit.setText(str(self.var_corresp))
        """
                
    def reset_dialog(self):
        self.layer.propertiesdialog.textEdit_2.clear()
        self.layer.propertiesdialog.textEdit_3.clear()
        self.layer.propertiesdialog.lineEdit_5.clear()
        self.layer.propertiesdialog.lineEdit.clear()
        self.layer.propertiesdialog.checkBox_6.setCheckState(0)
        self.layer.propertiesdialog.checkBox_6.setEnabled(False)
        
        
        
    def updateSelafinValue(self):
        #self.var_corresp=self.layer.propertiesdialog.lineEdit.text.tolist()
        temp1 = []
        """
        for i in range(len(self.var_corresp)):
            if self.var_corresp[i][1] is None:
                self.layer.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsSelectable)
        """


        #lenvarnames = len(self.slf1.VARNAMES)
        lenvarnames = len(self.layer.selafinparser.getVarnames())
        meshx1,meshy1 = self.layer.selafinparser.getMesh()
        ikle1 = self.layer.selafinparser.getIkle()
        meshx2,meshy2 = self.selafinparsercompared.getMesh()
        ikle2 = self.selafinparsercompared.getIkle()

        if self.comparetime != self.layer.time_displayed:
            try:
                #desactive non matching parameters

                
        

                if (np.array_equal(ikle1 , ikle2) 
                    and np.array_equal(meshx1 , meshx2) 
                    and np.array_equal(meshy1 , meshy2)):
                    
                    self.status.emit("fichiers identiques ")
                    valuetab = []
                    for i in range(lenvarnames):
                        if self.var_corresp[i][1] is not None:
                            #value = self.slf2.getVALUES(self.layer.temps_gachette)[i] - self.slf1.getVALUES(self.layer.temps_gachette)[i]
                            value = self.selafinparsercompared.getValues(self.layer.time_displayed)[i] - self.layer.selafinparser.getValues(self.layer.time_displayed)[i]
                            #print str(value.shape)
                        else:
                            value = [np.nan]*len(meshx1)
                            value = np.array(value).transpose()
                            #print str(value.shape)
                        valuetab.append(value)
                    
                    self.values = np.array(valuetab)
                    #print str(self.values.shape)

                else:
                    self.status.emit("fichiers non egaux")
                    #projection of slf2 to slf1
                    #triinterp
                    triang = tri.Triangulation(meshx2,meshy2,np.array(ikle2))
                    
                    self.triinterp = []
                    for i in range(lenvarnames):
                        if self.var_corresp[i][1] is not None:
                            #self.triinterp = [tri.LinearTriInterpolator(triang, self.slf2.getVALUES(self.layer.temps_gachette)[i]) for i in range(lenvarnames)]
                            #self.triinterp.append(tri.LinearTriInterpolator(triang, self.slf2.getVALUES(self.layer.temps_gachette)[self.var_corresp[i][1]]))
                            self.triinterp.append(tri.LinearTriInterpolator(triang, self.selafinparsercompared.getValues(self.layer.time_displayed)[self.var_corresp[i][1]]))
                        else:
                            self.triinterp.append(None)
                    valuesslf2 = []
                    #slf1meshx = self.slf1.MESHX
                    #slf1meshy = self.slf1.MESHY
                    count = self.layer.selafinparser.pointcount
                    #projection for matching parameters
                    if False:
                        for i in range(count):
                            if i%1000 == 0:
                                self.status.emit(ctime() + " - reproject " + str(i)+"/"+str(count))
                            tabtemp=[]
                            for  j in range(lenvarnames):
                                if self.var_corresp[j][1] is not None:
                                    temp = float(self.triinterp[j].__call__(meshx1[i],meshy1[i]))
                                    if np.isnan(temp) : temp=-9999.0
                                    tabtemp.append(temp)
                                else:
                                    tabtemp.append(np.nan)
                                    #tabtemp.append(np.array([np.nan]*count))
                            valuesslf2.append(tabtemp)
                        valuesslf2 = np.array(valuesslf2).transpose()
                        #self.values = valuesslf2 - self.slf1.getVALUES(self.layer.temps_gachette)
                        self.values = valuesslf2 - self.layer.selafinparser.getValues(self.layer.time_displayed)
                    else:
                        tabtemp=[]
                        for  j in range(lenvarnames):
                            if self.var_corresp[j][1] is not None:
                                #self.status.emit( str(self.var_corresp[j][1]) )
                                tabtemp = self.triinterp[j].__call__(meshx1,meshy1)
                                #self.status.emit( str(np.isnan(tabtemp).any())) 
                                #print str(tabtemp)
                                #self.status.emit( str(tabtemp.shape ))
                            else:
                                #self.status.emit( 'ok1')
                                
                                tabtemp = np.array([np.nan]*count)
                                #self.status.emit( str(tabtemp.shape ))
                                #tabtemp.append(arr1)

                            valuesslf2.append(tabtemp)
                        #self.status.emit( 'ok' )
                        #valuesslf2 = np.array(valuesslf2).transpose()
                        #temp1 = valuesslf2 - self.slf1.getVALUES(self.layer.temps_gachette)
                        temp1 = valuesslf2 - self.layer.selafinparser.getValues(self.layer.time_displayed)
                        self.values = np.nan_to_num(temp1)
                        #self.status.emit( str(np.isnan(self.values).any()) ) 
                                
                                
            except Exception, e:
                self.status.emit("updateSelafinValue :"+str(e))
                self.values = None
                self.finished.emit()
                
        if self.transmitvalues:
            self.layer.values = self.values
            self.layer.value = self.values[self.layer.param_displayed] 

        self.comparetime = self.layer.time_displayed
        self.status.emit( 'finish')
        self.finished.emit()

        
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

class initgetCompareValue():

    def __init__(self,layer):
        #QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.layer = layer

        
        #camparative variales
        self.var_corresp = []
        #self.slf1 = layer.slf
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.toPlainText())
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.text())
        self.selafinparsercompared = PostTelemacSelafinParser()
        self.selafinparsercompared.loadSelafin(layer.propertiesdialog.lineEdit_5.text())
        
        for var in self.layer.selafinparser.getVarnames():
            if var in self.selafinparsercompared.getVarnames() :
                self.var_corresp.append([self.layer.selafinparser.getVarnames().index(var),self.selafinparsercompared.getVarnames().index(var)])
            else:
                self.var_corresp.append([self.layer.selafinparser.getVarnames().index(var),None])
        self.layer.propertiesdialog.lineEdit.setText(str(self.var_corresp))
        
        self.compare = getCompareValue(self.layer,self.var_corresp)
        self.compare.status.connect(self.writeOutput)
        #self.compare.finished.connect(self.workerFinished)
        
        
    def run(self):
        try:
            self.compare.finished.disconnect(self.workerFinished)
        except Exception, e :
            pass
        self.compare.updateSelafinValue()
        

        
    def start(self):
        #self.compare = getCompareValue(self.layer)
        self.compare.moveToThread(self.thread)
        self.compare.finished.connect(self.workerFinished)
        #self.compare.status.connect(self.writeOutput)
        self.thread.started.connect(self.compare.updateSelafinValue)
        #self.compare.finished.connect(self.compare.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.compare.finished.connect(self.thread.quit)
        self.thread.start()
        
    def writeOutput(self,str1):
        self.layer.propertiesdialog.textBrowser_2.append(str(str1))
    
    def workerFinished(self):
        self.layer.propertiesdialog.checkBox_6.setEnabled(True)
    


