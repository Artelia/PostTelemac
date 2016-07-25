# -*- coding: utf-8 -*-

#unicode behaviour
from __future__ import unicode_literals
#import PyQT
from PyQt4 import QtCore
#imports divers
import sys
import os

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
    
    
    