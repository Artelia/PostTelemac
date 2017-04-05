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
 get Image class
 Generate a Qimage from selafin file to be displayed in map canvas 
 with tht draw method of posttelemacpluginlayer
 
Versions :
0.0 : debut

 ***************************************************************************/
"""


from qgis.PyQt import uic, QtCore, QtGui
from .meshlayer_abstract_tool import *
import qgis
import time
import tempfile
import subprocess
import shutil
import numpy as np

from ..meshlayerlibs import pyqtgraph 
from ..meshlayerlibs.pyqtgraph import exporters 

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'AnimationTool.ui'))



class AnimationTool(AbstractMeshLayerTool,FORM_CLASS):
    
    NAME = 'ANIMATIONTOOL'


    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        #self.setupUi(self)
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Video_48x48.png' )
        
        self.pushButton_film.clicked.connect(self.makeAnimation)
        qgis.utils.iface.composerAdded.connect(self.reinitcomposeurlist)
        qgis.utils.iface.composerRemoved.connect(self.reinitcomposeurlist)
        self.comboBox_compositions.currentIndexChanged.connect(self.reinitcomposeurimages)
        self.comboBox_8.installEventFilter(self)
        self.spinBox_2.valueChanged.connect(self.filmEstimateLenght)
        self.spinBox_3.valueChanged.connect(self.filmEstimateLenght)
        self.spinBox_4.valueChanged.connect(self.filmEstimateLenght)
        self.spinBox_fps.valueChanged.connect(self.filmEstimateLenght)

        
    def onActivation(self):
        self.reinitcomposeurlist()
        self.reinitcomposeurimages(0)
        
        maxiter = self.meshlayer.hydrauparser.itertimecount
        self.spinBox_3.setMaximum(maxiter)
        self.spinBox_2.setMaximum(maxiter)
        self.spinBox_3.setValue(maxiter)
        
        desactivatetemptool = False
        desactiveflowtool = True
        
        for tool in self.propertiesdialog.tools:
            if tool.__class__.__name__ == 'TemporalGraphTool':
                desactivatetemptool = False
            if tool.__class__.__name__ == 'FlowTool':
                desactiveflowtool = False
                
        if desactivatetemptool:
            self.comboBox_9.model().item(0).setEnabled(False)
        if desactiveflowtool:
            self.comboBox_9.model().item(0).setEnabled(False)

    def onDesactivation(self):
        pass

        

    def makeAnimation(self):
        self.initclass = PostTelemacAnimation(self.meshlayer,self)
        self.initclass.makeFilm()

    def filmEstimateLenght(self,int=None):
        lenght = (self.spinBox_3.value() - self.spinBox_2.value())/self.spinBox_4.value()/self.spinBox_fps.value()
        self.label_tempsvideo.setText(str(lenght))
        
        
    def reinitcomposeurlist(self,composeurview1=None):
        """
        update composer list in movie page when a new composer is added
        """
        try:
            self.comboBox_compositions.clear()
            for composeurview in qgis.utils.iface.activeComposers():
                name = composeurview.composerWindow().windowTitle()
                self.comboBox_compositions.addItems([str(name)])
        except Exception as e :
            self.comboBox_compositions.addItems([self.tr("no composer")])
        

    def reinitcomposeurimages(self,int1=None):
        """
        update image list in movie page when images' combobox is clicked
        """
        self.comboBox_8.clear()
        name = self.comboBox_compositions.currentText()
        #print name
        try:
            composition = None
            for composeurview in qgis.utils.iface.activeComposers():
                if composeurview.composerWindow().windowTitle() == name:
                    composition = composeurview.composition()
                
            self.comboBox_8.addItems([self.tr('no picture')])
            
            if composition != None:
                images = [item.id() for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerPicture and item.scene()] 
                images=[str(image) for image in images]
                self.comboBox_8.addItems(images)
        except Exception as e :
            print( str(e) )
            self.comboBox_8.addItems([self.tr('no picture')])
            
            

            
    def eventFilter(self,target,event):
        """
        event for specific actions
        Used only for movie utilities - update images in composer
        """
        #Action to update images in composer with movie tool
        try:
            if target == self.comboBox_8 and event.type() == QtCore.QEvent.MouseButtonPress:
                self.reinitcomposeurimages()
            return False
        except Exception as e:
            return False
        


class PostTelemacAnimation(QtCore.QObject):

    def __init__(self,slf,tool):
        QtCore.QObject.__init__(self)
        self.pluginlayer = slf
        self.tempdir = None
        self.fig = None
        self.vline = None
        self.outputtype = 1
        self.tool = tool

        
    def makeFilm(self):
            
        self.pluginlayer.propertiesdialog.tabWidget.setCurrentIndex(2)
        qgis.utils.iface.mapCanvas().freeze(True)
        
        txt = time.ctime()+ " Film - NE PAS MODIFIER L'ESPACE DESSIN DURANT L'OPERATION "
        if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
        else: self.status.emit(txt)
        
        #Cherche le composeur voulu
        for composeurview in qgis.utils.iface.activeComposers():
            if composeurview.composerWindow().windowTitle() == self.tool.comboBox_compositions.currentText():
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
        min1 = self.tool.spinBox_2.value()
        max1 = self.tool.spinBox_3.value()
        pas = self.tool.spinBox_4.value()
        fps =  self.tool.spinBox_fps.value()
        
        #Init graph things if an image is choosen **************************************************************************
        matplotlibimagepath = None
        pitem = None
        maps = [item for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerMap and item.scene()]
        images = [item for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerPicture and item.scene()]
        legends = [item for item in composition.items() if item.type() == qgis.core.QgsComposerItem.ComposerLegend and item.scene()]
        
        if self.tool.comboBox_8.currentIndex() != 0:
            tooltemp = None
            for image in images:
                if image.id() == self.tool.comboBox_8.currentText():
                    composeurimage = image
                    rectimage = np.array([composeurimage.rectWithFrame().width(),composeurimage.rectWithFrame().height()])    #size img in mm in composer width
            if self.tool.comboBox_9.currentIndex() == 0 :
                for tool in self.pluginlayer.propertiesdialog.tools:
                    if tool.__class__.__name__ == 'TemporalGraphTool':
                        toolused = tool
                        pitem = tool.pyqtgraphwdg.getPlotItem()
                        break
            elif self.tool.comboBox_9.currentIndex() == 1 :
                for tool in self.pluginlayer.propertiesdialog.tools:
                    if tool.__class__.__name__ == 'FlowTool':
                        toolused = tool
                        pitem = tool.pyqtgraphwdg.getPlotItem()
                        break
            
            if pitem != None :
                #making the figure the size of the image
                toolused.removeCursor()
                initialrect = pitem.geometry()
                rectfig = [ initialrect.width(), initialrect.height()]
                facteurconversion = float(composition.printResolution())
                rectimage = rectimage/25.4*facteurconversion
                pitem.setGeometry(0,0, int(rectimage[0]) , int(rectimage[1] ) )
                imageformat = 'png'

        
        #Main part : creating the png files ******************************************
        

        compt = 0
        for i in range(min1,max1+1):
            if i%pas==0:
                if pitem != None:
                    #saving the figure
                    matplotlibimagepath= os.path.join(self.tempdir,'test'+ "%04d"%compt +'.' + imageformat)
                    exporter =  exporters.ImageExporter(pitem)
                    exporter.export(matplotlibimagepath)
                    
                    if False and compt == 0 :
                        exporter.export('C://00_Bureau//data2//essai1.png')
                    
                    if False:
                        ex = exporters.SVGExporter(sc)
                        ex.export(fileName=matplotlibimagepath)
                            
                    composeurimage.setPicturePath(matplotlibimagepath)

                self.pluginlayer.changeTime(i)
                txt = time.ctime()+ ' - Film - iteration n '+ str(self.pluginlayer.time_displayed)
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
                
                
                #Update drawing space and composer space
                self.pluginlayer.triggerRepaint()
                
                for map in maps:
                    map.updateItem()
                
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
                    
                    
                image.save(filename1)

                if compt == 0:
                    image.save(os.path.join(dir,nameslf+'_preview.'+formatcomposer))
                    txt =time.ctime()+ ' - Film - previsulation du film ici : ' + str(os.path.join(dir,nameslf+'_preview.' + formatcomposer))
                    if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                    else: self.status.emit(txt)
                
                compt = compt + 1
        
        tmp_img_dir = os.path.join(self.tempdir,'img%04d.'+formatcomposer)
            
            
        try: 
            #Create the video *****************************************
            output_file = nameavi
            ffmpeg_res, logfile = self.images_to_video(tmp_img_dir,output_file,fps)
            if ffmpeg_res:
                #shutil.rmtree(self.tempdir)
                txt =(time.ctime()+ ' - Film - fichier cree ' + str(nameavi))
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
                
            else:
                txt = time.ctime()+ ' - Film - erreur '
                
                if self.outputtype:self.pluginlayer.propertiesdialog.textBrowser_2.append(txt)
                else: self.status.emit(txt)
            
            shutil.rmtree(self.tempdir)
            qgis.utils.iface.mapCanvas().freeze(False)
            
        except Exception as e : 
            txt =str(e)
            if self.outputtype : self.pluginlayer.propertiesdialog.textBrowser_2.append('make movie : ' + txt)
            else : self.status.emit('make movie : ' + txt)
        
        
        
        if pitem :
            toolused.appendCursor()
            pitem.setGeometry(initialrect )

        self.finished.emit()
        
        
        
    def images_to_video(self,tmp_img_dir= "/tmp/vid/%03d.png", output_file="/tmp/vid/test.avi", fps=10, qual=1, ffmpeg_bin="ffmpeg"):

        if qual == 0: # lossless
            opts = ["-vcodec", "ffv1"]
        else:
            bitrate = 10000 if qual == 1 else 2000
            opts = ["-vcodec", "mpeg4", "-b", str(bitrate) + "K"]
        

        # if images do not start with 1: -start_number 14
        cmd = [ffmpeg_bin, "-f", "image2", "-framerate", str(fps), "-i", tmp_img_dir]
        cmd += opts
        cmd += ["-r", str(fps), "-f", "avi", "-y", output_file]
        f= open (os.path.join(os.path.dirname(tmp_img_dir),"newfile.txt"), 'a')

        try:    #python 2
            f.write(unicode(cmd).encode('utf8') + "\n\n")
        except: #python 3
            f.write(unicode(cmd) + "\n\n")

        # stdin redirection is necessary in some cases on Windows
        res = subprocess.call(cmd, shell = False, stdin=subprocess.PIPE, stdout=f, stderr=f)
            
        if res != 0:
            #f.delete = False  # keep the file on error
            f.close()

        return res == 0, f.name
            
        
        
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    printimage = QtCore.pyqtSignal(str,str,int,str)
 