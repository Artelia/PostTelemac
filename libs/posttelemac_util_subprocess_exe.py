# -*- coding: utf-8 -*-

#import PyQT
from PyQt4 import QtCore, QtGui

#imports divers
import os
import subprocess




class runSubprocess(QtCore.QObject):

    def __init__(self,slf,path_to_exe):
        QtCore.QObject.__init__(self)
        self.pluginlayer = slf
        self.path_to_exe = path_to_exe
        
        
    def run(self):
        self.pluginlayer.propertiesdialog.tabWidget.setCurrentIndex(2)
        self.status.emit(str(self.path_to_exe))
        if os.path.basename(self.path_to_exe) == 'PPR.exe':
            try:
                p = subprocess.Popen(self.path_to_exe, shell = True, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                temp = str(p.stdout.readline())
                self.status.emit(str(temp))
                
                bool=False
                while bool == False:
                    temp = str(p.stdout.readline())
                    self.status.emit(str(temp))
                    if 'fichier' in temp:
                        bool = True
                
                p.stdin.write(str(self.pluginlayer.fname) + '\n')
                self.status.emit(str(self.pluginlayer.fname))
                
                while True:
                    next_line = p.stdout.readline()
                    self.status.emit(str(next_line))
                    if not next_line:
                        while True:
                            next_line = p.stderr.readline()
                            self.status.emit(str(next_line))
                            if not next_line:
                                break
                        break
                    else:
                        if next_line.strip() !='':
                            self.status.emit(str(next_line))

                self.finished.emit(self.pluginlayer.fname.split('.')[0] + '_MAX_PPR.res')
                
            except Exception, e:
                self.status.emit('erreur subprocess : '+str(e))
                self.finished.emit(None)
                
        else:
            self.finished.emit(None)
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)
    
    
class initRunSubprocess(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None

    def start(self,                 
                 selafin,path_to_exe):
        #Launch worker
        self.worker = runSubprocess(selafin,path_to_exe)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.writeOutput)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self,str1):
        self.finished1.emit(str1)

    status = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(str)
    