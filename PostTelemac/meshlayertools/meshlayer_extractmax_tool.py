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


#from PyQt4 import uic, QtCore, QtGui
from qgis.PyQt import uic, QtCore, QtGui
from .meshlayer_abstract_tool import *
import qgis, sys

import numpy as np
import time
import math
from ..meshlayerparsers.libs_telemac.other.Class_Serafin import Serafin

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ExtractMaxTool.ui'))



class ExtractMaxTool(AbstractMeshLayerTool,FORM_CLASS):

    NAME = 'EXTRACTMACTOOL'
    SOFTWARE = ['TELEMAC']

    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        self.pushButton_max_res.clicked.connect(self.calculMaxRes)
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Wizard_48x48.png' )
        
        


        

        
    def onActivation(self):
        maxiter = self.meshlayer.hydrauparser.itertimecount
        self.spinBox_max_start.setMaximum(maxiter)
        self.spinBox_max_end.setMaximum(maxiter)
        self.spinBox_max_end.setValue(maxiter)

    def onDesactivation(self):
        pass
        
        
    def calculMaxRes(self):

        self.initclass=initRunGetMax()
        #self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
        self.initclass.status.connect(self.propertiesdialog.logMessage)
        
        
        self.initclass.finished1.connect(self.chargerSelafin)
        self.initclass.start(self.meshlayer,
                             self,
                             self.checkBox_11.isChecked(),
                             self.checkBox_11.isChecked(),
                             self.doubleSpinBox_4.value() if self.checkBox_9.isChecked() else -1,
                             self.doubleSpinBox_5.value() if self.checkBox_10.isChecked() else -1)

        
        
        

    def chargerSelafin(self, path):
        if path and self.checkBox_8.isChecked():
            if sys.version_info.major == 2:
                slf = qgis.core.QgsPluginLayerRegistry.instance().pluginLayerType('selafin_viewer').createLayer()
                #slf.setRealCrs(iface.mapCanvas().mapSettings().destinationCrs())
                slf.setRealCrs(self.meshlayer.crs())
                slf.load_selafin(path,'TELEMAC')
                qgis.core.QgsMapLayerRegistry.instance().addMapLayer(slf)
            elif sys.version_info.major == 3:
                # slf = qgis.core.QgsPluginLayerRegistry.pluginLayerType('selafin_viewer').createLayer()
                if qgis.utils.iface is not None:
                    slf = qgis.core.QgsApplication.instance().pluginLayerRegistry().pluginLayerType('selafin_viewer').createLayer()
                    slf.setRealCrs(self.meshlayer.crs())
                    slf.load_selafin(path,'TELEMAC')
                    qgis.core.QgsProject.instance().addMapLayer(slf)
            


