# -*- coding: utf-8 -*-


from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import numpy
import numpy as np
#import matplotlib
from matplotlib.path import Path
import matplotlib.pyplot as plt
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui
#imports divers
import time
from time import ctime
import math
from shapely.geometry import *
import os.path    
import networkx as nx
#import selafinslicemesh
from ..libs_telemac.samplers.meshes import *
    
debug = False



#*********************************************************************************************
#*************** Classe de traitement **********************************************************
#********************************************************************************************


class computeFlow(QtCore.QObject):

    def __init__(self,                
                selafin,line):
        
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.polyline = line
        self.fig = plt.figure(0)
        
        
    def computeFlowMain(self):
        """
        Main method
        
        """
        list1 = []
        list2 = []
        list3 = []
        METHOD = self.selafinlayer.propertiesdialog.comboBox_flowmethod.currentIndex()
        try:
            for lineelement in self.polyline:
                temp3 = self.getLines(lineelement,METHOD)
                result=[]
                parameterh = self.selafinlayer.parametreh
                parameteruv = self.selafinlayer.parametrevx
                parametervv = self.selafinlayer.parametrevy 
                #self.slf = self.selafinlayer.slf
                
                if METHOD == 0 :
                    if not self.selafinlayer.networkxgraph:
                        G=nx.Graph()
                        G.add_edges_from([(edge[0],edge[1]) for edge in self.selafinlayer.triangulation.edges])
                        self.selafinlayer.networkxgraph = G
                    else:
                        G = self.selafinlayer.networkxgraph
                
                if isinstance(temp3,LineString):
                    temp3 = [temp3]
                
                for line in temp3:
                    linetemp = np.array([[point[0],point[1]] for point in line.coords ])
                    resulttemp=[]
                    
                    if METHOD == 0:         #Method0 : shortest path and vector computation
                        flow = None
                        for points in range(len(linetemp)-1):
                            try:
                                triangle = self.selafinlayer.trifind.__call__(linetemp[points][0],linetemp[points][1])
                                if triangle != -1:
                                    enumpointdebut = self.getNearestPointEdge(linetemp[points][0],linetemp[points][1],triangle)
                                triangle = self.selafinlayer.trifind.__call__(linetemp[points + 1][0],linetemp[points + 1][1])
                                if triangle != -1:
                                    enumpointfin = self.getNearestPointEdge(linetemp[points + 1][0],linetemp[points + 1][1],triangle)

                                shortest = nx.shortest_path(G, enumpointdebut, enumpointfin)
                                
                                for i,elem in enumerate(shortest):
                                    try:
                                        if i==0:    #init
                                            try:
                                                h2 = np.array(self.selafinlayer.selafinparser.getTimeSerie([elem + 1],[parameterh])[0][0])
                                            except Exception , e :
                                                self.status.emit('method 011 : ' + str(e))
                                            uv2 = np.array(self.selafinlayer.selafinparser.getTimeSerie([elem + 1],[parameteruv])[0][0])
                                            uv2 = np.array([[value,0.0] for value in uv2])
                                            vv2 = np.array(self.selafinlayer.selafinparser.getTimeSerie([elem + 1],[parametervv])[0][0])
                                            vv2 = np.array([[0.0,value] for value in vv2])
                                            v2vect = uv2 + vv2
                                            #xy2 = [self.slf.MESHX[elem],self.slf.MESHY[elem]]
                                            xy2 = list( self.selafinlayer.selafinparser.getXYFromNumPoint([elem])[0] )
                                        else:
                                            h1 = h2
                                            v1vect = v2vect
                                            xy1 = xy2
                                            h2 = np.array(self.selafinlayer.selafinparser.getTimeSerie([elem + 1],[parameterh])[0][0])
                                            uv2 = np.array(self.selafinlayer.selafinparser.getTimeSerie([elem + 1],[parameteruv])[0][0])
                                            uv2 = np.array([[value,0.0] for value in uv2])
                                            vv2 = np.array(self.selafinlayer.selafinparser.getTimeSerie([elem + 1],[parametervv])[0][0])
                                            vv2 = np.array([[0.0,value] for value in vv2])
                                            v2vect = uv2 + vv2
                                            #xy2 = [self.slf.MESHX[elem],self.slf.MESHY[elem]]
                                            xy2 = list( self.selafinlayer.selafinparser.getXYFromNumPoint([elem])[0] )
                                            if flow != None:
                                                flow = flow + self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                            else:
                                                flow = self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                    except Exception , e :
                                        self.status.emit('method 01 : ' + str(e))
                                    x,y = self.selafinlayer.selafinparser.getXYFromNumPoint([elem])[0]
                                    self.emitpoint.emit(x,y)
                            except Exception , e :
                                self.status.emit('method 0 : ' + str(e))
                        result.append([line,flow])
                    
                    

                    if METHOD == 1 :
                        flow=None
                        temp_edges,temp_point,temp_bary = self.getCalcPointsSlice(line)
                        
                        for i in range(len(temp_point)):
                            if i ==0:
                                h2  = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameterh)
                                uv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameteruv)
                                uv2 = np.array([[value,0.0] for value in uv2])
                                vv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parametervv)
                                vv2 = np.array([[0.0,value] for value in vv2])
                                v2vect = uv2 + vv2
                                xy2 = temp_point[i]
                                self.emitpoint.emit(temp_point[i][0],temp_point[i][1])
                                """
                                self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][0]],self.selafinlayer.slf.MESHY[temp_edges[i][0]])
                                self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][1]],self.selafinlayer.slf.MESHY[temp_edges[i][1]])
                                """
                                x,y = self.selafinlayer.selafinparser.getXYFromNumPoint([temp_edges[i][0]])[0] 
                                self.emitpoint.emit( x,y )
                                x,y = self.selafinlayer.selafinparser.getXYFromNumPoint([temp_edges[i][1]])[0]
                                self.emitpoint.emit( x,y )
                                
                            else:
                                h1 = h2
                                v1vect = v2vect
                                xy1 = xy2
                                h2  = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameterh)
                                uv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parameteruv)
                                uv2 = np.array([[value,0.0] for value in uv2])
                                vv2 = self.valuebetweenEdges(temp_point[i],temp_edges[i],parametervv)
                                vv2 = np.array([[0.0,value] for value in vv2])
                                v2vect = uv2 + vv2
                                xy2 = temp_point[i]
                                #vectorface = np.array([xy2[0]-xy1[0],xy2[1]-xy1[1]])
                                lenght = np.linalg.norm(np.array([xy2[0]-xy1[0],xy2[1]-xy1[1]]))
                                if lenght > 0 : 
                                    if flow != None:
                                        flow = flow + self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                    else:
                                        flow = self.computeFlowBetweenPoints(xy1,h1,v1vect,xy2,h2,v2vect)
                                    self.emitpoint.emit(temp_point[i][0],temp_point[i][1])
                                    """
                                    self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][0]],self.selafinlayer.slf.MESHY[temp_edges[i][0]])
                                    self.emitpoint.emit(self.selafinlayer.slf.MESHX[temp_edges[i][1]],self.selafinlayer.slf.MESHY[temp_edges[i][1]])
                                    """
                                    x,y = self.selafinlayer.selafinparser.getXYFromNumPoint([temp_edges[i][0]])[0] 
                                    self.emitpoint.emit( x,y )
                                    x,y = self.selafinlayer.selafinparser.getXYFromNumPoint([temp_edges[i][1]])[0]
                                    self.emitpoint.emit( x,y )
                                    
                        result.append([line,flow])
                        
                        

                flow = None
                for i in range(len(result)):
                            if i == 0:
                                flow = result[i][1]
                            else:
                                flow = flow + result[i][1]

                #list1.append( self.selafinlayer.slf.tags["times"].tolist() )
                list1.append( self.selafinlayer.selafinparser.getTimes().tolist() )
                list2.append( flow.tolist() )
                list3.append( result )
                
        except Exception, e :
            self.error.emit('flow calculation error : ' + str(e))
                
                
        self.finished.emit(list1,list2,list3)
     
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
    
    
         
    def getLines(self,polyline1,METHOD):
        """
        Line input traitment in order to be only in the area of the modelisation
        Method0 : line slighlty inside the area of modelisation
        Method1 : line slighlty outside
        """
        templine1 = LineString([(i[0],i[1]) for i in polyline1[:-1]])
        temp2_in = []
        temp2_out = []
        meshx,meshy = self.selafinlayer.selafinparser.getMesh()
        ikle = self.selafinlayer.selafinparser.getIkle()
        triplotcontourf = self.fig.gca().tricontourf(meshx,meshy,ikle,self.selafinlayer.value,[-1.0E20,1.0E20])

        if METHOD==0 : buffervalue = 0.05
        elif METHOD == 1 : buffervalue = -0.05
        
        for collection in triplotcontourf.collections:
            for path in collection.get_paths():
                for polygon in path.to_polygons(): 
                    tuplepoly = [(i[0],i[1]) for i in polygon]
                    polygons = Polygon(tuplepoly)
                    if templine1.intersects(polygons):
                        if  ( np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 >0 ):     #outer polygon
                            inter = templine1.intersection(polygons.buffer(-buffervalue))
                            if isinstance(inter,LineString):
                                temp2_out.append(inter)
                            else:
                                for line3 in   inter:      
                                    temp2_out.append(line3)
                        else:                                                                        #inner polygon
                            inter = templine1.intersection(polygons.buffer(buffervalue))
                            if isinstance(inter,LineString):
                                temp2_in.append(inter)
                            else:
                                for line3 in   inter:      
                                    temp2_in.append(line3)
        
        temp2out_line = MultiLineString(temp2_out)
        temp2in_line = MultiLineString(temp2_in)

        linefinal = []        
        for lineout in temp2out_line:
            templine = lineout
            for linein in temp2in_line:
                if lineout.length > linein.length and lineout.intersects(linein.buffer(0.01)):
                    templine = templine.difference(linein.buffer(0.02))
            if isinstance(templine,LineString):
                linefinal.append(templine)
            else:
                for line3 in   templine:      
                    linefinal.append(line3)

        #to keep line direction
        multitemp = MultiLineString(linefinal)
        multidef =  templine1.intersection(multitemp.buffer(0.01))

        return multidef
        
    def getCalcPointsSlice(self,line):
        linetemp = np.array([[point[0],point[1]] for point in line.coords ])
        #print str(line)
        temp_point_final=[]
        temp_edges_final=[]
        temp_bary_final = []
        for i in range(len(linetemp)-1) :
            resulttemp=[]
            lintemp1=np.array([[linetemp[i][0],linetemp[i][1]],[linetemp[i+1][0],linetemp[i+1][1]]])
            lintemp1shapely=LineString([(linetemp[i][0],linetemp[i][1]),(linetemp[i+1][0],linetemp[i+1][1])])
            meshx,meshy = self.selafinlayer.selafinparser.getMesh()
            ikle = self.selafinlayer.selafinparser.getIkle()
            
            quoi = sliceMesh(lintemp1,np.asarray(ikle),np.asarray(meshx),np.asarray(meshy))
            """
            quoi[0][0] is list of points of intersection
            quoi[0][1] is list of egdes intersected by line
            quoi[0][2] is kind of (not exactly) barycentric thing
            """

            temp_point=[]
            temp_edges=[]
            temp_bary = []

            #linebuf = line.buffer(1.0)
            
            for i, edgestemp in enumerate(quoi[0][1]):  #slicemesh - quoi[0][1] is list of egdes intersected by line
                #line4 : line of edge
                x1,y1 = self.selafinlayer.selafinparser.getXYFromNumPoint([edgestemp[0]])[0]
                x2,y2 = self.selafinlayer.selafinparser.getXYFromNumPoint([edgestemp[1]])[0]
                #line4 = LineString([(self.selafinlayer.slf.MESHX[edgestemp[0]],self.selafinlayer.slf.MESHY[edgestemp[0]]),(self.selafinlayer.slf.MESHX[edgestemp[1]],self.selafinlayer.slf.MESHY[edgestemp[1]])])
                line4 = LineString([(x1,y1),(x2,y2)])
                if line4.crosses(lintemp1shapely):
                    temp_edges.append(edgestemp)
                    temp_point.append([quoi[0][0][i][0],quoi[0][0][i][1]])
                    temp_bary.append(quoi[0][2][i])
            
            #check direction
            dir1 = lintemp1shapely.coords[1][0]-lintemp1shapely.coords[0][0]
            dir2 = temp_point[1][0]-temp_point[0][0]
            
            if dir1>0 and dir2 >0:
                pass
                #self.status.emit('line direction ok' + str(dir1) + ' ' +str(dir2))
            elif dir1<0 and dir2 <0:
                pass
                #self.status.emit('line direction ok'+ str(dir1) + ' ' +str(dir2))
            else:
                #self.status.emit('line direction pas ok '+ str(dir1) + ' ' +str(dir2))
                temp_edges = temp_edges[::-1]
                temp_point = temp_point[::-1]
                temp_bary = temp_bary[::-1]
                
            temp_point_final=temp_point_final + temp_point
            temp_edges_final = temp_edges_final + temp_edges
            temp_bary_final = temp_bary_final + temp_bary

        return temp_edges_final,temp_point_final,temp_bary_final
        
        

    

    def computeFlowBetweenPoints(self,xy1,h1,v1vect,xy2,h2,v2vect):
        vectorface = np.array([xy2[0]-xy1[0],xy2[1]-xy1[1]])
        lenght = np.linalg.norm(vectorface)
        if lenght == 0.0:
            return None
        vectorfacenorm = vectorface/np.linalg.norm(vectorface)
        perp = np.array([0,0,-1.0])
        vectorfacenormcrosstemp = np.cross(vectorfacenorm,perp)
        #vectorfacenormcross = np.array([vectorfacenormcrosstemp[0],vectorfacenormcrosstemp[1]]*len(self.selafinlayer.slf.getSERIES([temp_edges[i][1]],[parametervv],False)[0][0]))
        vectorfacenormcross = np.array([vectorfacenormcrosstemp[0],vectorfacenormcrosstemp[1]])


        v1 = np.array([np.dot(vectorfacenormcross,temp) for temp in v1vect ])
        v2 = np.array([np.dot(vectorfacenormcross,temp) for temp in v2vect ])

        """
        v1 et v2 normal à la face
        loi lineaire :
        h = ax+b 
        h1 = b (x=0)
        h2 = axlenght + b 
        b= h1
        a = (h2-h1)/lenght
        
        q = int ( (ah * x + bh) * (av * x + bv )   dx ,0,lenght)
        q = int ( (ah x av)  x^2 + (  ah x bv  + av x bh    ) x + bh x bv   dx ,0,lenght)
        q = ( 1/3 x (ah x av)  x^3 + 1/2 (  ah x bv  + av x bh    ) x^2 + (bh x bv ) * x   ,0,lenght)
        
        q = 1/3 x (ah x av)  lenght^3 + 1/2 (  ah x bv  + av x bh    ) lenght^2 + (bh x bv ) x lenght
        """
        
        deltah = h2-h1
        ah = deltah/lenght
        bh = h1
        deltav = v2 - v1
        av = deltav/lenght
        bv = v1

        #self.status.emit( 'ah : '+str(ah.shape)+'  bh : '+str(bh.shape)+' av :  '+str(av.shape)+' bv : '+str(bv.shape))
        flow = 1.0/3.0*(ah*av)*math.pow(lenght,3) + 1.0/2.0*(ah*bv+av*bh)*math.pow(lenght,2) + (bh*bv)*lenght
        if np.isnan(flow).any():
            self.status.emit(' vecor ' + str(vectorface) + 'lenght ' + str(np.linalg.norm(vectorface)) +  ' norm ' + str(vectorfacenormcross))
            #self.status.emit( 'ah : '+str(ah)+'  bh : '+str(bh)+' av :  '+str(av)+' bv : '+str(bv)+' flow : '+str(flow))
            #self.status.emit( 'flow ' + str(flow) + ' - norm ' +str(vectorfacenormcross) + ' - edges '+str(edges1) + 'x ' +str(self.selafinlayer.slf.MESHX[edges1[0]]) + ' '+str(edges2) + ' - h1 '+str(h1) + ' - h2 ' + str(h2) + ' - v1temp : '+str(v1temp)+  ' - v1 ' + str(v1) + ' v2temp ' + str(v2temp) +  ' - v2 ' + str(v2))
            #self.status.emit( 'flow ' + str(flow[0]) + ' - norm ' +str(vectorfacenormcross) + ' - edges '+str(edges1) + 'x ' +str(self.selafinlayer.slf.MESHX[edges1[0]]) + ' '+str(edges2) + ' - h1 '+str(h1[0]) + ' - h2 ' + str(h2[0]) + ' - v1temp : '+str(v1temp[0])+  ' - v1 ' + str(v1[0]) + ' v2temp ' + str(v2temp[0]) +  ' - v2 ' + str(v2[0]))
        return flow
    

        
    def valuebetweenEdges(self,xy,edges,param):
        xytemp = np.array(xy)
        h11 = np.array(self.selafinlayer.selafinparser.getTimeSerie([edges[0] + 1],[param])[0][0])   #getseries begins at  1 
        h12 = np.array(self.selafinlayer.selafinparser.getTimeSerie([edges[1] + 1 ],[param])[0][0])
        """
        e1 = np.array([self.selafinlayer.slf.MESHX[edges[0]],self.selafinlayer.slf.MESHY[edges[0]]])
        e2 = np.array([self.selafinlayer.slf.MESHX[edges[1]],self.selafinlayer.slf.MESHY[edges[1]]])
        """
        e1 = np.array(self.selafinlayer.selafinparser.getXYFromNumPoint([edges[0]]))
        e2 = np.array(self.selafinlayer.selafinparser.getXYFromNumPoint([edges[1]]))
        
        rap=np.linalg.norm(xytemp-e1)/np.linalg.norm(e2-e1)
        return (1.0-rap)*h11 + (rap)*h12
        
        
    def getNearest(self,x,y,triangle):
        numfinal=None
        distfinal = None
        meshx, meshy = self.selafinlayer.selafinparser.getMesh()
        ikle = self.selafinlayer.selafinparser.getIkle()
        for num in np.array(ikle)[triangle]:
            dist = math.pow(math.pow(float(meshx[num])-float(x),2)+math.pow(float(meshy[num])-float(y),2),0.5)
            if distfinal:
                if dist<distfinal:
                    distfinal = dist
                    numfinal=num
            else:
                distfinal = dist
                numfinal=num
        return numfinal
        
    def getNearestPointEdge(self,x,y,triangle):
        numfinal1=None
        trianglepoints=[]
        point = np.array([x,y])
        distedge = None
        meshx, meshy = self.selafinlayer.selafinparser.getMesh()
        ikle = self.selafinlayer.selafinparser.getIkle()
        for num in np.array(ikle)[triangle]:
            trianglepoints.append(np.array([np.array([meshx[num],meshy[num]]),num]))
        num1 = np.array(ikle)[triangle][0]
        trianglepoints.append(np.array([np.array([meshx[num1],meshy[num1]]),num1]))
            
        for i in range(len(trianglepoints)-1):
            #d = np.linalg.norm(np.cross(l2-l1, l1-p))/np.linalg.norm(l2-l1)
            dist = np.linalg.norm(np.cross(trianglepoints[i+1][0]-trianglepoints[i][0], trianglepoints[i][0]-point))/np.linalg.norm(trianglepoints[i+1][0]-trianglepoints[i][0])
            if distedge:
                if dist<distedge:
                    distedge = dist
                    numfinal1=[trianglepoints[i][1],trianglepoints[i+1][1]]
            else:
                distedge = dist
                numfinal1=[trianglepoints[i][1],trianglepoints[i+1][1]]
        numfinal2=None
        distfinal = None
        
        for num in numfinal1:
            distpoint = math.pow(math.pow(float(meshx[num])-float(x),2)+math.pow(float(meshy[num])-float(y),2),0.5)
            #d = norm(np.cross(l2-l1, l1-p))/norm(l2-l1)
            if distfinal:
                if distpoint<distfinal:
                    distfinal = distpoint
                    numfinal2=num
            else:
                distfinal = distpoint
                numfinal2=num
        return numfinal2
        
        
        

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitComputeFlow(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None
        self.processtype = 0

    def start(self,                 
                 selafin,
                 line):
        #Launch worker
        self.worker = computeFlow(selafin,line)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.computeFlowMain)
        self.worker.status.connect(self.writeOutput)
        self.worker.emitpoint.connect(self.emitPoint)
        self.worker.error.connect(self.raiseError)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        

    
    def raiseError(self,str):
        if self.processtype ==0:
            self.error.emit(str)
        elif self.processtype in [1,2,3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print str
            sys.exit(0)
            
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self,list1,list2,list3):
        self.finished1.emit(list1,list2,list3)

    def emitPoint(self,x,y):
        self.emitpoint.emit(x,y)
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(float,float)
    
    
class FlowMapTool(QgsMapTool):

    def __init__(self, canvas,button):
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QCursor(Qt.CrossCursor)
        self.button = button

    def canvasMoveEvent(self,event):
        self.emit( SIGNAL("moved"), {'x': event.pos().x(), 'y': event.pos().y()} )


    def canvasReleaseEvent(self,event):
        if event.button() == Qt.RightButton:
            self.emit( SIGNAL("rightClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )
        else:
            self.emit( SIGNAL("leftClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )

    def canvasDoubleClickEvent(self,event):
        self.emit( SIGNAL("doubleClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )

    def activate(self):
        QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)
        #print  'activate'
        #self.button.setEnabled(False)
        #self.button.setCheckable(True)
        #self.button.setChecked(True)



    def deactivate(self):
        self.emit( SIGNAL("deactivate") )
        #self.button.setCheckable(False)
        #self.button.setEnabled(True)
        #print  'deactivate'
        QgsMapTool.deactivate(self)


    def setCursor(self,cursor):
        self.cursor = QCursor(cursor)
    