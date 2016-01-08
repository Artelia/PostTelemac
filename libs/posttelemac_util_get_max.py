# -*- coding: utf8 -*-
import os
import numpy as np
from math import pi
from time import ctime
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui

from ..libs_telemac.other.Class_Serafin import Serafin

class runGetMax(QtCore.QObject):

    def __init__(self,selafinlayer, intensite = False, direction = False, submersion = -1, duree = -1):
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafinlayer
        self.name_res = self.selafinlayer.selafinpath
        self.name_res_out = self.selafinlayer.selafinpath.split('.')[0] + '_Max.res'
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
        try:
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
            for param in self.selafinlayer.parametres:
                if param[2]:        #for virtual parameter
                    resout.nbvar += 1
                    resout.nomvar.append(str(param[1]))
            if self.intensite:
                resout.nbvar += 1
                resout.nomvar.append('intensite')
            if self.direction:
                resout.nbvar += 1
                resout.nomvar.append('direction')
            if self.submersion > -1 and self.selafinlayer.parametreh != None :
                resout.nbvar += 1
                resout.nomvar.append('submersion')
            if self.duree > -1  and self.selafinlayer.parametreh != None :
                resout.nbvar += 1
                resout.nomvar.append('duree')

            ## Ecriture de l'entete dans le fichier de sortie
            resout.write_header()

            ## Boucle sur tous les temps et récuperation des variables
            for num_time, time in enumerate(self.selafinlayer.selafinparser.getTimes()):
                if num_time%10 == 0:
                    self.status.emit(ctime() + ' - Maximum creation - time '+ str(time))
                if num_time != 0:
                    #var = resin.read(time)
                    var = self.selafinlayer.getValues(num_time)
                    for num_var, val_var in enumerate(var):
                        if self.selafinlayer.parametrevx != None and self.selafinlayer.parametrevy != None and (num_var == self.selafinlayer.parametrevx or num_var == self.selafinlayer.parametrevy):
                            #if num_var == self.selafinlayer.parametrevx or num_var == self.selafinlayer.parametrevy:
                            pos_max = np.where(np.abs(var[num_var]) > np.abs(var_max[num_var]))[0] ## On recherche tous les indicides du tableau ou les nouvelles valeurs sont supérieurs aux anciennes
                            var_max[num_var][pos_max] = val_var[pos_max]
                        else:
                            if (self.submersion > -1 or self.duree > -1 ) and self.selafinlayer.parametreh != None and num_var == self.selafinlayer.parametreh:
                                pos_sub = np.where(var[num_var] >= 0.05)[0]  #la ou h est sup a 0.05 m
                                if self.duree > -1  :
                                    var_dur[pos_sub] += time - previoustime
                                    previoustime = time
                                if self.submersion > -1 :
                                    #possubpreced = np.isnan(var_sub[num_var])
                                    possubpreced = np.where( np.isnan(var_sub) )[0]        #on cherche les valeurs encore a nan
                                    #self.status.emit('test \n' + str(possubpreced) +'\n' + str(pos_sub))
                                    goodnum = np.intersect1d(pos_sub,possubpreced)  #on intersecte les deux
                                    var_sub[goodnum] = time
                            pos_max = np.where(var[num_var] > var_max[num_var])[0] ## On recherche tous les indicides du tableau ou les nouvelles valeurs sont supérieurs aux anciennes
                            var_max[num_var][pos_max] = val_var[pos_max]
                    ## Maintenant on s'occuppe du cas particulier des vitesses
                    if self.selafinlayer.parametrevx != None and self.selafinlayer.parametrevy != None :
                        vit = np.power(np.power(var[self.selafinlayer.parametrevx],2)+np.power(var[self.selafinlayer.parametrevy],2),0.5)
                        vit_max = np.power(np.power(var_max[self.selafinlayer.parametrevx],2)+np.power(var_max[self.selafinlayer.parametrevy],2),0.5)
                        pos_vmax = np.where(vit > vit_max)[0]
                        var_max[self.selafinlayer.parametrevx][pos_vmax] = var[self.selafinlayer.parametrevx][pos_vmax]
                        var_max[self.selafinlayer.parametrevy][pos_vmax] = var[self.selafinlayer.parametrevy][pos_vmax]

                    
                else: ## Ce else permet de d'initialiser notre variable max avec le premier pas de temps
                    #var_max = resin.read(time)
                    var_max = self.selafinlayer.getValues(num_time)
                    if self.submersion > -1 and self.selafinlayer.parametreh != None:
                        var_sub = np.array([np.nan]*self.selafinlayer.selafinparser.pointcount)
                        pos_sub = np.where(var_max[self.selafinlayer.parametreh] >= 0.05)[0]  #la ou h est sup a 0.05 m
                        var_sub[pos_sub] = time
                    if self.duree > -1 and self.selafinlayer.parametreh != None:
                        var_dur = np.array([0]*self.selafinlayer.selafinparser.pointcount)
                        previoustime = time
                        """
                        pos_dur = np.where(var_max[self.selafinlayer.parametreh] >= 0.05)[0]  #la ou h est sup a 0.05 m
                        var_dur[pos_dur] += 1
                        """
                        
            if self.submersion > -1 and self.selafinlayer.parametreh != None:
                var_sub = np.nan_to_num(var_sub)

            ## Une fois sortie de la boucle le max a ete calculer
            ## On recalcule les directions et les intensites sur le dernier pas de temps

            if self.selafinlayer.parametrevx != None and self.selafinlayer.parametrevy != None and (self.intensite or self.direction):
                u = var_max[self.selafinlayer.parametrevx]
                v = var_max[self.selafinlayer.parametrevy]
                if self.intensite:
                    val_intensite = np.power(np.power(u,2)+np.power(v,2),0.5)
                    var_max = np.vstack((var_max, val_intensite))
                if self.direction:
                    val_direction = np.arctan2(u,v)*360./(2.*pi) +\
                                    np.minimum(np.arctan2(u,v),0.0)/np.arctan2(u,v)*360.

                    ## Dans la creation des directions il peut y avoir des divisions par 0
                    ## Ceci entraine la creation de nan (not a number)
                    ## On va alors remplacer tous ces nan par 0.
                    np.place(val_direction, np.isnan(val_direction), 0.0)
                    var_max = np.vstack((var_max, val_direction))
            
            if self.submersion > -1 and self.selafinlayer.parametreh != None:
                var_max = np.vstack((var_max, var_sub))
            if self.duree > -1 and self.selafinlayer.parametreh != None:
                var_max = np.vstack((var_max, var_dur))

            ## Ecriture des valeurs max dans le fichier de sortie (on met un temps à 0 dans le fichier)
            time = 0.0
            resout.write_frame(time, var_max)

            ## On ferme les deux fichiers
            resin.close()
            resout.close()
            
            self.finished.emit(self.name_res_out)
        except Exception, e:
            self.status.emit(str(e))
        
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)
        
class initRunGetMax(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None

    def start(self,selafinlayer, intensite, direction , submersion, duree):
        #Launch worker
        self.worker = runGetMax(selafinlayer, intensite, direction,submersion, duree )
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