class runGetMax(QtCore.QObject):

    def __init__(self,selafinlayer, tool, intensite = False, direction = False, submersion = -1, duree = -1):
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafinlayer
        self.tool = tool
        self.name_res = self.selafinlayer.hydraufilepath
        # self.name_res_out = self.selafinlayer.hydraufilepath.split('.')[0] + '_Max.res'
        self.name_res_out = self.selafinlayer.hydraufilepath.rsplit('.', maxsplit=1)[0] + '_Max.res'
        self.intensite = intensite
        self.direction = direction
        self.submersion = submersion
        self.duree = duree


    def run(self):
        """
        Fonction permettant de recuperer la valeur max d'un resultat (avec en plus
        l'ecriture de l'intensite et de la direction)
        Parametre d'entree:
        - name_res (str) : nom du fichier resultat telemac
        - name_res_out (str) : nom du fichier a creer (au format Serafin)
        - intensite (bool) : si vrai alors on recalcule l'intensite max
        - direction (bool) : si vrai alors on recalcule la direction des intensites max
        Parametre de sortie:
        - aucun
        fonctions appelees:
        - aucunes

      """

        ## Creation de la variable au format Serafin
        #try:
        if True:
            resin = Serafin(name = self.name_res, mode = 'rb')
            resout = Serafin(name = self.name_res_out, mode = 'wb')


            ## Lecture de l'entete du fichier d'entree
            resin.read_header()

            ## Recuperation de tous les temps
            resin.get_temps()
            
            ## On copie toutes les variables de l'entete du fichier d'entree dans
            ## les variables du fichier de sortie
            resout.copy_info(resin)

            ## On ajoute les deux nouvelles variables, pour cela il faut modifier la variable
            ## nbvar et nomvar (le nom de la variable ne doit pas depasser 72 caracteres
            # print('params',self.selafinlayer.hydrauparser.parametres)
            
            for param in self.selafinlayer.hydrauparser.parametres:
                #if param[2]:        #for virtual parameter
                if param[4]:        #for virtual parameter
                    resout.nbvar += 1
                    resout.nomvar.append(str(param[1]))
            if self.intensite:
                resout.nbvar += 1
                resout.nomvar.append('intensite')
            if self.direction:
                resout.nbvar += 1
                resout.nomvar.append('direction')
            if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None :
                resout.nbvar += 1
                resout.nomvar.append('submersion')
            if self.duree > -1  and self.selafinlayer.hydrauparser.parametreh != None :
                resout.nbvar += 1
                resout.nomvar.append('duree')
                
            print('resout.nomvar',resout.nomvar)
            
            ## Ecriture de l'entete dans le fichier de sortie
            resout.write_header()

            ## Boucle sur tous les temps et récuperation des variables
            itermin = self.tool.spinBox_max_start.value()
            iterfin = self.tool.spinBox_max_end.value()
            #for num_time, time in enumerate(self.selafinlayer.hydrauparser.getTimes()[itermin:iterfin]):
            for  timeslf in self.selafinlayer.hydrauparser.getTimes()[itermin:iterfin]:
                num_time = np.where(self.selafinlayer.hydrauparser.getTimes() == timeslf)[0][0]
                if (num_time - itermin)%10 == 0:
                    self.status.emit(time.ctime() + ' - Maximum creation - time '+ str(timeslf))
                if num_time != itermin:
                    #var = resin.read(time)
                    var = self.selafinlayer.hydrauparser.getValues(num_time)
                    for num_var, val_var in enumerate(var):
                        if self.selafinlayer.hydrauparser.parametrevx != None and self.selafinlayer.hydrauparser.parametrevy != None and (num_var == self.selafinlayer.hydrauparser.parametrevx or num_var == self.selafinlayer.hydrauparser.parametrevy):
                            #if num_var == self.selafinlayer.parametrevx or num_var == self.selafinlayer.parametrevy:
                            pos_max = np.where(np.abs(var[num_var]) > np.abs(var_max[num_var]))[0] ## On recherche tous les indicides du tableau ou les nouvelles valeurs sont supérieurs aux anciennes
                            var_max[num_var][pos_max] = val_var[pos_max]
                        else:
                            if (self.submersion > -1 or self.duree > -1 ) and self.selafinlayer.hydrauparser.parametreh != None and num_var == self.selafinlayer.hydrauparser.parametreh:
                                pos_sub = np.where(var[num_var] >= 0.05)[0]  #la ou h est sup a 0.05 m
                                if self.duree > -1  :
                                    var_dur[pos_sub] += timeslf - previoustime
                                    previoustime = timeslf
                                if self.submersion > -1 :
                                    #possubpreced = np.isnan(var_sub[num_var])
                                    possubpreced = np.where( np.isnan(var_sub) )[0]        #on cherche les valeurs encore a nan
                                    #self.status.emit('test \n' + str(possubpreced) +'\n' + str(pos_sub))
                                    goodnum = np.intersect1d(pos_sub,possubpreced)  #on intersecte les deux
                                    var_sub[goodnum] = timeslf
                            pos_max = np.where(var[num_var] > var_max[num_var])[0] ## On recherche tous les indicides du tableau ou les nouvelles valeurs sont supérieurs aux anciennes
                            var_max[num_var][pos_max] = val_var[pos_max]
                    ## Maintenant on s'occuppe du cas particulier des vitesses
                    if self.selafinlayer.hydrauparser.parametrevx != None and self.selafinlayer.hydrauparser.parametrevy != None :
                        vit = np.power(np.power(var[self.selafinlayer.hydrauparser.parametrevx],2)+np.power(var[self.selafinlayer.hydrauparser.parametrevy],2),0.5)
                        vit_max = np.power(np.power(var_max[self.selafinlayer.hydrauparser.parametrevx],2)+np.power(var_max[self.selafinlayer.hydrauparser.parametrevy],2),0.5)
                        pos_vmax = np.where(vit > vit_max)[0]
                        var_max[self.selafinlayer.hydrauparser.parametrevx][pos_vmax] = var[self.selafinlayer.hydrauparser.parametrevx][pos_vmax]
                        var_max[self.selafinlayer.hydrauparser.parametrevy][pos_vmax] = var[self.selafinlayer.hydrauparser.parametrevy][pos_vmax]

                    
                else: ## Ce else permet de d'initialiser notre variable max avec le premier pas de temps
                    #var_max = resin.read(time)
                    var_max = self.selafinlayer.hydrauparser.getValues(num_time)
                    if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                        #var_sub = np.array([np.nan]*self.selafinlayer.hydrauparser.pointcount)
                        var_sub = np.array([np.nan]*self.selafinlayer.hydrauparser.facesnodescount)
                        pos_sub = np.where(var_max[self.selafinlayer.hydrauparser.parametreh] >= 0.05)[0]  #la ou h est sup a 0.05 m
                        var_sub[pos_sub] = timeslf
                    if self.duree > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                        #var_dur = np.array([0.0]*self.selafinlayer.hydrauparser.pointcount)
                        var_dur = np.array([0.0]*self.selafinlayer.hydrauparser.facesnodescount)
                        previoustime = timeslf
                        """
                        pos_dur = np.where(var_max[self.selafinlayer.parametreh] >= 0.05)[0]  #la ou h est sup a 0.05 m
                        var_dur[pos_dur] += 1
                        """
                        
            if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                var_sub = np.nan_to_num(var_sub)

            ## Une fois sortie de la boucle le max a ete calculer
            ## On recalcule les directions et les intensites sur le dernier pas de temps

            if self.selafinlayer.hydrauparser.parametrevx != None and self.selafinlayer.hydrauparser.parametrevy != None and (self.intensite or self.direction):
                u = var_max[self.selafinlayer.hydrauparser.parametrevx]
                v = var_max[self.selafinlayer.hydrauparser.parametrevy]
                if self.intensite:
                    val_intensite = np.power(np.power(u,2)+np.power(v,2),0.5)
                    var_max = np.vstack((var_max, val_intensite))
                if self.direction:
                    val_direction = np.arctan2(u,v)*360./(2.*math.pi) +\
                                    np.minimum(np.arctan2(u,v),0.0)/np.arctan2(u,v)*360.

                    ## Dans la creation des directions il peut y avoir des divisions par 0
                    ## Ceci entraine la creation de nan (not a number)
                    ## On va alors remplacer tous ces nan par 0.
                    np.place(val_direction, np.isnan(val_direction), 0.0)
                    var_max = np.vstack((var_max, val_direction))
            
            if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                var_max = np.vstack((var_max, var_sub))
            if self.duree > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                var_max = np.vstack((var_max, var_dur))

            ## Ecriture des valeurs max dans le fichier de sortie (on met un temps à 0 dans le fichier)
            timeoutput = 0.0
            resout.write_frame(timeoutput, var_max)

            ## On ferme les deux fichiers
            resin.close()
            resout.close()
            
            self.finished.emit(self.name_res_out)
                
            """
            except Exception, e:
                self.status.emit('getmax error : ' + str(e))
            """

        """
        except Exception as e:
            print('***', e)
            self.status.emit(str(e))
            self.finished.emit('')
        """
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)
        
class initRunGetMax(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None

    def start(self,selafinlayer, tool, intensite, direction , submersion, duree):
        #Launch worker
        self.worker = runGetMax(selafinlayer, tool, intensite, direction,submersion, duree )
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