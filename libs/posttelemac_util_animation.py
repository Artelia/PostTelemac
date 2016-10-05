# -*- coding: utf-8 -*-

#unicode behaviour
from __future__ import unicode_literals
#import numpy
import numpy as np
import matplotlib
#import matplotlib
#import PyQT
from PyQt4 import QtCore, QtGui
import qgis.utils
import qgis.core
#imports divers
import time
import os
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
            qgis.utils.iface.mapCanvas().freeze(True)
            
            txt = time.ctime()+ " Film - NE PAS MODIFIER L'ESPACE DESSIN DURANT L'OPERATION "
            if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
            else: self.status.emit(txt)
            
            #Cherche le composeur voulu
            for composeurview in qgis.utils.iface.activeComposers():
                if composeurview.composerWindow().windowTitle() == self.pluginlayer.propertiesdialog.comboBox_compositions.currentText():
                    composition = composeurview.composition()
            
            #Cree les paths souhaités
            self.tempdir = tempfile.mkdtemp()   #path to temp dir where png are stored
            dir = os.path.dirname(self.pluginlayer.hydraufilepath)  #dir of sl file where movie will be put"
            nameslf =  os.path.basename(self.pluginlayer.hydraufilepath).split('.')[0]
            nameavi = os.path.join(dir,nameslf+'.avi')

            txt = time.ctime()+ ' - Film - creation du fichier ' + str(nameavi)
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
            self.fig = None
            maps = [item for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerMap and item.scene()]
            images = [item for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerPicture and item.scene()]
            legends = [item for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerLegend and item.scene()]
            
            if self.pluginlayer.propertiesdialog.comboBox_8.currentIndex() != 0:
                for image in images:
                    if image.id() == self.pluginlayer.propertiesdialog.comboBox_8.currentText():
                        composeurimage = image
                        rectimage = np.array([composeurimage.rectWithFrame().width(),composeurimage.rectWithFrame().height()])    #size img in mm in composer width
                if self.pluginlayer.propertiesdialog.comboBox_9.currentIndex() == 0 :
                    self.fig = self.pluginlayer.propertiesdialog.figure1
                    canvas = self.pluginlayer.propertiesdialog.canvas1
                    ax = self.pluginlayer.propertiesdialog.ax
                elif self.pluginlayer.propertiesdialog.comboBox_9.currentIndex() == 1 :
                    self.fig = self.pluginlayer.propertiesdialog.figure2
                    canvas = self.pluginlayer.propertiesdialog.canvas2
                    ax = self.pluginlayer.propertiesdialog.ax2
                
                #making the figure the size of the image
                rectfig = [self.fig.get_size_inches()[0],self.fig.get_size_inches()[1]]
                facteurconversion = float(composition.printResolution())/80.0
                rectimage = rectimage/25.4*facteurconversion
                self.fig.set_size_inches(float(rectimage[0]),float(rectimage[1]), forward=True)
                
                #search matplotlib supported format
                tempmplsupportedfile =  self.fig.canvas.get_supported_filetypes()
                if 'svg' in tempmplsupportedfile:
                    mplformat = 'svg'
                elif 'jpg' in tempmplsupportedfile:
                    mplformat = 'jpg'
                elif 'png' in tempmplsupportedfile:
                    mplformat = 'png'

            
            #Main part : creating the png files ******************************************
            

                
            
            compt = 0
            for i in range(min1,max1+1):
                if i%pas==0:
                    if self.fig != None:
                        try:
                            if False:
                                #modifying ax to show the time
                                self.addtimelineonax(ax,self.pluginlayer.hydrauparser.getTimes()[i])
                                #saving the figure
                                matplotlibimagepath= os.path.join(self.tempdir,'test'+ "%04d"%compt +'.jpg')
                                #print str(matplotlibimagepath)
                                self.fig.savefig(matplotlibimagepath,format='jpg',dpi = 80 )
                                #fig.savefig(matplotlibimagepath )
                            else:
                                #modifying ax to show the time
                                self.addtimelineonax(ax,self.pluginlayer.hydrauparser.getTimes()[i])
                                #saving the figure
                                matplotlibimagepath= os.path.join(self.tempdir,'test'+ "%04d"%compt +'.' + mplformat)
                                #print str(matplotlibimagepath)
                                #fig.savefig(matplotlibimagepath,format='png',dpi = 80 )
                                #fig.canvas.print_figure(matplotlibimagepath,format='png',dpi = 80 )
                                self.fig.canvas.print_figure(matplotlibimagepath,dpi = 80 )
                                #fig.savefig(matplotlibimagepath )
                            #print 'ok1_2'
                            composeurimage.setPicturePath(matplotlibimagepath)
                        except Exception, e:
                            #print 'saveimg ' + str(e)
                            pass
                    
                    self.pluginlayer.changeTime(i)
                    txt = time.ctime()+ ' - Film - iteration n '+ str(self.pluginlayer.time_displayed)
                    if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                    else: self.status.emit(txt)
                    
                    #print 'ok3'
                    
                    #Update drawing space and composer space
                    self.pluginlayer.triggerRepaint()
                    for map in maps:
                        map.updateItem()
                    
                    #format='jpg'
                    formatcomposer='png'
                    finlename='img'+"%04d"%compt + '.' + formatcomposer
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
                        
                        
                    #image.save(filename1,format)
                    image.save(filename1)

                    if compt == 0:
                        #image.save(os.path.join(dir,nameslf+'_preview.'+format),format)
                        image.save(os.path.join(dir,nameslf+'_preview.'+formatcomposer))
                        txt =time.ctime()+ ' - Film - previsulation du film ici : ' + str(os.path.join(dir,nameslf+'_preview.' + formatcomposer))
                        if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                        else: self.status.emit(txt)
                    
                    compt = compt + 1
            
            tmp_img_dir = os.path.join(self.tempdir,'img%04d.'+formatcomposer)
            
            #Create the video *****************************************
            output_file = nameavi
            ffmpeg_res, logfile = self.images_to_video(tmp_img_dir,output_file,fps)
            if ffmpeg_res:
                shutil.rmtree(self.tempdir)
                txt =(time.ctime()+ ' - Film - fichier cree ' + str(nameavi))
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
                
            else:
                txt = time.ctime()+ ' - Film - erreur '
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
                
            qgis.utils.iface.mapCanvas().freeze(False)
        
        except Exception, e : 
            txt =str(e)
            if self.outputtype : self.pluginlayer.propertiesdialog.textBrowser_2.append('make movie : ' + txt)
            else : self.status.emit('make movie : ' + txt)
        
        if self.fig:
            if self.vline:
                ax.lines.remove(self.vline)
            self.fig.set_size_inches(rectfig[0],rectfig[1],forward=True)
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