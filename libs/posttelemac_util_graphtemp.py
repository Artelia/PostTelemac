# -*- coding: utf-8 -*-

#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import numpy
from numpy import *
import numpy as np
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui
#imports divers
from time import ctime
import math
import sys
import os.path
from scipy.spatial import cKDTree

debug = False


#*********************************************************************************************
#*************** Classe de traitement **********************************************************
#********************************************************************************************

        
class graphTemp(QtCore.QObject):
    
    def __init__(self, selafin, qgspoints, compare):
        
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.points = qgspoints
        #self.skdtree = None
        self.compare = compare


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
                    
                    param=self.selafinlayer.propertiesdialog.comboBox_parametreschooser.currentIndex()
                    #param = self.selafinlayer.propertiesdialog.getTreeWidgetSelectedIndex(self.selafinlayer.propertiesdialog.treeWidget_parameters)[1]
                    if self.selafinlayer.parametres[param][2]:
                        dico = self.getDico(self.selafinlayer.parametres[param][2], self.selafinlayer.parametres, self.selafinlayer.values,enumpoint)
                        tempordonees = eval(self.selafinlayer.parametres[param][2],{}, dico)
                    else:
                        #tempordonees = self.selafinlayer.slf.getSERIES([enumpoint + 1],[param],False)   #points in getseries begin with 1
                        #tempordonees = self.selafinlayer.hydrauparser.getTimeSerie([enumpoint + 1],[param])   #points in getseries begin with 1
                        tempordonees = self.getGraphTempSeries([enumpoint + 1],[param])   #points in getseries bein with 1
                    ordonnees = tempordonees[0][0].tolist()
                    list1.append(abscisse)
                    list2.append(ordonnees)
            self.finished.emit(list1,list2)
        except Exception, e:
            self.status.emit(str(e))
            self.finished.emit([],[])
        
        
    def getDico(self,expr, parametres, values,enumpoint):
        dico = {}
        try:

            dico['sin'] = sin
            dico['cos'] = cos
            dico['abs'] = abs
            dico['int'] = int
            dico['if_then_else'] = self.selafinlayer.if_then_else
            a = 'V{}'
            nb_var = len(values)
            i = 0
            num_var = 0
            while num_var < nb_var:
                if not parametres[i][2]:
                    #dico[a.format(i)] = self.selafinlayer.hydrauparser.getTimeSerie([enumpoint + 1],[i])
                    dico[a.format(i)] = self.getGraphTempSeries([enumpoint + 1],[i])
                num_var += 1
                i += 1
        except Exception, e:
            print str(e)
        return dico
        
    def getGraphTempSeries(self,num,param):
        if self.compare :
            x,y = self.selafinlayer.hydrauparser.getXYFromNumPoint(num)[0]
            triangles,numpointsfinal,pointsfinal,coef = self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getInterpFactorInTriangleFromPoint([x],[y])
            layer2serie = 0
            for i, numpoint in enumerate(numpointsfinal[0]):
                layer2serie += float(coef[0][i]) * self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getTimeSerie([numpoint],[self.selafinlayer.parametres[param[0]][3]])
            layer1serie = self.selafinlayer.hydrauparser.getTimeSerie(num,param)
            return layer2serie  - layer1serie
        else:
            return self.selafinlayer.hydrauparser.getTimeSerie(num,param)
        


     
     
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(list,list)
    emitpoint = QtCore.pyqtSignal(float,float)

      

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

    def start(self, selafin,
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
    
    
    