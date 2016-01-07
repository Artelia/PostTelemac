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

#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import matplotlib
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import tri
#import numpy
import numpy as np
#import PyQT
from PyQt4 import  QtGui, QtCore
#other imports
from time import ctime
import cStringIO
import gc
import time

DEBUG = True


class Selafin2QImage():

    def __init__(self,int=1):
        self.fig =  plt.figure(int)
        self.ax = self.fig.add_subplot(111)
        self.tricontourf1 = None
        self.meshplot = None
        self.tritemp = None
        self.mask = None
        self.image_mesh = None

        
    def getimage(self,selafinlayer,rendererContext):
        """
        Generate a qimage depanding on variables in selafin layer
        3 methods :
            first : map is just panned
            second : selfin parameters are changed
            third : mapcanvas dimension are changed
        """
        timestart = time.clock()
        time1=[]
        ratio = selafinlayer.propertiesdialog.doubleSpinBox_aspectratio.value()
        #Compute renderer extent
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())]
        mupp = float(rendererContext.mapToPixel().mapUnitsPerPixel())
        sizepx = [ round(((rect[1] - rect[0] )/mupp/ratio),2) , round(((rect[3]  - rect[2] )/mupp/ratio),2) ]
        dpi1 = rendererContext.painter().device().logicalDpiX()
        dpi2 =dpi1
        #matplotlib figure dimension
        width= (sizepx[0])/dpi1
        lenght = (sizepx[1])/dpi1
        #buffer for qimage
        buf = cStringIO.StringIO()

        #Working with CRS - todo
        ct = rendererContext.coordinateTransform()
        if ct:
            recttemp2 = ct.transformBoundingBox(rendererContext.extent())
            rect2 = [float(recttemp2.xMinimum()), float(recttemp2.xMaximum()), float(recttemp2.yMinimum()), float(recttemp2.yMaximum())]

        if DEBUG and False:   #debug thing
            txt = ('rect '+str(rect)+"\n"+ str(mupp) + "\n"+
                    " px "+str(selafinlayer.renderersizepx)+'/'+str(sizepx) + "\n"+
                                                    ' temps '+str(selafinlayer.temps_memoire)+'/'+str(selafinlayer.temps_gachette) +"\n"
                                                    +'param '+ str(selafinlayer.param_memoire)+ " " +str(selafinlayer.param_gachette))
            
            selafinlayer.propertiesdialog.textBrowser_2.append(txt)
        
        
        try:
            #***********************************************************************
            #Case 1 : mapcanvas panned
            if (selafinlayer.renderersizepx==sizepx and selafinlayer.temps_memoire == selafinlayer.temps_gachette 
                and selafinlayer.param_memoire == selafinlayer.param_gachette 
                and selafinlayer.lvl_gachette == selafinlayer.lvl_memoire and selafinlayer.alpha_gachette == selafinlayer.alpha 
                and selafinlayer.cmap == selafinlayer.cmap_gachette and selafinlayer.forcerefresh == False):
                if DEBUG : time1.append("deplacement")

                if selafinlayer.showvelocityparams['show'] :
                    self.temp.remove()
                    tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                    C = np.sqrt(np.array(tabvx)**2 + np.array(tabvy)**2)
                    self.temp = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                               scale=selafinlayer.showvelocityparams['norm'],
                                               scale_units='xy',
                                               cmap=  selafinlayer.cmap_mpl_vel,
                                               norm=selafinlayer.norm_mpl_vel)
                    if DEBUG : time1.append("quiver : "+str(round(time.clock()-timestart,3)))

                #change view of matplotlib figure
                """
                if not self.mask == None :
                    selafinlayer.triangulation.set_mask(None)
                    self.tricontourf1= self.ax.tricontourf(selafinlayer.triangulation,
                                                       selafinlayer.value,
                                                       selafinlayer.lvl_gachette, 
                                                       mask = self.mask ,
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha/100.0,
                                                       #extent = tuple(rect),
                                                       rasterized=True)
                """
                if not self.tritemp == None :
                    ncollections = len(self.ax.collections)
                    for i in range(ncollections):  
                        self.ax.collections[0].remove()
                    self.fig.canvas.flush_events()
                    gc.collect()
                    #selafinlayer.triangulation.set_mask(None)
                    self.tricontourf1= self.ax.tricontourf(selafinlayer.triangulation,
                                                       selafinlayer.value,
                                                       selafinlayer.lvl_gachette, 
                                                       mask = self.mask ,
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha/100.0,
                                                       rasterized=True)
                    
                
                self.ax.set_ylim([rect[2],rect[3]])
                self.ax.set_xlim([rect[0],rect[1]])
                
                

                
                self.mask = None
                self.tritemp = None
                self.image_mesh = None
                
                if DEBUG : time1.append("deplacement : "+str(round(time.clock()-timestart,3)))


            #***********************************************************************
            #Case 2 : figure changed (time,param) with the same mapcanvas dimension
            elif selafinlayer.renderersizepx==sizepx and selafinlayer.forcerefresh == False :
                #update selafinlayer parameters
                selafinlayer.param_memoire = selafinlayer.param_gachette
                selafinlayer.lvl_memoire=selafinlayer.lvl_gachette
                selafinlayer.temps_memoire=selafinlayer.temps_gachette
                selafinlayer.alpha = selafinlayer.alpha_gachette
                selafinlayer.rendererrect = rect
                selafinlayer.renderersizepx = sizepx
                selafinlayer.cmap_gachette = selafinlayer.cmap
                
                if DEBUG : time1.append("nouveau meme taille")
                if DEBUG : time1.append("avant value : "+str(round(time.clock()-timestart,3)))
                
                #Removing contours
                ncollections = len(self.ax.collections)
                for i in range(ncollections):  
                    self.ax.collections[0].remove()
                self.fig.canvas.flush_events()
                gc.collect()
                
                self.ax.set_ylim([rect[2],rect[3]])
                self.ax.set_xlim([rect[0],rect[1]])
                
                if True:
                    if self.image_mesh == None:
                        print str('mesh')
                        self.image_mesh = self.saveImage(ratio,dpi2)
                        self.ax.cla()
                        self.ax.axes.axis('off')
                    #if self.meshplot : 
                    print str('remove meshplt')
                    try:
                        self.meshplot.remove()
                        self.meshplot = None
                    except Exception, e:
                        pass
                    self.meshplot = None
                
                    if not self.tritemp:
                        #self.mask = self.getMaskMesh2(selafinlayer,rendererContext)
                        self.tritemp, self.goodpointindex = self.getMaskMesh4(selafinlayer,rendererContext)
                        #self.tritemp , goodnum =  self.getTriTemp(selafinlayer,rendererContext)
                        #print str(len(selafinlayer.value[goodnum])) + " " + str(selafinlayer.value[goodnum])
                        
                        
                    self.tricontourf1= self.ax.tricontourf(self.tritemp,
                                                       selafinlayer.value[self.goodpointindex],
                                                       selafinlayer.lvl_gachette, 
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha/100.0,
                                                       #extent = tuple(rect),
                                                       mask = self.mask ,
                                                       rasterized=True)
                """
                if False: 
                    if self.mask == None :
                        self.mask = self.getMaskMesh4(selafinlayer,rendererContext)
                        #self.mask = 1.0
                        #triangle, goodpointindex = self.getMaskMesh4(selafinlayer,rendererContext)
                        #print 'mask ' + str(self.mask)
                        #print str(np.where(self.mask == False))
                        #selafinlayer.triangulation.set_mask(self.mask)
                        
                    self.tricontourf1= self.ax.tricontourf(selafinlayer.triangulation,
                                                       selafinlayer.value[goodpointindex],
                                                       selafinlayer.lvl_gachette, 
                                                       mask = self.mask ,
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha/100.0,
                                                       #extent = tuple(rect),
                                                       rasterized=True)
                                                       
                if False : 
                    if not self.tritemp:
                        self.tritemp , goodnum =  self.getTriTemp(selafinlayer,rendererContext)
                        #print str(len(selafinlayer.value[goodnum])) + " " + str(selafinlayer.value[goodnum]) 
                    self.tricontourf1= self.ax.tricontourf(self.tritemp,
                                                       selafinlayer.value[goodnum],
                                                       selafinlayer.lvl_gachette, 
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha/100.0,
                                                       #extent = tuple(rect),
                                                       #mask = self.mask ,
                                                       rasterized=True)
                        
                    
                """
                """
                if True:
                    self.tricontourf1= self.ax.tricontourf(selafinlayer.triangulation,
                                                       selafinlayer.value,selafinlayer.lvl_gachette, 
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha/100.0,
                                                       #extent = tuple(rect),
                                                       mask = self.mask ,
                                                       rasterized=True)
                else:   #test
                    
                    tempvalue = np.array(selafinlayer.value)
                    tabx,taby, goodnum,badnum = self.getxynuminrenderer(selafinlayer,rendererContext)
                    tempvalue[badnum] = np.nan
                    self.tricontourf1= self.ax.tricontourf(selafinlayer.triangulation,
                                                           tempvalue,selafinlayer.lvl_gachette, 
                                                           cmap=  selafinlayer.cmap_mpl_contour,
                                                           norm=selafinlayer.norm_mpl_contour ,
                                                           alpha = selafinlayer.alpha/100.0,
                                                           extend = 'neither',
                                                           rasterized=True)
                """
                if DEBUG : time1.append("tricontourf : "+str(round(time.clock()-timestart,3)))
                
                
                if selafinlayer.showvelocityparams['show']:
                    tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                    C = np.sqrt(np.array(tabvx)**2 + np.array(tabvy)**2)
                    self.temp = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                               scale=selafinlayer.showvelocityparams['norm'],
                                               scale_units='xy',
                                               cmap=  selafinlayer.cmap_mpl_vel,
                                               norm=selafinlayer.norm_mpl_vel)
                    if DEBUG : time1.append("quiver : "+str(round(time.clock()-timestart,3)))



            #***********************************************************************
            #Case 3 : new figure
            else:

                #update selafinlayer parameters
                selafinlayer.param_memoire = selafinlayer.param_gachette
                selafinlayer.lvl_memoire=selafinlayer.lvl_gachette
                selafinlayer.temps_memoire=selafinlayer.temps_gachette
                selafinlayer.renderersizepx = sizepx
                selafinlayer.alpha = selafinlayer.alpha_gachette
                selafinlayer.cmap_gachette = selafinlayer.cmap
                if DEBUG : time1.append("nouveau")

                #matplotlib figure construction
                self.fig.set_size_inches(width,lenght)
                self.ax.cla()
                #no axis nor border
                self.fig.patch.set_visible(False)
                self.ax.axes.axis('off')
                self.ax.set_ylim([rect[2],rect[3]])
                self.ax.set_xlim([rect[0],rect[1]])
                self.mask = None
                self.tritemp = None
                self.image_mesh = None
                #graph 
                if DEBUG : time1.append("value : "+str(round(time.clock()-timestart,3)))
                
                if True:
                    self.tricontourf1 = self.ax.tricontourf(selafinlayer.triangulation,
                                                        selafinlayer.value,selafinlayer.lvl_gachette, 
                                                        cmap=  selafinlayer.cmap_mpl_contour,
                                                        norm=selafinlayer.norm_mpl_contour ,
                                                        alpha = selafinlayer.alpha/100.0,
                                                        #extent = tuple(rect),
                                                        extend = 'neither',
                                                        rasterized=True)
                else:   #test
                    print 'ok1'
                    tempvalue = np.array(selafinlayer.value)
                    tabx,taby,goodnum,badnum = self.getxynuminrenderer(selafinlayer,rendererContext)
                    print 'ok'
                    tempvalue[badnum] = np.nan
                    self.tricontourf1 = self.ax.tricontourf(selafinlayer.triangulation,
                                                            tempvalue,selafinlayer.lvl_gachette, 
                                                            cmap=  selafinlayer.cmap_mpl_contour,
                                                            norm=selafinlayer.norm_mpl_contour ,
                                                            alpha = selafinlayer.alpha/100.0,
                                                            rasterized=True)
                                                                         
                if selafinlayer.showmesh:
                    self.meshplot = self.ax.triplot(selafinlayer.triangulation, 'k,-',color = '0.5',linewidth = 0.5, alpha = selafinlayer.alpha/100.0)

                if selafinlayer.showvelocityparams['show']:
                    tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                    C = np.sqrt(np.array(tabvx)**2 + np.array(tabvy)**2)
                    self.temp = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                scale=selafinlayer.showvelocityparams['norm'],
                                                scale_units='xy',
                                                cmap=  selafinlayer.cmap_mpl_vel,
                                                norm=selafinlayer.norm_mpl_vel)
                    if DEBUG : time1.append("quiver : "+str(round(time.clock()-timestart,3)))

                
                if selafinlayer.forcerefresh == True:
                    selafinlayer.forcerefresh = False

                self.fig.subplots_adjust(0,0,1,1)
            

            #save qimage
            
            if DEBUG and False:
                #time1.append( str( QtGui.QImageReader.supportedImageFormats() ))
                timejpg = time.clock()
                format1 = 'jpg'
                self.fig.savefig(buf,transparent=True, format = format1, dpi = dpi2)
                #if DEBUG : time1.append("savefig jpg: "+str(round(time.clock()-timejpg,3)))
                buf.seek(0)
                image = QtGui.QImage.fromData(buf.getvalue(),format1)
                if DEBUG : time1.append("qimage jpg: "+str(round(time.clock()-timejpg,3)))
                
                timetif = time.clock()
                format1 = 'jpg'
                self.fig.savefig(buf,transparent=True, format = format1, dpi = dpi2)
                #if DEBUG : time1.append("savefig tif: "+str(round(time.clock()-timetif,3)))
                buf.seek(0)
                image = QtGui.QImage.fromData(buf.getvalue(),format1)
                if DEBUG : time1.append("qimage tif: "+str(round(time.clock()-timetif,3)))
                
                timetif = time.clock()
                format1 = 'svgz'
                self.fig.savefig(buf,transparent=True, format = format1, dpi = dpi2)
                #if DEBUG : time1.append("savefig tif: "+str(round(time.clock()-timetif,3)))
                buf.seek(0)
                image = QtGui.QImage.fromData(buf.getvalue(),format1)
                if DEBUG : time1.append("qimage svg: "+str(round(time.clock()-timetif,3)))
            
            """
            #format1 = 'jpeg'
            #self.fig.savefig(buf,transparent=True, format = format1, dpi = dpi2/ratio)
            self.fig.savefig(buf,transparent=True, dpi = dpi2)
            if DEBUG : time1.append("savefig : "+str(round(time.clock()-timestart,3)))
            buf.seek(0)
            #image = QtGui.QImage.fromData(buf.getvalue(),format1)
            image = QtGui.QImage.fromData(buf.getvalue())
            image = image.scaled(image.width() * ratio , image.height() * ratio )
            """
            image_contour = self.saveImage(ratio,dpi2)
            
            if DEBUG : time1.append("qimage : "+str(round(time.clock()-timestart,3)))
            if DEBUG : selafinlayer.propertiesdialog.textBrowser_2.append("Chargement carte : "+str(time1))
            return (True,image_contour,self.image_mesh)

        except Exception, e :
            selafinlayer.propertiesdialog.textBrowser_2.append('getqimage1 : '+str(e))
            return(False,QtGui.QImage(),QtGui.QImage())

            
            
    def getVelocity(self,selafin,rendererContext):

        tabx=[]
        taby=[]
        tabvx=[]
        tabvy=[]
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        #print str(selafin.showvelocityparams)
        if selafin.showvelocityparams['type'] in [0,1]:
            if selafin.showvelocityparams['type'] == 0:
                nombrecalcul = selafin.showvelocityparams['step'] 
                pasespace = int((rect[1]-rect[0])/nombrecalcul)
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0]/pasespace)*pasespace
                rect[2] = int(rect[2]/pasespace)*pasespace
                rangex = nombrecalcul+3
                rangey = nombrecalcul+3
                pasy = int((rect[3]-rect[2])/nombrecalcul)
            elif selafin.showvelocityparams['type'] == 1 :
                pasespace = selafin.showvelocityparams['step'] 
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0]/pasespace)*pasespace
                rect[2] = int(rect[2]/pasespace)*pasespace
                rangex = int((rect[1]-rect[0])/pasespace)+3
                rangey = int((rect[3]-rect[2])/pasespace)+3
            
            x = np.arange(rect[0],rect[0]+rangex*pasx,pasx) 
            y = np.arange(rect[2],rect[2]+rangey*pasy,pasy)
            mesh = np.meshgrid(x,y)
            tabx = np.ravel(mesh[0].tolist())
            taby = np.ravel(mesh[1].tolist())
            if not selafin.triinterp :
                selafin.initTriinterpolator()
            tabvx =  selafin.triinterp[selafin.parametrevx].__call__(tabx,taby)
            tabvy =  selafin.triinterp[selafin.parametrevy].__call__(tabx,taby)

        elif selafin.showvelocityparams['type'] == 2:
            tabx, taby, goodnum, badnum = self.getxynuminrenderer(selafin,rendererContext)
            tabvx=selafin.values[selafin.parametrevx][goodnum]
            tabvy=selafin.values[selafin.parametrevy][goodnum]
        return tabx,taby,tabvx,tabvy
        
    def saveImage(self,ratio,dpi2):
        buf = cStringIO.StringIO()
        self.fig.savefig(buf,transparent=True, dpi = dpi2)
        buf.seek(0)
        #image = QtGui.QImage.fromData(buf.getvalue(),format1)
        image = QtGui.QImage.fromData(buf.getvalue())
        image = image.scaled(image.width() * ratio , image.height() * ratio )
        return image
        
    def getxynuminrenderer(self,selafin,rendererContext):
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        tabx, taby = selafin.selafinparser.getMesh()
        valtabx = np.where(np.logical_and(tabx>rect[0], tabx< rect[1]))
        valtaby = np.where(np.logical_and(taby>rect[2], taby< rect[3]))
        goodnum = np.intersect1d(valtabx[0],valtaby[0])
        tabx = tabx[goodnum]
        taby = taby[goodnum]
        badnum = np.setxor1d(valtabx[0],valtaby[0])
        return tabx,taby,goodnum,badnum
        
    def getTriTemp(self,selafin,rendererContext):
        tabx, taby, goodnum, badnum = self.getxynuminrenderer(selafin,rendererContext)
        #meshx, meshy = self.selafinparser.getMesh()
        ikle = selafin.selafinparser.getIkle()
        print str(ikle)
        tritemp = matplotlib.tri.Triangulation(tabx,taby,np.array(ikle))
        return tritemp , goodnum
        
    def getMaskMesh(self,selafin,rendererContext):
        ikle = selafin.selafinparser.getIkle()
        print str(len(ikle))
        #maskmeshs = np.zeros(len(ikle))
        tabx, taby, goodnum, badnum = self.getxynuminrenderer(selafin,rendererContext)
        #maskmeshs = np.array([np.any(np.equal(mesh, goodnum))  for i, mesh in enumerate(ikle)])
        maskmeshs = np.array([np.any(np.in1d(mesh, goodnum))  for mesh in ikle])
        print str(len(maskmeshs))
        print str(maskmeshs)
        
        return maskmeshs
        
    def getMaskMesh2(self,selafin,rendererContext):
        mesh = np.array(selafin.selafinparser.getIkle())
        #maskMesh = np.zeros(len(mesh))
        maskMesh = np.array([1.0]*len(mesh))
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        x0 = rect[0]
        y0 = rect[2]
        dx = rect[1]-rect[0]
        dy = rect[3]-rect[2]
        xMesh, yMesh = selafin.selafinparser.getMesh()
        for i in range(len(mesh)):
            #plot only mesh inside a box x0,y0 lower left corner dx/dy length

            """
            x0 = 5300
            y0 = 4160
            dx = 200
            dy = 200
            """

            minX = min(xMesh[mesh[i][0]],xMesh[mesh[i][1]],xMesh[mesh[i][2]])
            maxX = max(xMesh[mesh[i][0]],xMesh[mesh[i][1]],xMesh[mesh[i][2]])
            minY = min(yMesh[mesh[i][0]],yMesh[mesh[i][1]],yMesh[mesh[i][2]])
            maxY = max(yMesh[mesh[i][0]],yMesh[mesh[i][1]],yMesh[mesh[i][2]])
            #if ((x0 < minX < (x0 + dx)) and   (y0 < maxY < (y0 + dy))):
            #if minX > x0  and minX < x0 + dx and  maxY > y0  and maxY < y0 + dy:
            """
            if i%40000 == 0 :
                print 'x ' + str(minX)+' - ' +str(maxX)+' - ' +str(rect[0]) + ' - ' + str(rect[1])
                if minX > rect[0]  and maxX < rect[1]:
                    print 'okx'
                print 'y ' + str(minY)+' - ' +str(maxY)+' - ' +str(rect[2]) + ' - ' + str(rect[3])
                if minY > rect[2]  and maxY < rect[3]:
                    print 'oky'
            """
            if maxX > rect[0]  and minX < rect[1] and  maxY > rect[2]  and minY < rect[3]:
                maskMesh[i] = 0.0
            """
            else:
                maskMesh[i] = 1.0
            """

            #search after node id's this helps if you like to plot the boundary
            """
            minId =  min(mesh[i][0],mesh[i][1],mesh[i][2])
            if (minId < nofBoundaryNodes):
                maskMesh[i] = 0.0
            else:
                maskMesh[i] = 1.0
            """
        #print str(np.where(maskMesh == 0.0))
        Zm = np.ma.masked_where(maskMesh > 0.5, maskMesh)
        #print str(np.where(Zm.mask == True))
        #print str(Zm.mask)
        return Zm.mask
        
    def getMaskMesh3(self,selafin,rendererContext):
        mesh = np.array(selafin.selafinparser.getIkle())
        #mesh = selafin.selafinparser.getIkle()
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        #mask = np.zeros(len(ikle))
        #tabx, taby = selafin.selafinparser.getMesh()
        #valmaskx = np.where(np.logical_and(tabx>rect[0], tabx< rect[1]))
        xMesh, yMesh = selafin.selafinparser.getMesh()
        #tabx, taby, goodnum, badnum = self.getxynuminrenderer(selafin,rendererContext)
        maskMesh = np.array([1.0]*len(mesh))
        
        if True : 
            trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
            trianx = np.transpose(trianx)
            triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
            triany = np.transpose(triany)
            
            valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
            valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))

            goodnum = np.intersect1d(valtabx[0],valtaby[0])

            maskMesh[goodnum] = 0.0
        
        
        else:
            trian = [xMesh[mesh[:][0]], xMesh[mesh[:][1]], xMesh[mesh[:][2]], yMesh[mesh[:][0]], yMesh[mesh[:][1]], yMesh[mesh[:][2]]]
            #trian = np.transpose(trian)
            
            #print str(trian)
            
            valtab = np.where( np.logical_and( np.logical_and(trian[:2]>rect[0], trian[:2]< rect[1]) ,  np.logical_and(trian[2:5]>rect[2], trian[2:5]< rect[3]) ) )
            
            print str(valtab)
            
            valtab2 = np.any(valtab, axis = 0 )
            
            #goodnum = np.intersect1d(valtabx[0],valtaby[0])
            
            print str(valtab2)
            
        return maskMesh
        
    def getMaskMesh4(self,selafin,rendererContext):
        mesh = np.array(selafin.selafinparser.getIkle())
        #mesh = selafin.selafinparser.getIkle()
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        #mask = np.zeros(len(ikle))
        #tabx, taby = selafin.selafinparser.getMesh()
        #valmaskx = np.where(np.logical_and(tabx>rect[0], tabx< rect[1]))
        xMesh, yMesh = selafin.selafinparser.getMesh()
        #tabx, taby, goodnum, badnum = self.getxynuminrenderer(selafin,rendererContext)


        trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
        triany = np.transpose(triany)
        
        valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
        valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))
        #index of triangles in canvas
        goodnum = np.intersect1d(valtabx[0],valtaby[0])
        #goodnum2 = [i, gdnum for i, gdnum in goodnum]
        
        goodikle = mesh[goodnum]
        goodpointindex = np.unique(goodikle)
        
        #print str(goodpointindex)
        
        oldpoint = goodpointindex
        #print 'oldpoint ' + str(oldpoint)
        newpoints = np.arange(0,len(oldpoint),1)
        #print 'newpoints ' + str(newpoints)
        
        mask = np.in1d(goodikle,oldpoint)
        idx = np.searchsorted(oldpoint,goodikle.ravel()[mask])
        goodikle.ravel()[mask] = newpoints[idx]
        #print str(goodikle)
        
        triangle = matplotlib.tri.Triangulation(xMesh[goodpointindex],yMesh[goodpointindex],np.array(goodikle))
        
        return triangle, goodpointindex
        
        
        #goodpointindex = np.unique(goodikle)
        
        
        
    def replaceval(self, arr, df):
        oldval = np.array(df['country_codes'])
        newval = np.array(df['continent_codes'])
        left_idx = np.searchsorted(oldval,arr,'left')
        right_idx = np.searchsorted(oldval,arr,'right')
        mask = left_idx!=right_idx
        arr[mask] = newval[left_idx[mask]]
        return arr
 
        
        
        
        
        
        
        
        
        
        
        
        