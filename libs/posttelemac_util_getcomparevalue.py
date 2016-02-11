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

#from ..libs_telemac.utils.files import getFileContent
#from ..libs_telemac.parsers.parserSortie import getValueHistorySortie
#from ..libs_telemac.parsers.parserSELAFIN import getValueHistorySLF,   getValuePolylineSLF,subsetVariablesSLF
#from ..libs_telemac.parsers.parserSELAFIN import SELAFIN

#from ..libs_telemac.parsers.parserStrings import parseArrayPaires
#imports divers
import threading
from time import ctime
import math
from os import path
from shapely.geometry import Polygon
import sys
import os.path
from matplotlib import tri
from ..posttelemacparsers.posttelemac_selafin_parser import *

#*************************************************************************


class getCompareValue(QtCore.QObject):

    def __init__(self,layer):
        QtCore.QObject.__init__(self)
        self.layer = layer
        #self.slf1 = layer.slf
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.toPlainText())
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.text())
        self.hydrauparsercompared = PostTelemacSelafinParser()
        self.hydrauparsercompared.loadHydrauFile(layer.propertiesdialog.lineEdit_5.text())
        #layer.compare = True
        
        #layer.updatevalue.connect(self.updateSelafinValue)
        self.triinterp=None
        #self.comparetime = None
        self.values = None
        #self.transmitvalues = False
        #self.var_corresp = var_corresp

                
    def reset_dialog(self):
        self.layer.propertiesdialog.textEdit_2.clear()
        self.layer.propertiesdialog.textEdit_3.clear()
        self.layer.propertiesdialog.lineEdit_5.clear()
        self.layer.propertiesdialog.lineEdit.clear()
        self.layer.propertiesdialog.checkBox_6.setCheckState(0)
        self.layer.propertiesdialog.checkBox_6.setEnabled(False)
        
    def oppositeValues(self):
        self.values = -self.values
        
    def updateSelafinValue(self,onlyparamtimeunchanged = -1):
        temp1 = []
        lenvarnames = len(self.layer.parametres)
        meshx1,meshy1 = self.layer.hydrauparser.getMesh()
        ikle1 = self.layer.hydrauparser.getIkle()
        meshx2,meshy2 = self.hydrauparsercompared.getMesh()
        ikle2 = self.hydrauparsercompared.getIkle()


        try:
            #desactive non matching parameters
            if onlyparamtimeunchanged < 0 : 
                if (np.array_equal(ikle1 , ikle2) 
                    and np.array_equal(meshx1 , meshx2) 
                    and np.array_equal(meshy1 , meshy2)):
                    
                    #self.status.emit("fichiers identiques ")
                    self.layer.propertiesdialog.textBrowser_2.append("fichiers identiques ")
                    valuetab = []
                    for i in range(lenvarnames):
                        if self.layer.parametres[i][3] is not None :
                            value = self.hydrauparsercompared.getValues(self.layer.time_displayed)[self.layer.parametres[i][3]] - self.layer.getValues(self.layer.time_displayed)[i]
                        else:
                            value = [np.nan]*len(meshx1)
                            value = np.array(value).transpose()
                        valuetab.append(value)
                    self.values = np.array(valuetab)
                    
                    if self.layer.propertiesdialog.comboBox_compare_method.currentIndex() == 1:
                        self.oppositeValues()
                    

                else:
                    #self.status.emit("fichiers non egaux")
                    self.layer.propertiesdialog.textBrowser_2.append("fichiers non egaux")

                    #projection of slf2 to slf1
                    #triinterp
                    triang = tri.Triangulation(meshx2,meshy2,np.array(ikle2))
                    self.triinterp = []
                    for i in range(lenvarnames):
                        if self.layer.parametres[i][3] is not None:
                            self.triinterp.append(tri.LinearTriInterpolator(triang, self.hydrauparsercompared.getValues(self.layer.time_displayed)[self.layer.parametres[i][3]]))
                        else:
                            self.triinterp.append(None)
                    valuesslf2 = []
                    count = self.layer.hydrauparser.pointcount
                    #projection for matching parameters
                    tabtemp=[]
                    for  j in range(lenvarnames):
                        if self.layer.parametres[j][3] is not None:
                            tabtemp = self.triinterp[j].__call__(meshx1,meshy1)
                        else:
                            tabtemp = np.array([np.nan]*count)
                            tabtemp = tabtemp.transpose()
                        valuesslf2.append(tabtemp)
                    temp1 = valuesslf2 - self.layer.getValues(self.layer.time_displayed)
                    self.values = np.nan_to_num(temp1)
                    
                    if self.layer.propertiesdialog.comboBox_compare_method.currentIndex() == 1:
                        self.oppositeValues()
                        
                        
                self.layer.values = self.values
                self.layer.value = self.values[self.layer.param_displayed]
            else:
                self.layer.value = self.values[self.layer.param_displayed]
                

                
        except Exception, e:
            print str("updateSelafinValue :"+str(e))
            #self.status.emit("updateSelafinValue :"+str(e))
            self.values = None
            #self.finished.emit()
                

        #self.comparetime = self.layer.time_displayed



    


