# -*- coding: utf-8 -*-

#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import numpy
import numpy as np
#import matplotlib
import matplotlib
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui

#imports divers
from time import ctime
import os.path
import tempfile
import subprocess
import shutil



class PostTelemacAnimation(QtCore.QObject):

    def __init__(self,slf):
        QtCore.QObject.__init__(self)
        self.pluginlayer = slf
        self.tempdir = None
        self.fig = None
        self.vline = None
        self.outputtype = 1

        
    def makeFilm(self):
        try:
            
            self.pluginlayer.propertiesdialog.tabWidget.setCurrentIndex(2)
            iface.mapCanvas().freeze(True)
            
            txt = ctime()+ " Film - NE PAS MODIFIER L'ESPACE DESSIN DURANT L'OPERATION "
            if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
            else: self.status.emit(txt)
            
            #Cherche le composeur voulu
            for composeurview in iface.activeComposers():
                if composeurview.composerWindow().windowTitle() == self.pluginlayer.propertiesdialog.comboBox_compositions.currentText():
                    composition = composeurview.composition()
            
            #Cree les paths souhaités
            self.tempdir = tempfile.mkdtemp()   #path to temp dir where png are stored
            dir = os.path.dirname(self.pluginlayer.hydraufilepath)  #dir of sl file where movie will be put"
            nameslf =  os.path.basename(self.pluginlayer.hydraufilepath).split('.')[0]
            nameavi = os.path.join(dir,nameslf+'.avi')

            txt = ctime()+ ' - Film - creation du fichier ' + str(nameavi)
            if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
            else: self.status.emit(txt)
            
            #init max, min , time step
            min1 = self.pluginlayer.propertiesdialog.spinBox_2.value()
            max1 = self.pluginlayer.propertiesdialog.spinBox_3.value()
            pas = self.pluginlayer.propertiesdialog.spinBox_4.value()
            fps =  self.pluginlayer.propertiesdialog.spinBox_fps.value()
            
            #Init matplotlib things if an image is choosen **************************************************************************
            ax = None
            matplotlibimagepath = None
            fig = None
            maps = [item for item in composition.items() if item.type() == QgsComposerItem.ComposerMap and item.scene()]
            images = [item for item in composition.items() if item.type() == QgsComposerItem.ComposerPicture and item.scene()]
            legends = [item for item in composition.items() if item.type() == QgsComposerItem.ComposerLegend and item.scene()]
            if self.pluginlayer.propertiesdialog.comboBox_8.currentIndex() != 0:
                for image in images:
                    if image.id() == self.pluginlayer.propertiesdialog.comboBox_8.currentText():
                        composeurimage = image
                        rectimage = np.array([composeurimage.rectWithFrame().width(),composeurimage.rectWithFrame().height()])    #size img in mm in composer width
                if self.pluginlayer.propertiesdialog.comboBox_9.currentIndex() == 0 :
                    fig = self.pluginlayer.propertiesdialog.figure1
                    canvas = self.pluginlayer.propertiesdialog.canvas1
                    ax = self.pluginlayer.propertiesdialog.ax
                elif self.pluginlayer.propertiesdialog.comboBox_9.currentIndex() == 1 :
                    fig = self.pluginlayer.propertiesdialog.figure2
                    canvas = self.pluginlayer.propertiesdialog.canvas2
                    ax = self.pluginlayer.propertiesdialog.ax2
                
                #making the figure the size of the image
                rectfig = [fig.get_size_inches()[0],fig.get_size_inches()[1]]
                facteurconversion = float(composition.printResolution())/80.0
                rectimage = rectimage/25.4*facteurconversion
                fig.set_size_inches(float(rectimage[0]),float(rectimage[1]), forward=True)

            
            #Main part : creating the png files ******************************************
            compt = 0
            for i in range(min1,max1+1):
                if i%pas==0:
                    if fig:
                        #modifying ax to show the time
                        self.addtimelineonax(ax,self.pluginlayer.hydrauparser.getTimes()[i])
                        #saving the figure
                        matplotlibimagepath= os.path.join(self.tempdir,'test'+ "%04d"%compt +'.jpg')
                        fig.savefig(matplotlibimagepath,format='jpg',dpi = 80 )
                        composeurimage.setPicturePath(matplotlibimagepath)
                    self.pluginlayer.changeTime(i)
                    txt =ctime()+ ' - Film - iteration n '+ str(self.pluginlayer.time_displayed)
                    if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                    else: self.status.emit(txt)
                    
                    #Update drawing space and composer space
                    self.pluginlayer.triggerRepaint()
                    for map in maps:
                        map.updateItem()
                    
                    format='jpg'
                    finlename='img'+"%04d"%compt + '.' + format
                    filename1 = os.path.join(self.tempdir,finlename)
                    
                    if True:
                        image = composition.printPageAsRaster(0)
                    else:   #test
                        width = (composition.printResolution() * composition.paperWidth() / 25.4 )
                        height =( composition.printResolution() * composition.paperHeight() / 25.4 )
                        image = QImage( QSize( width, height ), QImage.Format_ARGB32 )
                        image.setDotsPerMeterX( composition.printResolution() / 25.4 * 1000 )
                        image.setDotsPerMeterY( composition.printResolution() / 25.4 * 1000 )
                        image.fill( 0 )
                        imagePainter = QPainter( image )
                        composition.renderPage( imagePainter, 0 )
                        for legend in legends :
                            s = legend.paintAndDetermineSize(imagePainter)
                        
                        
                    image.save(filename1,format)

                    if compt == 0:
                        image.save(os.path.join(dir,nameslf+'_preview.'+format),format)
                        txt =ctime()+ ' - Film - previsulation du film ici : ' + str(os.path.join(dir,nameslf+'_preview.' + format))
                        if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                        else: self.status.emit(txt)
                    
                    compt = compt + 1
            
            tmp_img_dir = os.path.join(self.tempdir,'img%04d.'+format)
            
            #Create the video *****************************************
            output_file = nameavi
            ffmpeg_res, logfile = self.images_to_video(tmp_img_dir,output_file,fps)
            if ffmpeg_res:
                shutil.rmtree(self.tempdir)
                txt =(ctime()+ ' - Film - fichier cree ' + str(nameavi))
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
                
            else:
                txt =ctime()+ ' - Film - erreur '
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
                
            iface.mapCanvas().freeze(False)
        
        except Exception, e : 
            txt =str(e)
            if self.outputtype : self.pluginlayer.propertiesdialog.textBrowser_2.append('make movie : ' + txt)
            else : self.status.emit('make movie : ' + txt)

        if fig:
            if self.vline:
                ax.lines.remove(self.vline)
            fig.set_size_inches(rectfig[0],rectfig[1],forward=True)
            canvas.draw()

        self.finished.emit()
        
    def images_to_video(self,tmp_img_dir= "/tmp/vid/%03d.png", output_file="/tmp/vid/test.avi", fps=10, qual=1, ffmpeg_bin="ffmpeg"):
        #print 'im ' + str(tmp_img_dir) + ' output ' + str(output_file)


        if qual == 0: # lossless
            opts = ["-vcodec", "ffv1"]
        else:
            bitrate = 10000 if qual == 1 else 2000
            opts = ["-vcodec", "mpeg4", "-b", str(bitrate) + "K"]

        # if images do not start with 1: -start_number 14
        cmd = [ffmpeg_bin, "-f", "image2", "-framerate", str(fps), "-i", tmp_img_dir]
        cmd += opts
        cmd += ["-r", str(fps), "-f", "avi", "-y", output_file]
        #f = os.mknod(os.path.join(os.path.dirname(tmp_img_dir),"newfile.txt"))
        f= open (os.path.join(os.path.dirname(tmp_img_dir),"newfile.txt"), 'a')
        #f.close()

        #f = tempfile.NamedTemporaryFile(prefix="crayfish",suffix=".txt")
        
        f.write(unicode(cmd).encode('utf8') + "\n\n")

        # stdin redirection is necessary in some cases on Windows
        res = subprocess.call(cmd, shell = True, stdin=subprocess.PIPE, stdout=f, stderr=f)
        if res != 0:
            #f.delete = False  # keep the file on error
            f.close()

        return res == 0, f.name
        
        
    def addtimelineonax(self,ax1,time1):
        if self.vline:
            ax1.lines.remove(self.vline)
        self.vline = ax1.axvline(time1,linewidth=2, color = 'k')
        
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    printimage = QtCore.pyqtSignal(str,str,int,str)
 

    
"""
class initPostTelemacAnimation(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None

    def start(self,                 
                 selafin):
        #Launch worker
        self.worker = PostTelemacAnimation(selafin)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.makeFilm)
        self.worker.status.connect(self.writeOutput)
        #self.worker.printimage.connect(self.printImage)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self):
        self.finished1.emit()
        
    def printImage(self,str1,str2,int1,str3):
        self.printimage.emit(str1,str2,int1,str3)

    printimage = QtCore.pyqtSignal(str,str,int,str)
    status = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal()
"""