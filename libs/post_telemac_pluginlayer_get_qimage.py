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
import qgis.core 
#import PyQT
from PyQt4 import QtGui
#import matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import tri
from matplotlib.backends.backend_agg import FigureCanvasAgg
#import numpy
import numpy as np

#other imports
from time import ctime
import cStringIO
import gc
import time

DEBUG = False
PRECISION = 0.01


class Selafin2QImage():

    def __init__(self,selafinlayer,int=1):
        self.fig =  plt.figure(int)
        #self.canvas = FigureCanvasAgg(self.fig)
        self.selafinlayer = selafinlayer
        self.ax = self.fig.add_subplot(111)
        #Reprojected things
        self.triangulation = None   #the reprojected triangulation
        self.meshxreprojected, self.meshyreprojected = None, None
        #mpl figures
        self.tricontourf1 = None    #the contour plot
        self.meshplot = None    #the meshplot
        self.quiverplot = None  #the quiver plot
        self.tritemp = None #the matplotlib triangulation centred on canvas view
        #other
        self.image_mesh = None
        self.goodpointindex  = None
        self.previousdrawrenderersizepx = None
        self.previousdrawlvl = None
        self.previousdrawtime = None
        self.previousdrawparam = None
        self.previousdrawalpha = None
        self.previousdrawcmcontour = None
        self.previousdrawcmvelocity = None
        
    def changeTriangulationCRS(self):
        try:
            if self.selafinlayer != None and self.selafinlayer.hydrauparser != None:
                meshx, meshy = self.selafinlayer.hydrauparser.getMesh()
                ikle = self.selafinlayer.hydrauparser.getIkle()
                self.meshxreprojected, self.meshyreprojected = self.getTransformedCoords(meshx, meshy)
                self.meshxreprojected = np.array(self.meshxreprojected)
                self.meshyreprojected = np.array(self.meshyreprojected)
                self.triangulation = matplotlib.tri.Triangulation(self.meshxreprojected,self.meshyreprojected,np.array(ikle))
        except Exception, e :
            print str('changecrs : '+str(e))
        
    def getTransformedCoords(self,xcoords,ycoords,direction = True):
        coordinatesAsPoints = [ qgis.core.QgsPoint(xcoords[i], ycoords[i]) for i in range(len(xcoords))]
        if direction:
            transformedCoordinatesAsPoints = [self.selafinlayer.xform.transform(point) for point in coordinatesAsPoints]
        else:
            transformedCoordinatesAsPoints = [self.selafinlayer.xform.transform(point,qgis.core.QgsCoordinateTransform.ReverseTransform) for point in coordinatesAsPoints]
        xcoordsfinal = [point.x() for point in transformedCoordinatesAsPoints]
        ycoordsfinal = [point.y() for point in transformedCoordinatesAsPoints]
        return xcoordsfinal,ycoordsfinal
            
            
        
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

        #Working with CRS - todo
        ct = rendererContext.coordinateTransform()
        if ct:
            recttemp2 = ct.transformBoundingBox(rendererContext.extent())
            rect2 = [float(recttemp2.xMinimum()), float(recttemp2.xMaximum()), float(recttemp2.yMinimum()), float(recttemp2.yMaximum())]

        if DEBUG and False:   #debug thing
            txt = ('rect '+str(rect)+"\n"+ str(mupp) + "\n"+
                    " px "+str(selafinlayer.renderersizepx)+'/'+str(sizepx) + "\n"+
                                                    ' temps '+str(selafinlayer.temps_memoire)+'/'+str(selafinlayer.time_displayed) +"\n"
                                                    +'param '+ str(selafinlayer.param_memoire)+ " " +str(selafinlayer.param_displayed))
            
            selafinlayer.propertiesdialog.textBrowser_2.append(txt)
        
        
        try:
            #***********************************************************************
            #Case 1 : mapcanvas panned
            if (self.previousdrawrenderersizepx==sizepx and self.previousdrawtime == selafinlayer.time_displayed 
                and self.previousdrawparam == selafinlayer.param_displayed 
                and selafinlayer.lvl_contour == self.previousdrawlvl and selafinlayer.alpha_displayed == self.previousdrawalpha 
                and self.previousdrawcmcontour == selafinlayer.cmap_mpl_contour_raw and selafinlayer.forcerefresh == False):
                
                if DEBUG : time1.append("deplacement")

                #change view of matplotlib figure
                if not self.tritemp == None :   #case if a temporary triangulation was used
                    ncollections = len(self.ax.collections)
                    for i in range(ncollections):  
                        self.ax.collections[0].remove()
                    self.fig.canvas.flush_events()
                    gc.collect()

                    self.tricontourf1= self.ax.tricontourf(self.triangulation,
                                                       selafinlayer.value,
                                                       selafinlayer.lvl_contour, 
                                                       cmap=  selafinlayer.cmap_mpl_contour,
                                                       norm=selafinlayer.norm_mpl_contour ,
                                                       alpha = selafinlayer.alpha_displayed/100.0,
                                                       nchunk = 10
                                                       #rasterized=True
                                                       )

                    if selafinlayer.showmesh:
                        self.meshplot = self.ax.triplot(self.triangulation, 'k,-',color = '0.5',linewidth = 0.5, alpha = selafinlayer.alpha_displayed/100.0)

                    #reinit temporary triangulation variables
                    self.tritemp = None
                    self.image_mesh = None
                    self.goodpointindex  = None
                    
                if selafinlayer.showvelocityparams['show']:
                
                    try:
                        self.quiverplot.remove()
                    except Exception, e:
                        pass
                    
                    tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                    C = np.sqrt(tabvx**2 + tabvy**2)
                    
                    tabx = tabx[np.where(C > PRECISION) ]
                    taby = taby[np.where(C > PRECISION) ]
                    tabvx = tabvx[np.where(C > PRECISION) ]
                    tabvy = tabvy[np.where(C > PRECISION) ]
                    C = C[np.where(C > PRECISION)]
                    
                    if selafinlayer.showvelocityparams['norm'] >=0 :
                        self.quiverplot = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                   scale=selafinlayer.showvelocityparams['norm'],
                                                   scale_units='xy',
                                                   cmap=  selafinlayer.cmap_mpl_vel,
                                                   norm=selafinlayer.norm_mpl_vel)
                    else:
                        UN = np.array(tabvx)/C
                        VN = np.array(tabvy)/C
                        self.quiverplot = self.ax.quiver(tabx,taby,UN,VN,C,
                                                   cmap=  selafinlayer.cmap_mpl_vel,
                                                   scale=-1/selafinlayer.showvelocityparams['norm'],
                                                   scale_units='xy'
                                                   )
                                                   
                    if DEBUG : time1.append("quiver : "+str(round(time.clock()-timestart,3)))
                
                self.ax.set_ylim([rect[2],rect[3]])
                self.ax.set_xlim([rect[0],rect[1]])

                
                if DEBUG : time1.append("deplacement : "+str(round(time.clock()-timestart,3)))


            #***********************************************************************
            #Case 2 : figure changed (time,param) with the same mapcanvas dimension
            elif self.previousdrawrenderersizepx == sizepx and selafinlayer.forcerefresh == False :
                #update selafinlayer parameters
                self.previousdrawparam = selafinlayer.param_displayed
                self.previousdrawlvl = selafinlayer.lvl_contour
                self.previousdrawtime = selafinlayer.time_displayed
                self.previousdrawalpha = selafinlayer.alpha_displayed
                self.previousdrawrenderersizepx = sizepx
                self.previousdrawcmcontour = selafinlayer.cmap_mpl_contour_raw
                
                if DEBUG : time1.append("nouveau meme taille")
                if DEBUG : time1.append("avant value : "+str(round(time.clock()-timestart,3)))
                
                #Removing older graph
                ncollections = len(self.ax.collections)
                for i in range(ncollections):  
                    #print str(self.ax.collections[0])
                    self.ax.collections[0].remove()
                self.fig.canvas.flush_events()
                gc.collect()
                
                #first time - if image of mesh is not created
                if self.image_mesh == None and selafinlayer.showmesh :
                    #create image mesh
                    self.image_mesh = self.saveImage(ratio,dpi2)
                    #remove mesh graph
                    self.ax.cla()
                    self.ax.axes.axis('off')
            
                if not self.tritemp:    #create temp triangulation
                    self.tritemp, self.goodpointindex = self.getMaskMesh4(selafinlayer,rendererContext)
                    if DEBUG : time1.append("tritemp : "+str(round(time.clock()-timestart,3)))
                    
                self.tricontourf1= self.ax.tricontourf(self.tritemp,
                                                   selafinlayer.value[self.goodpointindex],
                                                   selafinlayer.lvl_contour, 
                                                   cmap=  selafinlayer.cmap_mpl_contour,
                                                   norm=selafinlayer.norm_mpl_contour ,
                                                   alpha = selafinlayer.alpha_displayed/100.0,
                                                   nchunk = 10
                                                   #extent = tuple(rect),
                                                   #mask = self.mask ,
                                                   #rasterized=True
                                                   )

                if DEBUG : time1.append("tricontourf : "+str(round(time.clock()-timestart,3)))
                
                
                if selafinlayer.showvelocityparams['show']:
                    tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                    C = np.sqrt(tabvx**2 + tabvy**2)
                    
                    tabx = tabx[np.where(C > PRECISION) ]
                    taby = taby[np.where(C > PRECISION) ]
                    tabvx = tabvx[np.where(C > PRECISION) ]
                    tabvy = tabvy[np.where(C > PRECISION) ]
                    C = C[np.where(C > PRECISION)]
                    
                    if selafinlayer.showvelocityparams['norm'] >=0 :
                        self.quiverplot = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                   scale=selafinlayer.showvelocityparams['norm'],
                                                   scale_units='xy',
                                                   cmap=  selafinlayer.cmap_mpl_vel,
                                                   norm=selafinlayer.norm_mpl_vel)
                    else:
                        UN = np.array(tabvx)/C
                        VN = np.array(tabvy)/C
                        self.quiverplot = self.ax.quiver(tabx,taby,UN,VN,C,
                                                   cmap=  selafinlayer.cmap_mpl_vel,
                                                   scale=-1/selafinlayer.showvelocityparams['norm'],
                                                   scale_units='xy'
                                                   )
                                                   
                    if DEBUG : time1.append("quiver : "+str(round(time.clock()-timestart,3)))
                
                self.ax.set_ylim([rect[2],rect[3]])
                self.ax.set_xlim([rect[0],rect[1]])
                

            #***********************************************************************
            #Case 3 : new figure
            else:
                #update selafinlayer parameters
                self.previousdrawparam = selafinlayer.param_displayed
                self.previousdrawlvl = selafinlayer.lvl_contour
                self.previousdrawtime = selafinlayer.time_displayed
                self.previousdrawalpha = selafinlayer.alpha_displayed
                #selafinlayer.rendererrect = rect
                self.previousdrawrenderersizepx = sizepx
                self.previousdrawcmcontour = selafinlayer.cmap_mpl_contour_raw
                
                if DEBUG : time1.append("nouveau")

                #matplotlib figure construction
                self.fig.set_size_inches(width,lenght)
                self.ax.cla()
                #no axis nor border
                self.fig.patch.set_visible(False)
                self.ax.axes.axis('off')
                self.ax.set_ylim([rect[2],rect[3]])
                self.ax.set_xlim([rect[0],rect[1]])
                #self.mask = None
                self.tritemp = None
                self.image_mesh = None
                self.goodpointindex = None
                #graph 
                if DEBUG : time1.append("value : "+str(round(time.clock()-timestart,3)))
                

                self.tricontourf1 = self.ax.tricontourf(self.triangulation,
                                                    selafinlayer.value,selafinlayer.lvl_contour, 
                                                    cmap=  selafinlayer.cmap_mpl_contour,
                                                    norm=selafinlayer.norm_mpl_contour ,
                                                    alpha = selafinlayer.alpha_displayed/100.0,
                                                    #extent = tuple(rect),
                                                    extend = 'neither'
                                                    #rasterized=True
                                                    )


                                                                         
                if selafinlayer.showmesh:
                    self.meshplot = self.ax.triplot(self.triangulation, 'k,-',color = '0.5',linewidth = 0.5, alpha = selafinlayer.alpha_displayed/100.0)

                if selafinlayer.showvelocityparams['show']:
                    tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                    C = np.sqrt(tabvx**2 + tabvy**2)
                    
                    tabx = tabx[np.where(C > PRECISION) ]
                    taby = taby[np.where(C > PRECISION) ]
                    tabvx = tabvx[np.where(C > PRECISION) ]
                    tabvy = tabvy[np.where(C > PRECISION) ]
                    C = C[np.where(C > PRECISION)]
                    
                    if selafinlayer.showvelocityparams['norm'] >=0 :
                        self.quiverplot = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                   scale=selafinlayer.showvelocityparams['norm'],
                                                   scale_units='xy',
                                                   cmap=  selafinlayer.cmap_mpl_vel,
                                                   norm=selafinlayer.norm_mpl_vel)
                    else:
                        UN = np.array(tabvx)/C
                        VN = np.array(tabvy)/C
                        self.quiverplot = self.ax.quiver(tabx,taby,UN,VN,C,
                                                   cmap=  selafinlayer.cmap_mpl_vel,
                                                   scale=-1/selafinlayer.showvelocityparams['norm'],
                                                   scale_units='xy'
                                                   )

                    if DEBUG : time1.append("quiver : "+str(round(time.clock()-timestart,3)))

                
                if selafinlayer.forcerefresh == True:
                    selafinlayer.forcerefresh = False

                self.fig.subplots_adjust(0,0,1,1)
            

            #save qimage
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
            """
            tabvx =  selafin.triinterp[selafin.parametrevx].__call__(tabx,taby)
            tabvy =  selafin.triinterp[selafin.parametrevy].__call__(tabx,taby)
            """
            tempx1, tempy1 = self.getTransformedCoords(tabx,taby,False)
            tabvx =  selafin.triinterp[selafin.hydrauparser.parametrevx].__call__(tempx1,tempy1)
            tabvy =  selafin.triinterp[selafin.hydrauparser.parametrevy].__call__(tempx1,tempy1)

        elif selafin.showvelocityparams['type'] == 2:
            if not self.goodpointindex == None :
                #tabx, taby = selafin.hydrauparser.getMesh()
                tabx = self.meshxreprojected
                taby = self.meshyreprojected
                goodnum = self.goodpointindex
                tabx = tabx[goodnum]
                taby = taby[goodnum]
            else:
                tabx, taby, goodnum = self.getxynuminrenderer(selafin,rendererContext)
            tabvx=selafin.values[selafin.hydrauparser.parametrevx][goodnum]
            tabvy=selafin.values[selafin.hydrauparser.parametrevy][goodnum]
        return np.array(tabx),np.array(taby),np.array(tabvx),np.array(tabvy)
        
    def saveImage(self,ratio,dpi2):
        """
        Return a qimage of the matplotlib figure
        """
        try:
            if False:
                buf = cStringIO.StringIO()
                #self.fig.savefig(buf,transparent=True, dpi = dpi2)
                self.fig.savefig(buf, dpi = dpi2)
                buf.seek(0)
                #image = QtGui.QImage.fromData(buf.getvalue(),format1)
                image = QtGui.QImage.fromData(buf.getvalue())
                if ratio > 1.0 :
                    image = image.scaled(image.width() * ratio , image.height() * ratio )
            else:
                buf = cStringIO.StringIO()
                #canvas = FigureCanvasAgg(self.fig)
                #self.canvas.draw()
                #self.canvas.print_figure(buf, dpi = dpi2)
                #self.fig.canvas.draw()
                self.fig.canvas.print_figure(buf, dpi = dpi2)
                
                buf.seek(0)
                #image = QtGui.QImage.fromData(buf.getvalue(),format1)
                image = QtGui.QImage.fromData(buf.getvalue())
                if ratio > 1.0 :
                    image = image.scaled(image.width() * ratio , image.height() * ratio )
            return image
        except Exception, e :
            self.selafinlayer.propertiesdialog.textBrowser_2.append('getqimagesave : '+str(e))
            return None
        
    def getxynuminrenderer(self,selafin,rendererContext):
        """
        Return index of selafin points in the visible canvas with corresponding x and y value
        """
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        """
        tabx, taby = selafin.hydrauparser.getMesh()
        tabx, taby = self.getTransformedCoords(tabx,taby)
        """
        tabx = self.meshxreprojected
        taby = self.meshyreprojected
        
        valtabx = np.where(np.logical_and(tabx>rect[0], tabx< rect[1]))
        valtaby = np.where(np.logical_and(taby>rect[2], taby< rect[3]))
        goodnum = np.intersect1d(valtabx[0],valtaby[0])
        tabx = tabx[goodnum]
        taby = taby[goodnum]
        #badnum = np.setxor1d(valtabx[0],valtaby[0])
        return tabx,taby,goodnum
        
        
    def getMaskMesh3(self,selafin,rendererContext):
        """
        Not used - case if we want a mask mesh for tricontour
        """
        mesh = np.array(selafin.hydrauparser.getIkle())
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        xMesh, yMesh = selafin.hydrauparser.getMesh()
        maskMesh = np.array([1.0]*len(mesh))
        
        trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
        triany = np.transpose(triany)
        
        valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
        valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))

        goodnum = np.intersect1d(valtabx[0],valtaby[0])

        maskMesh[goodnum] = 0.0
        
        return maskMesh
        
    def getMaskMesh4(self,selafin,rendererContext):
        """
        return a new triangulation based on triangles visbles in the canvas. 
        return index of selafin points correspondind to the new triangulation
        """
        mesh = np.array(selafin.hydrauparser.getIkle())
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        """
        xMesh, yMesh = selafin.hydrauparser.getMesh()
        xMesh, yMesh = self.getTransformedCoords(xMesh, yMesh)
        """
        xMesh = self.meshxreprojected
        yMesh = self.meshyreprojected

        trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
        triany = np.transpose(triany)
        
        valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
        valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))
        #index of triangles in canvas
        goodnum = np.intersect1d(valtabx[0],valtaby[0])
        
        goodikle = mesh[goodnum]
        goodpointindex = np.unique(goodikle)

        oldpoint = goodpointindex
        newpoints = np.arange(0,len(oldpoint),1)
        
        mask = np.in1d(goodikle,oldpoint)
        idx = np.searchsorted(oldpoint,goodikle.ravel()[mask])
        goodikle.ravel()[mask] = newpoints[idx]
        
        triangle = matplotlib.tri.Triangulation(xMesh[goodpointindex],yMesh[goodpointindex],np.array(goodikle))
        
        return triangle, goodpointindex

