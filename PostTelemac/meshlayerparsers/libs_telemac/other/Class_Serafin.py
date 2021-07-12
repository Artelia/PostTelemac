# -*- coding: utf8 -*-

import os
import sys
import warnings
from struct import unpack, pack
import numpy as np
import copy
import matplotlib.tri as tri
import mmap


class Serafin:
    ## French
    nomvar2d = [
        "VITESSE U       M/S             ",
        "VITESSE V       M/S             ",
        "CELERITE        M/S             ",
        "HAUTEUR D'EAU   M               ",
        "SURFACE LIBRE   M               ",
        "FOND            M               ",
        "FROUDE                          ",
        "DEBIT SCALAIRE  M2/S            ",
        "TRACEUR                         ",
        "ENERGIE TURBUL. JOULE/KG        ",
        "DISSIPATION     WATT/KG         ",
        "VISCOSITE TURB. M2/S            ",
        "DEBIT SUIVANT X M2/S            ",
        "DEBIT SUIVANT Y M2/S            ",
        "VITESSE SCALAIREM/S             ",
        "VENT X          M/S             ",
        "VENT Y          M/S             ",
        "PRESSION ATMOS. PASCAL          ",
        "FROTTEMENT                      ",
        "DERIVE EN X     M               ",
        "DERIVE EN Y     M               ",
        "NBRE DE COURANT                 ",
        "COTE MAXIMUM    M               ",
        "TEMPS COTE MAXI S               ",
        "VITESSE MAXIMUM M/S             ",
        "T VITESSE MAXI  S               ",
    ]
    nomvar3d = [
        "COTE Z          M               ",
        "VITESSE U       M/S             ",
        "VITESSE V       M/S             ",
        "VITESSE W       M/S             ",
        "NUX POUR VITESSEM2/S            ",
        "NUY POUR VITESSEM2/S            ",
        "NUZ POUR VITESSEM2/S            ",
        "ENERGIE TURBULENJOULE/KG        ",
        "DISSIPATION     WATT/KG         ",
        "NB DE RICHARDSON                ",
        "DENSITE RELATIVE                ",
        "PRESSION DYNAMIQPA              ",
        "PRESSION HYDROSTPA              ",
        "U CONVECTION    M/S             ",
        "V CONVECTION    M/S             ",
        "W CONVECTION    M/S             ",
        "VOLUMES TEMPS N M3              ",
        "DM1                             ",
        "DHHN            M               ",
        "UCONVC          M/S             ",
        "VCONVC          M/S             ",
        "UD              M/S             ",
        "VD              M/S             ",
        "WD              M/S             ",
        "PRIVE 1         ?               ",
        "PRIVE 2         ?               ",
        "PRIVE 3         ?               ",
        "PRIVE 4         ?               ",
    ]
    ## English
    nomvar2d_ENG = [
        "VELOCITY U      M/S             ",
        "VELOCITY V      M/S             ",
        "CELERITY        M/S             ",
        "WATER DEPTH     M               ",
        "FREE SURFACE    M               ",
        "BOTTOM          M               ",
        "FROUDE NUMBER                   ",
        "SCALAR FLOWRATE M2/S            ",
        "EX TRACER                       ",
        "TURBULENT ENERG.JOULE/KG        ",
        "DISSIPATION     WATT/KG         ",
        "VISCOSITY       M2/S            ",
        "FLOWRATE ALONG XM2/S            ",
        "FLOWRATE ALONG YM2/S            ",
        "SCALAR VELOCITY M/S             ",
        "WIND ALONG X    M/S             ",
        "WIND ALONG Y    M/S             ",
        "AIR PRESSURE    PASCAL          ",
        "BOTTOM FRICTION                 ",
        "DRIFT ALONG X   M               ",
        "DRIFT ALONG Y   M               ",
        "COURANT NUMBER                  ",
        "VARIABLE 23     UNIT   ??       ",
        "VARIABLE 24     UNIT   ??       ",
        "VARIABLE 25     UNIT   ??       ",
        "VARIABLE 26     UNIT   ??       ",
        "HIGH WATER MARK M               ",
        "HIGH WATER TIME S               ",
        "HIGHEST VELOCITYM/S             ",
        "TIME OF HIGH VELS               ",
        "FRICTION VEL.   M/S             ",
    ]
    nomvar3d_ENG = [
        "ELEVATION Z     M               ",
        "VELOCITY U      M/S             ",
        "VELOCITY V      M/S             ",
        "VELOCITY W      M/S             ",
        "NUX FOR VELOCITYM2/S            ",
        "NUY FOR VELOCITYM2/S            ",
        "NUZ FOR VELOCITYM2/S            ",
        "TURBULENT ENERGYJOULE/KG        ",
        "DISSIPATION     WATT/KG         ",
        "RICHARDSON NUMB                 ",
        "RELATIVE DENSITY                ",
        "DYNAMIC PRESSUREPA              ",
        "HYDROSTATIC PRESPA              ",
        "U ADVECTION     M/S             ",
        "V ADVECTION     M/S             ",
        "W ADVECTION     M/S             ",
        "DM1                             ",
        "DHHN            M               ",
        "UCONVC          M/S             ",
        "VCONVC          M/S             ",
        "UD              M/S             ",
        "VD              M/S             ",
        "WD              M/S             ",
        "PRIVE 1         ?               ",
        "PRIVE 2         ?               ",
        "PRIVE 3         ?               ",
        "PRIVE 4         ?               ",
    ]

    def __init__(self, name="", mode="rb", read_time=False, pdt_variable=False):
        self.file = open(name, mode)
        self.name = name
        self.format = "telemac"
        self.title = ""
        self.nbvar = 0
        self.nbvar2 = 0
        self.nomvar = []
        self.date = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.date_supp = []
        self.nelem = 0
        self.npoin = 0
        self.ndp = 0
        self.var_i = 1
        self.ikle = np.array([], dtype="int32")
        self.ipobo = np.array([], dtype="int32")
        self.x = np.array([])
        self.y = np.array([])
        self.entete = 0
        self.taille_pdt = 0
        self.nb_pdt = 0
        self.taille_fichier = 0
        self.pos_fic = 0
        self.pos_pdt = 0

        self.temps = []
        self.min_elem = 99999999.0
        self.max_elem = 0.0
        self.min_surface = 99999999.0
        self.max_surface = 0.0
        self.surface = 0.0

        self.FindH = False
        self.PosH = -1
        self.PosSL = -1
        self.PosZ = -1
        self.PosU = -1
        self.PosV = -1
        self.PosW = -1
        self.ecritV = 0
        self.ecritSL = 0
        self.ecritH = 0

        if mode == "rb" or mode == "r+b":
            self.read_header()
            if read_time:
                self.get_temps(pdt_variable=pdt_variable)

    def read_header(self):
        self.file.seek(0, 0)
        ## Recuperation du nombre d'octet dans le fichier
        self.taille_fichier = os.path.getsize(self.name)

        ## Lecture du titre
        self.file.read(4)  ## debut encadrement
        self.title = self.file.read(80)
        self.file.read(4)  ## fin encadrement

        ## Lecture de nbvar et de nbvar2
        self.file.read(4)  ## debut encadrement
        self.nbvar = unpack(">i", self.file.read(4))[0]  # nbvar
        self.nbvar2 = unpack(">i", self.file.read(4))[0]  # nbvar2
        self.file.read(4)  ## fin encadrement

        ##Lecture du nom des variables
        self.nomvar = []
        for j in range(self.nbvar):
            self.file.read(4)  ## debut encadrement
            nomvar_tempo = self.file.read(32)
            self.file.read(4)  ## fin encadrement
            self.nomvar.append(nomvar_tempo)
            if nomvar_tempo == Serafin.nomvar2d[3] or nomvar_tempo == Serafin.nomvar2d_ENG[3]:
                self.FindH = True
                self.PosH = j
            elif nomvar_tempo == Serafin.nomvar2d[4] or nomvar_tempo == Serafin.nomvar2d_ENG[4]:
                self.PosSL = j
            elif (
                nomvar_tempo == Serafin.nomvar2d[5]
                or nomvar_tempo == Serafin.nomvar2d_ENG[5]
                or nomvar_tempo == Serafin.nomvar3d[0]
                or nomvar_tempo == Serafin.nomvar3d_ENG[0]
            ):
                self.PosZ = j
            elif (
                nomvar_tempo == Serafin.nomvar2d[0]
                or nomvar_tempo == Serafin.nomvar2d_ENG[0]
                or nomvar_tempo == Serafin.nomvar3d[1]
                or nomvar_tempo == Serafin.nomvar3d_ENG[1]
            ):
                self.PosU = j
            elif (
                nomvar_tempo == Serafin.nomvar2d[1]
                or nomvar_tempo == Serafin.nomvar2d_ENG[1]
                or nomvar_tempo == Serafin.nomvar3d[2]
                or nomvar_tempo == Serafin.nomvar3d_ENG[2]
            ):
                self.PosV = j
            elif nomvar_tempo == Serafin.nomvar3d[3] or nomvar_tempo == Serafin.nomvar3d_ENG[3]:
                self.PosW = j

        ## Verification si date dans resultat
        self.file.read(4)
        self.date = unpack(">10i", self.file.read(40))
        self.file.read(4)  ## fin encadrement
        if self.date[-1] == 1:
            ## Lecture des 6 entier (si date)
            self.file.read(4)
            self.date_supp = unpack(">6i", self.file.read(6 * 4))
            self.file.read(4)

        ## Lecture des 4 entier nelem, npoin, ndp et i
        self.file.read(4)  ## debut encadrement

        self.nelem = unpack(">i", self.file.read(4))[0]

        self.npoin = unpack(">i", self.file.read(4))[0]

        self.ndp = unpack(">i", self.file.read(4))[0]

        self.var_i = unpack(">i", self.file.read(4))[0]  ## lecture du point i qui ne nous interesse pas
        self.file.read(4)  ## fin encadrement

        ## On ignore ikle
        self.file.read(4)  ## debut encadrement
        nb_val = ">%ii" % (self.nelem * self.ndp)
        self.ikle = np.array(unpack(nb_val, self.file.read(4 * self.nelem * self.ndp)))
        self.file.read(4)  ## fin encadrement

        ## On ignore IPOBO
        self.file.read(4)  ## debut encadrement
        nb_val = ">%ii" % (self.npoin)
        self.ipobo = np.array(unpack(nb_val, self.file.read(4 * self.npoin)))
        self.file.read(4)  ## fin encadrement

        ## On ignore x
        self.file.read(4)  ## debut encadrement
        nb_val = ">%if" % (self.npoin)
        self.x = np.array(unpack(nb_val, self.file.read(4 * self.npoin)))
        self.file.read(4)  ## fin encadrement

        ## On ignore y
        self.file.read(4)  ## debut encadrement
        nb_val = ">%if" % (self.npoin)
        self.y = np.array(unpack(nb_val, self.file.read(4 * self.npoin)))
        self.file.read(4)  ## fin encadrement

        ## Recherche de la taille de l'entete
        self.entete = (
            (80 + 8)
            + (8 + 8)
            + (self.nbvar * (8 + 32))
            + (40 + 8)
            + (self.date[-1] * ((6 * 4) + 8))
            + (16 + 8)
            + ((int(self.nelem) * self.ndp * 4) + 8)
            + (3 * (int(self.npoin) * 4 + 8))
        )
        self.pos_fic = self.entete

        ## Recherche de la taille de l'enregistrement (combien d'octet pour un PDT)
        self.taille_pdt = 12 + (self.nbvar * (8 + int(self.npoin) * 4))

        ## Recuperation du nombre de PDT
        self.nb_pdt = (self.taille_fichier - self.entete) / self.taille_pdt

        ## Cette liste permet par la suite de lire le bloc entier des variables
        ## et ensuite de supprimer tous les octets d'encadrement
        self.liste2del = []
        for n in range(self.nbvar):
            self.liste2del.extend([n * self.npoin + 2 * n, n * self.npoin + 2 * (n + 1)])

    def get_temps(self, pdt_variable=False):
        self.nb_pdt = int(self.nb_pdt)
        if not pdt_variable:
            if self.nb_pdt < 3:
                for num_time in range(self.nb_pdt):
                    self.file.seek(self.entete + 4 + num_time * self.taille_pdt, 0)
                    self.temps.append(unpack(">f", self.file.read(4))[0])
            else:
                t = []
                for num_time in range(3):
                    self.file.seek(self.entete + 4 + num_time * self.taille_pdt, 0)
                    t.append(unpack(">f", self.file.read(4))[0])
                self.temps.append(t[0])
                for i in range(self.nb_pdt - 1):
                    self.temps.append(t[1] + i * (t[2] - t[1]))
        else:
            ## Recuperation de tous les pas de temps
            self.temps = []
            self.file.seek(self.entete, 0)  ## On se positionne a la fin de l'entete du fichier (debut des PDT)
            for num_time in range(self.nb_pdt):
                self.file.seek(4, 1)
                self.temps.append(unpack(">f", self.file.read(4))[0])
                self.file.seek(self.taille_pdt - 8, 1)
        self.temps = np.array(self.temps)

        ## On se positionne a la fin de l'entete du fichier (debut des PDT)
        self.file.seek(self.entete, 0)

    ## On retire quelques informations provenant du maillage:
    ##  - Le plus petit et le plus grand elements
    ##  - La plus petite et la plus grande surface d'un elements
    ##  - La surface total du modele
    def get_info(self):
        ikle2 = np.reshape(self.ikle, (self.nelem, -1))
        for i in range(self.nelem):
            L1 = (
                (self.x[ikle2[i][0] - 1] - self.x[ikle2[i][1] - 1]) ** 2
                + (self.y[ikle2[i][0] - 1] - self.y[ikle2[i][1] - 1]) ** 2
            ) ** 0.5
            L2 = (
                (self.x[ikle2[i][1] - 1] - self.x[ikle2[i][2] - 1]) ** 2
                + (self.y[ikle2[i][1] - 1] - self.y[ikle2[i][2] - 1]) ** 2
            ) ** 0.5
            L3 = (
                (self.x[ikle2[i][0] - 1] - self.x[ikle2[i][2] - 1]) ** 2
                + (self.y[ikle2[i][0] - 1] - self.y[ikle2[i][2] - 1]) ** 2
            ) ** 0.5
            if min(L1, L2, L3) < self.min_elem:
                self.min_elem = min(L1, L2, L3)
            if max(L1, L2, L3) > self.max_elem:
                self.max_elem = max(L1, L2, L3)
            p = (L1 + L2 + L3) / 2
            Surface_elem = (p * (p - L1) * (p - L2) * (p - L3)) ** 0.5
            if Surface_elem < self.min_surface:
                self.min_surface = Surface_elem
            if Surface_elem > self.max_surface:
                self.max_surface = Surface_elem

            self.surface += Surface_elem

    def copy_info(self, resname):
        self.title = resname.title
        self.nbvar = resname.nbvar
        self.nbvar2 = resname.nbvar2
        self.nomvar = copy.deepcopy(resname.nomvar)
        self.date = copy.deepcopy(resname.date)
        self.date_supp = copy.deepcopy(resname.date_supp)
        self.nelem = resname.nelem
        self.npoin = resname.npoin
        self.ndp = resname.ndp
        self.var_i = resname.var_i
        self.ikle = copy.deepcopy(resname.ikle)
        self.ipobo = copy.deepcopy(resname.ipobo)
        self.x = copy.deepcopy(resname.x)
        self.y = copy.deepcopy(resname.y)
        self.entete = resname.entete
        self.taille_pdt = resname.taille_pdt
        self.nb_pdt = resname.nb_pdt
        self.taille_fichier = resname.taille_fichier

        self.FindH = resname.FindH
        self.PosH = resname.PosH
        self.PosSL = resname.PosSL
        self.PosZ = resname.PosZ
        self.temps = resname.temps

    def write_header(self):
        spacetemp = b" "

        ## Lecture du titre
        self.file.write(pack(">i", 80))  ## debut encadrement
        self.file.write(self.title + spacetemp * (80 - len(self.title)))
        self.file.write(pack(">i", 80))  ## fin encadrement

        ## Lecture de nbvar et de nbvar2
        self.file.write(pack(">i", 2 * 4))  ## debut encadrement
        self.file.write(pack(">i", self.nbvar))  # nbvar
        self.file.write(pack(">i", self.nbvar2))  # nbvar2
        self.file.write(pack(">i", 2 * 4))  ## fin encadrement

        ##Lecture du nom des variables
        for j in range(self.nbvar):
            self.file.write(pack(">i", 32))  ## debut encadrement
            if sys.version_info.major == 3:
                if isinstance(self.nomvar[j], str):
                    self.nomvar[j] = self.nomvar[j].encode()

            self.file.write(self.nomvar[j] + spacetemp * (32 - len(self.nomvar[j])))
            self.file.write(pack(">i", 32))  ## fin encadrement

        ## Verification si date dans resultat
        self.file.write(pack(">i", 10 * 4))  ## debut encadrement
        self.file.write(pack(">10i", *self.date))
        self.file.write(pack(">i", 10 * 4))  ## fin encadrement
        if self.date[-1] == 1:
            ## Lecture des 6 entier (si date)
            self.file.write(pack(">i", 6 * 4))  ## debut encadrement
            self.file.write(pack(">6i", *self.date_supp))
            self.file.write(pack(">i", 6 * 4))  ## fin encadrement

        ## Lecture des 4 entier nelem, npoin, ndp et i
        self.file.write(pack(">i", 4 * 4))  ## debut encadrement
        self.file.write(pack(">i", self.nelem))
        self.file.write(pack(">i", self.npoin))
        self.file.write(pack(">i", self.ndp))
        self.file.write(pack(">i", self.var_i))
        self.file.write(pack(">i", 4 * 4))  ## fin encadrement

        ## On ignore ikle
        self.file.write(pack(">i", 4 * self.nelem * self.ndp))  ## debut encadrement
        nb_val = ">%ii" % (self.nelem * self.ndp)
        self.file.write(pack(nb_val, *self.ikle))
        self.file.write(pack(">i", 4 * self.nelem * self.ndp))  ## fin encadrement

        ## On ignore IPOBO
        self.file.write(pack(">i", 4 * self.npoin))  ## debut encadrement
        nb_val = ">%ii" % (self.npoin)
        self.file.write(pack(nb_val, *self.ipobo))
        self.file.write(pack(">i", 4 * self.npoin))  ## fin encadrement

        ## On ignore x
        self.file.write(pack(">i", 4 * self.npoin))  ## debut encadrement
        nb_val = ">%if" % (self.npoin)
        self.file.write(pack(nb_val, *self.x))
        self.file.write(pack(">i", 4 * self.npoin))  ## fin encadrement

        ## On ignore y
        self.file.write(pack(">i", 4 * self.npoin))  ## debut encadrement
        nb_val = ">%if" % (self.npoin)
        self.file.write(pack(nb_val, *self.y))
        self.file.write(pack(">i", 4 * self.npoin))  ## fin encadrement

    def read(self, time2read, var2del=[], is_time=True, specific_frame=False):

        if is_time:
            pos_time2read = np.where(self.temps == time2read)[0][0]
        else:
            pos_time2read = time2read

        if not specific_frame:
            position = (pos_time2read - self.pos_pdt) * self.taille_pdt + 12
            self.file.seek(position, 1)
            self.pos_pdt = pos_time2read + 1
        else:
            self.file.seek(self.entete, 0)
            for num_time in range(pos_time2read):
                self.file.seek(self.taille_pdt, 1)
                self.pos_pdt = num_time + 1
            self.file.seek(12, 1)

        nb_val = ">%if" % (self.npoin)
        var = []
        for pos_var in range(self.nbvar):
            self.file.read(4)
            var.append(unpack(nb_val, self.file.read(4 * self.npoin)))
            self.file.read(4)

        var = np.array(var)

        if len(var2del) > 0:
            var = np.delete(var, var2del, 0)

        return var

    def read_nodes(self, time2read, liste_nodes, var2del=[], is_time=True):

        warnings.filterwarnings("error")
        if is_time:
            pos_time2read = np.where(self.temps == time2read)[0][0]
        else:
            pos_time2read = time2read

        try:
            position = pos_time2read * self.taille_pdt + 12
            self.file.seek(self.entete + position, 0)
        except Warning:
            self.file.seek(self.entete, 0)
            for num_time in range(pos_time2read):
                self.file.seek(self.taille_pdt, 1)
                self.pos_pdt = num_time + 1
            self.file.seek(12, 1)

        offset = int(self.file.tell() / mmap.ALLOCATIONGRANULARITY) * mmap.ALLOCATIONGRANULARITY
        remain_octet = self.file.tell() - offset
        mm = mmap.mmap(
            self.file.fileno(), remain_octet + (4 * self.npoin + 8) * self.nbvar, access=mmap.ACCESS_READ, offset=offset
        )

        nb_val = ">%if" % (len(liste_nodes))
        var = []
        for pos_var in range(self.nbvar):
            first = remain_octet + (4 + 4 * self.npoin + 4) * pos_var + 4
            last = remain_octet + (4 + 4 * self.npoin + 4) * (pos_var + 1) - 4
            val_tempo = mm[first:last]
            val = b"".join(val_tempo[i : i + 4] for i in liste_nodes)
            var.append(unpack(nb_val, val))

        mm.close()

        var = np.array(var)

        return var

    def write_frame(self, time, var):
        if len(var) != self.nbvar:
            erreur = "Il n'y a pas le meme nombre de variable entre la taille de var et nbvar\n\
                      Le nombre de variable attendu est de {nbvar}, alors \
                      que la dimension de l'enregistrement est de {shape}".format(
                nbvar=self.nbvar, shape=var.shape
            )
            raise Exception(erreur)
        nb_val = ">%if" % (self.npoin)
        self.file.write(pack(">i", 4))
        self.file.write(pack(">f", time))
        self.file.write(pack(">i", 4))
        for val_var in var:
            self.file.write(pack(">i", 4 * self.npoin))
            self.file.write(pack(nb_val, *val_var))
            self.file.write(pack(">i", 4 * self.npoin))

    def in_triangulation(self, points):

        res_elem = []
        coeff = []

        nplan = self.date[6]
        if nplan > 1:
            npoin2d = self.npoin / nplan
            nelem2d = self.nelem / (nplan - 1)
            ikle2d = self.ikle - 1
            ikle2d = ikle2d.reshape((self.nelem, 6))
            ikle2d = ikle2d[:nelem2d, :3]
            x2d = self.x[:npoin2d]
            y2d = self.y[:npoin2d]
        else:
            npoin2d = self.npoin
            ikle2d = self.ikle - 1
            ikle2d = ikle2d.reshape((resin.nelem, 3))
            x2d = self.x
            y2d = self.y
        triang = tri.Triangulation(x2d, y2d, ikle2d)
        findtri = triang.get_trifinder()

        x, y = zip(*points)
        res_elem = findtri(x, y)

        return np.array(res_elem)

    def close(self):
        self.file.close()
