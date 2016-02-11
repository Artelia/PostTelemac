"""@author Christopher J. Cawthorn and Sebastien E. Bourban
"""
"""@note ... this work is based on a collaborative effort between
                           .________.                             ,--.
 HR Wallingford            |        |     EDF - LNHE          .  (  (           Bundesanstalt fur            +-     -+
                           |,-.    /                         / \_ \_/ .--.        Wasserbau             =~~..|_ BAW  |
 Howbery Park,             /   \  /       6, quai Watier     \   )   /_   )                                `^|.`-_   |
 Wallingford, Oxfordshire   ,.  `'        78401 Cedex         `-'_  __ `--      17, Kussmaulstr. PO 210253   +-)   \-+
 OX10 8BA, United Kingdom  /  \   /       Chatou, France      __/ \ \ `.        76152  Karlsruhe, Germany    _/     }
 www.hrwallingford.com    /    `-'|       innovation.edf.com |    )  )  )       www.baw.de               _.=^       )
                         !________!                           `--'   `--                             ______________/
"""
"""@brief
         Tools for handling SELAFIN files and TELEMAC binary related in python
"""
"""@details
         Contains read/write functions for binary (big-endian) SELAFIN files
"""
"""@history 07/12/2011 -- Sebastien E. Bourban:
         Addition of 2 new methods (getVariablesAt and getNeighboursSLF)
         and modifications to others to:
         + replace NBV1+NBV2 by NVAR and varsNumbers by varsIndexes
         + and correct a bug in subsetVariablesSLF
"""
"""@history 07/01/2012 -- Sebastien E. Bourban:
         Implementation of the SELAFIN class and of the putSLF function.
         A number of methods are available to the SELAFIN object to modify
            or transform its content, which are then called upon in putSLF.
"""
"""@history 07/01/2012 -- Sebastien E. Bourban:
         Distinguishing between VARIABLES and CLANDESTINES.
         Also, now learned how mix multiple classes' methods.
"""
"""@history 01/02/2012 -- Sebastien E. Bourban:
         Massively speeding up the read and write of SELAFIN files.
         Also, following discussion with Laure C. Grignon (HRW), addition of
         the getSERIES() method to the SELAFIN class, which will eventually
         replace or at least accelerate getValueHistorySLF
"""
"""@history 20/02/2012 -- Sebastien E. Bourban:
         A new class has been added to handle the information contained in
         CONLIM files: class CONLIM.
         This class has two methods: __init__ and putContent
         + __init__: reads the content of a standard CONLIM file
         + putContent writes both the content to a standard CONLIM file
           or a parallel CONLIM file.
"""
"""@history 12/12/2012 -- Sebastien E. Bourban:
         Massively speeding up the cross-sectioning through meshes, which
            is now implemented within samplers / meshes.py
"""
"""@history 31/07/2013 -- Sebastien E. Bourban:
         Allowing for the 3D extraction of timeseries, etc. including the new
            method getValuePolyplanSLF
"""
"""@history 31/12/2013 -- Leo Stadler and Sebastien E. Bourban:
         Allowing for automated checking of both little and big endians
"""
"""@history 1/01/2014 -- Leo Stadler and Sebastien E. Bourban:
         Allowing for automated checking of both single and double
            precision floats
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
from struct import unpack,pack
import sys
from os import path,getcwd
import glob
from copy import deepcopy
import numpy as np
from scipy.spatial import cKDTree
from matplotlib.tri import Triangulation
# ~~> dependencies towards other modules
# ~~> dependencies towards other pytel/modules
from utils.progressbar import ProgressBar
from utils.files import getFileContent,putFileContent

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def subsetVariablesSLF(vars,ALLVARS):
   ids = []; names = []
   # vars has the form "var1:object;var2:object;var3;var4"
   # /!\ the ; separator might be a problem for command line action
   v = vars.replace(',',';').split(';')
   for ivar in range(len(v)):
      vi = v[ivar].split(':')[0]
      for jvar in range(len(ALLVARS)):
         if vi.lower() in ALLVARS[jvar].lower():  #.strip()
            ids.append(jvar)
            names.append(ALLVARS[jvar].strip())
   if len(ids) < len(v):
      print "... Could not find ",v," in ",ALLVARS
      print "   +> may be you forgot to switch name spaces into underscores in your command ?"
      sys.exit(1)

   return ids,names

def getValueHistorySLF( hook,tags,time,support,NVAR,NPOIN3,NPLAN,(varsIndexes,varsName) ):
   """
      Extraction of time series at points.
      A point could be:
      (a) A point could be a node 2D associated with one or more plan number
      (b) A pair (x,y) associated with one or more plan number
/!\   Vertical interpolation has not been implemented yet.
      Arguments:
      - time: the discrete list of time frame to extract from the time history
      - support: the list of points
      - varsIndexes: the index in the NVAR-list to the variable to extract
   """
   f = hook['hook']
   endian = hook['endian']
   ftype,fsize = hook['float']

   # ~~ Total size of support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   lens = 0
   for xy,zp in support: lens += len(zp)

   # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   z = np.zeros((len(varsIndexes),lens,len(time)))
   if fsize == 4: z = np.zeros((len(varsIndexes),lens,len(time)),dtype=np.float32)
   else: z = np.zeros((len(varsIndexes),lens,len(time)),dtype=np.float64)
   for it in range(len(time)):            # it is from 0 to len(time)-1
      f.seek(tags['cores'][time[it]])     # time[it] is the frame to be extracted
      f.seek(4+fsize+4,1)                     # the file pointer is initialised
      for ivar in range(NVAR):            # ivar is from 0 to NVAR-1
         f.seek(4,1)                      # the file pointer advances through all records to keep on track
         if ivar in varsIndexes:          # extraction of a particular variable
            VARSOR = unpack(endian+str(NPOIN3)+ftype,f.read(fsize*NPOIN3))
            jvar = varsIndexes.index(ivar)
            ipt = 0                       # ipt is from 0 to lens-1 (= all points extracted and all plans extracted)
            for xy,zp in support:
               if type(xy) == type(()):   # xp is a pair (x,y) and you need interpolation
                  for plan in zp:   # /!\ only list of plans is allowed for now
                     z[jvar][ipt][it] = 0.
                     ln,bn = xy
                     for inod in range(len(bn)): z[jvar][ipt][it] += bn[inod]*VARSOR[ln[inod]+plan*NPOIN3/NPLAN]
                     ipt += 1             # ipt advances to keep on track
               else:
                  for plan in zp:   # /!\ only list of plans is allowed for now
                     z[jvar][ipt][it] = VARSOR[xy+plan*NPOIN3/NPLAN]
                     ipt += 1             # ipt advances to keep on track
         else:
            f.seek(fsize*NPOIN3,1)            # the file pointer advances through all records to keep on track
         f.seek(4,1)

   return z

def getEdgesSLF(IKLE,MESHX,MESHY,showbar=True):

   try:
      from matplotlib.tri import Triangulation
      edges = Triangulation(MESHX,MESHY,IKLE).get_cpp_triangulation().get_edges()
   except:
      #print '... you are in bad luck !'
      #print '       ~>  without matplotlib based on python 2.7, this operation takes ages'
      edges = []
      ibar = 0
      if showbar: pbar = ProgressBar(maxval=len(IKLE)).start()
      for e in IKLE:
         ibar += 1
         if showbar: pbar.update(ibar)
         if [e[0],e[1]] not in edges: edges.append([e[1],e[0]])
         if [e[1],e[2]] not in edges: edges.append([e[2],e[1]])
         if [e[2],e[0]] not in edges: edges.append([e[0],e[2]])
      if showbar: pbar.finish()

   return edges

def getNeighboursSLF(IKLE,MESHX,MESHY,showbar=True):

   try:
      from matplotlib.tri import Triangulation
      neighbours = Triangulation(MESHX,MESHY,IKLE).get_cpp_triangulation().get_neighbors()
   except:
      #print '... you are in bad luck !'
      #print '       ~>  without matplotlib based on python 2.7, this operation takes a little longer'
      insiders = {}; bounders = {}
      #print '    +> start listing neighbours of edges'
      ibar = 0
      if showbar: pbar = ProgressBar(maxval=(3*len(IKLE))).start()
      for e,i in zip(IKLE,range(len(IKLE))):
         nk = bounders.keys()
         for k in [0,1,2]:
            ibar += 1
            if showbar: pbar.update(ibar)
            if (e[k],e[(k+1)%3]) not in nk: bounders.update({ (e[(k+1)%3],e[k]):i })
            else:
               j = bounders[(e[k],e[(k+1)%3])]
               insiders.update({(e[k],e[(k+1)%3]):[i,j]})
               del bounders[(e[k],e[(k+1)%3])]
      ibar = 0
      neighbours = - np.ones((len(IKLE),3),dtype=np.int)
      for e,i in zip(IKLE,range(len(IKLE))):
         for k in [0,1,2]:
            ibar += 1
            if showbar: pbar.update(ibar)
            if (e[k],e[(k+1)%3]) in insiders:
               a,b = insiders[(e[k],e[(k+1)%3])]
               if a == i: neighbours[i][k] = b
               if b == i: neighbours[i][k] = a
            if (e[(k+1)%3],e[k]) in insiders:
               a,b = insiders[(e[(k+1)%3],e[k])]
               if a == i: neighbours[i][k] = b
               if b == i: neighbours[i][k] = a
      #pbar.write('    +> listing neighbours of edges completed',ibar)
      if showbar: pbar.finish()

   return neighbours

def getValuePolylineSLF(hook,tags,time,support,NVAR,NPOIN3,NPLAN,(varsIndexes,varsName)):
   """
      Extraction of longitudinal profiles along lines.
      A line is made of points extracted from sliceMesh:
      A point is a pair (x,y) associated with one or more plan number
/!\   Vertical interpolation has not been implemented yet.
      Arguments:
      - time: the discrete list of time frame to extract from the time history
      - support: the list of points intersecting th mesh
      - varsIndexes: the index in the NVAR-list to the variable to extract
   """
   f = hook['hook']
   endian = hook['endian']
   ftype,fsize = hook['float']

   # ~~ Total size of support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   lens = len(support[0][1])

   # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if fsize == 4: z = np.zeros((len(varsIndexes),len(time),lens,len(support)),dtype=np.float32)
   else: z = np.zeros((len(varsIndexes),len(time),lens,len(support)),dtype=np.float64)
   # ~~ Extract data along line ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for it in range(len(time)):            # it is from 0 to len(time)-1
      f.seek(tags['cores'][time[it]])     # time[it] is the frame to be extracted
      f.read(4+fsize+4)                       # the file pointer is initialised
      for ivar in range(NVAR):            # ivar is from 0 to NVAR-1
         f.read(4)                        # the file pointer advances through all records to keep on track
         if ivar in varsIndexes:          # extraction of a particular variable
            VARSOR = unpack(endian+str(NPOIN3)+ftype,f.read(fsize*NPOIN3))
            for ipt in range(len(support)):  # ipt is from 0 to lens-1 (= all points extracted and all plans extracted)
               xy,zp = support[ipt]
               for ipl in range(len(zp)):    # /!\ only list of plans is allowed for now
                  z[varsIndexes.index(ivar)][it][ipl][ipt] = 0.
                  ln,bn = xy
                  for inod in range(len(bn)): z[varsIndexes.index(ivar)][it][ipl][ipt] += bn[inod]*VARSOR[ln[inod]+zp[ipl]*NPOIN3/NPLAN]
         else:
            f.read(fsize*NPOIN3)              # the file pointer advances through all records to keep on track
         f.read(4)

   return z

def getValuePolyplanSLF(hook,tags,time,support,NVAR,NPOIN3,NPLAN,(varsIndexes,varsName)):
   """
      Extraction of variables at a list of times on a list of planes.
      A plane is an integer
/!\   Vertical interpolation has not been implemented yet.
      Arguments:
      - time: the discrete list of time frame to extract from the time history
      - support: the list of planes
      - varsIndexes: the index in the NVAR-list to the variable to extract
   """
   f = hook['hook']
   endian = hook['endian']
   ftype,fsize = hook['float']

   # ~~ Extract planes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if fsize == 4: z = np.zeros((len(varsIndexes),len(time),len(support),NPOIN3/NPLAN),dtype=np.float32)
   else: z = np.zeros((len(varsIndexes),len(time),len(support),NPOIN3/NPLAN),dtype=np.float64)
   # ~~ Extract data on several planes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for it in range(len(time)):            # it is from 0 to len(time)-1
      f.seek(tags['cores'][time[it]])     # time[it] is the frame to be extracted
      f.read(4+fsize+4)                       # the file pointer is initialised
      for ivar in range(NVAR):            # ivar is from 0 to NVAR-1
         f.read(4)                        # the file pointer advances through all records to keep on track
         if ivar in varsIndexes:          # extraction of a particular variable
            VARSOR = unpack(endian+str(NPOIN3)+ftype,f.read(fsize*NPOIN3))
            for ipl in range(len(support)):  # ipt is from 0 to len(support) (= all plans extracted)
               z[varsIndexes.index(ivar)][it][ipl] = VARSOR[support[ipl]*NPOIN3/NPLAN:(support[ipl]+1)*NPOIN3/NPLAN]
         else:
            f.read(fsize*NPOIN3)              # the file pointer advances through all records to keep on track
         f.read(4)

   return z

def getEndianFromChar(f,nchar):
   pointer = f.tell()
   endian = ">"       # "<" means little-endian, ">" means big-endian
   l,c,chk = unpack(endian+'i'+str(nchar)+'si',f.read(4+nchar+4))
   if chk!=nchar:
      endian = "<"
      f.seek(pointer)
      l,c,chk = unpack(endian+'i'+str(nchar)+'si',f.read(4+nchar+4))
   if l!=chk:
      print '... Cannot read '+str(nchar)+' characters from your binary file'
      print '     +> Maybe it is the wrong file format ?'
      sys.exit(1)
   f.seek(pointer)
   return endian

def getFloatTypeFromFloat(f,endian,nfloat):
   pointer = f.tell()
   ifloat = 4
   cfloat = 'f'
   l = unpack(endian+'i',f.read(4))
   if l[0]!=ifloat*nfloat:
      ifloat = 8
      cfloat = 'd'
   r = unpack(endian+str(nfloat)+cfloat,f.read(ifloat*nfloat))
   chk = unpack(endian+'i',f.read(4))
   if l!=chk:
      print '... Cannot read '+str(nfloat)+' floats from your binary file'
      print '     +> Maybe it is the wrong file format ?'
      sys.exit(1)
   f.seek(pointer)
   return cfloat,ifloat

# _____                  ___________________________________________
# ____/ Primary Classes /__________________________________________/
#

class CONLIM:

   def __init__(self,fileName):
      self.fileName = fileName
      # ~~> Columns of integers and floats
      DTYPE = np.dtype=[('lih','<i4'),('liu','<i4'),('liv','<i4'), \
                          ('h','<f4'),('u','<f4'),('v','<f4'),('au','<f4'), \
         ('lit','<i4'),   ('t','<f4'),('at','<f4'),('bt','<f4'), \
         ('n','<i4'),('c','<i4') ]

      if fileName != '':
         # ~~> Number of boundary points ( tuple() necessary for dtype parsing )
         #core = [ tuple((' '.join(c.strip().split()[0:13])+' 0 0.0 0.0 0').split()) for c in getFileContent(fileName) ]
         core = [ tuple(c.strip().split()[0:13]) for c in getFileContent(fileName) ]
         self.NPTFR = len(core)
         self.BOR = np.array( core, DTYPE )
         # ~~> Dictionary of KFRGL
         self.KFRGL = dict(zip( self.BOR['n']-1,range(self.NPTFR) ))

         # ~~> Filtering indices
         self.INDEX = np.array( range(self.NPTFR),dtype=np.int )

   def setNUMLIQ(self,closedContours):

      # ~~> Part linkages
      self.NPTIR = {}
      self.IFAPAR = {}

      # ~~> Extra columns
      DTYPE = np.dtype=[('is','<i4'),('xs','<f4'),('ys','<f4'),('lq','<i4') ]
      core = [ tuple(' 0 0.0 0.0 0'.split()) for c in range(self.NPTFR) ]
      self.POR = np.array( core, DTYPE )

      # ~~> Initiates NUMLIQ
      solids = self.BOR['lih'] == 2
      self.NFRLIQ = 0 # liquid boundary numbers start at 1

      # ~~> Finds TELEMAC's south-east corner


      # ~~> Counts NUMLIQ
      for contour in closedContours: # for the domain boundary and eavery islands
         # ~~> look for a solid point
         inode = 0
         while not solids[self.KFRGL[contour[inode]]] and inode < len(contour): inode += 1
         if inode == len(contour): # No solid boundary found in contour
            self.NFRLIQ += 1
            for i in contour: self.POR['lq'][self.KFRGL[i]] = self.NFRLIQ
            continue # go to next contour
         # ~~> list all liquid boundaries on contour
         wassolid = True
         for i in contour: # this makes sure you go around contour only once
            if not solids[self.KFRGL[contour[inode%len(contour)]]]:
               if wassolid:
                  self.NFRLIQ += 1
                  wassolid = False
               self.POR['lq'][self.KFRGL[contour[inode%len(contour)]]] = self.NFRLIQ
            else: wassolid = True
            inode += 1

      return

   def putContent(self,fileName):

      # standard part of the CONLIM
      core = []
      for ifr in range(self.NPTFR):
         if self.INDEX[ifr] != 0:
            c = ( ' '.join(['{0[' + repr(i) + ']}' for i in range(len(self.BOR[ifr]))]) ).format(self.BOR[ifr])
            if self.NPTIR != {} and self.IFAPAR != {}:
               c += ' '+repr(self.POR[ifr][0])
               c += ' '+repr(float(self.POR[ifr][1]))
               c += ' '+repr(float(self.POR[ifr][2]))
               c += ' '+repr(self.POR[ifr][3])
            core.append( c )

      if self.NPTIR != {} and self.IFAPAR != {}:
      # parrallel part 1 of the CONLIM -- format with i7 /!\
         ntr = self.NPTIR.keys()
         ntr.sort()
         core.append(str(len(ntr)))
         for itr in ntr:
            c = self.NPTIR[itr]
            c.sort()
            c.extend([-1,-1,-1,-1,-1,-1,-1,-1,-1,-1])
            s = repr(itr+1).rjust(7) + ' ' + \
               repr(c[0]).rjust(7) + ' ' + repr(c[1]).rjust(7) + ' ' + repr(c[2]).rjust(7) + ' ' + \
               repr(c[3]).rjust(7) + ' ' + repr(c[4]).rjust(7) + ' ' + repr(c[5]).rjust(7) + ' ' + \
               repr(c[6]).rjust(7) + ' ' + repr(c[7]).rjust(7) + ' ' + repr(c[8]).rjust(7)
            core.append( s )
      # parrallel part 2 of the CONLIM -- format with i9 /!\
         ntr = self.IFAPAR.keys()
         ntr.sort()
         core.append(str(len(ntr)))
         for itr in ntr:
            c = self.IFAPAR[itr]
            s = repr(itr+1).rjust(9) + ' ' + \
               repr(c[1]).rjust(9) + ' ' + repr(c[3]).rjust(9) + ' ' + repr(c[5]).rjust(9) + ' ' + \
               repr(c[0]+1).rjust(9) + ' ' + repr(c[2]+1).rjust(9) + ' ' + repr(c[4]+1).rjust(9)
            core.append( s )

      core.append("")
      putFileContent(fileName,core)

class SELAFIN:
   """                                 (DOXYGEN parsing)
   Class Selafin

   @brief
      Read and create Selafin files with python

   @details
      The idea is to be able to set floatType and floatTypeSize from
      outside when we start to write a selafinfiles.
      This will make it possible to do some kind of converters

   @history
      - switch between big/little endian
      - switch to double precission only for float

   @TODO
      - changes where only tested for simple reading, writing must still be done
      - getSERIES was not tested
      - all appen and put functions must be tested
      - needs some intensive testing
   """

   DATETIME = [1972,07,13,17,24,27]  # ... needed here because optional in SLF (static)

   def __init__(self,fileName):
      self.file = {}
      self.file.update({ 'name': fileName })
      self.file.update({ 'endian': ">" })    # "<" means little-endian, ">" means big-endian
      self.file.update({ 'float': ('f',4) }) #'f' size 4, 'd' = size 8
      if fileName != '':
         self.file.update({ 'hook': open(fileName,'rb') })
         # ~~> checks endian encoding
         self.file['endian'] = getEndianFromChar(self.file['hook'],80)
         # ~~> header parameters
         self.tags = { 'meta': self.file['hook'].tell() } #TODO remove?
         self.getHeaderMetaDataSLF()
         # ~~> sizes and connectivity
         self.getHeaderIntegersSLF()
         # ~~> checks float encoding
         self.file['float'] = getFloatTypeFromFloat(self.file['hook'],self.file['endian'],self.NPOIN3)
         # ~~> xy mesh
         self.getHeaderFloatsSLF()
         # ~~> time series
         self.tags = { 'cores':[],'times':[] }
         self.getTimeHistorySLF()
      else:
         self.TITLE = ''
         self.NBV1 = 0; self.NBV2 = 0; self.NVAR = self.NBV1 + self.NBV2
         self.VARINDEX = range(self.NVAR)
         self.IPARAM = []
         self.NELEM3 = 0; self.NPOIN3 = 0; self.NDP3 = 0; self.NPLAN = 1
         self.NELEM2 = 0; self.NPOIN2 = 0; self.NDP2 = 0
         self.NBV1 = 0; self.VARNAMES = []; self.VARUNITS = []
         self.NBV2 = 0; self.CLDNAMES = []; self.CLDUNITS = []
         self.IKLE3 = []; self.IKLE2 = []; self.IPOB2 = []; self.IPOB3 = []; self.MESHX = []; self.MESHY = []
         self.tags = { 'cores':[],'times':[] }
      self.fole = {}
      self.fole.update({ 'name': '' })
      self.fole.update({ 'endian': self.file['endian'] })
      self.fole.update({ 'float': self.file['float'] })
      self.tree = None
      self.neighbours = None
      self.edges = None
      self.alterZnames = []

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #   Parsing the Big- and Little-Endian binary file
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   def getHeaderMetaDataSLF(self):
      f = self.file['hook']
      endian = self.file['endian']
      # ~~ Read title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,self.TITLE,chk = unpack(endian+'i80si',f.read(4+80+4))
      # ~~ Read NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,self.NBV1,self.NBV2,chk = unpack(endian+'iiii',f.read(4+8+4))
      self.NVAR = self.NBV1 + self.NBV2
      self.VARINDEX = range(self.NVAR)
      # ~~ Read variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      self.VARNAMES = []; self.VARUNITS = []
      for _ in range(self.NBV1):
         l,vn,vu,chk = unpack(endian+'i16s16si',f.read(4+16+16+4))
         self.VARNAMES.append(vn)
         self.VARUNITS.append(vu)
      self.CLDNAMES = []; self.CLDUNITS = []
      for _ in range(self.NBV2):
         l,vn,vu,chk = unpack(endian+'i16s16si',f.read(4+16+16+4))
         self.CLDNAMES.append(vn)
         self.CLDUNITS.append(vu)
      # ~~ Read IPARAM array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      d = unpack(endian+'12i',f.read(4+40+4))
      self.IPARAM = np.asarray( d[1:11] )
      # ~~ Read DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      self.DATETIME = [1972,07,13,17,15,13]
      if self.IPARAM[9] == 1:
         d = unpack(endian+'8i',f.read(4+24+4))
         self.DATETIME = np.asarray( d[1:9] )

   def getHeaderIntegersSLF(self):
      f = self.file['hook']
      endian = self.file['endian']
      # ~~ Read NELEM3, NPOIN3, NDP3, NPLAN ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,self.NELEM3,self.NPOIN3,self.NDP3,self.NPLAN,chk = unpack(endian+'6i',f.read(4+16+4))
      self.NELEM2 = self.NELEM3
      self.NPOIN2 = self.NPOIN3
      self.NDP2 = self.NDP3
      self.NPLAN = max( 1,self.NPLAN )
      if self.IPARAM[6] > 1:
         self.NPLAN = self.IPARAM[6] # /!\ How strange is that ?
         self.NELEM2 = self.NELEM3 / ( self.NPLAN - 1 )
         self.NPOIN2 = self.NPOIN3 / self.NPLAN
         self.NDP2 = self.NDP3 / 2
      # ~~ Read the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.IKLE3 = np.array( unpack(endian+str(self.NELEM3*self.NDP3)+'i',f.read(4*self.NELEM3*self.NDP3)) ) - 1
      f.seek(4,1)
      self.IKLE3 = self.IKLE3.reshape((self.NELEM3,self.NDP3))
      if self.NPLAN > 1: self.IKLE2 = np.compress( np.repeat([True,False],self.NDP2), self.IKLE3[0:self.NELEM2], axis=1 )
      else: self.IKLE2 = self.IKLE3
      # ~~ Read the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.IPOB3 = np.asarray( unpack(endian+str(self.NPOIN3)+'i',f.read(4*self.NPOIN3)) )
      f.seek(4,1)
      self.IPOB2 = self.IPOB3[0:self.NPOIN2]

   def getHeaderFloatsSLF(self):
      f = self.file['hook']
      endian = self.file['endian']
      # ~~ Read the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
      ftype,fsize = self.file['float']
      f.seek(4,1)
      self.MESHX = np.asarray( unpack(endian+str(self.NPOIN3)+ftype,f.read(fsize*self.NPOIN3))[0:self.NPOIN2] )
      f.seek(4,1)
      # ~~ Read the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.MESHY = np.asarray( unpack(endian+str(self.NPOIN3)+ftype,f.read(fsize*self.NPOIN3))[0:self.NPOIN2] )
      f.seek(4,1)

   def getTimeHistorySLF(self):
      f = self.file['hook']
      endian = self.file['endian']
      ftype,fsize = self.file['float']
      ATs = []; ATt = []
      while True:
         try:
            ATt.append(f.tell())
            # ~~ Read AT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            f.seek(4,1)
            ATs.append(unpack(endian+ftype,f.read(fsize))[0])
            f.seek(4,1)
            # ~~ Skip Values ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            f.seek(self.NVAR*(4+fsize*self.NPOIN3+4),1)
         except:
            ATt.pop(len(ATt)-1)   # since the last record failed the try
            break
      self.tags.update({ 'cores': ATt })
      self.tags.update({ 'times': np.asarray(ATs) })

   def getVariablesAt( self,frame,varsIndexes ):
      f = self.file['hook']
      endian = self.file['endian']
      ftype,fsize = self.file['float']
      if fsize == 4: z = np.zeros((len(varsIndexes),self.NPOIN3),dtype=np.float32)
      else: z = np.zeros((len(varsIndexes),self.NPOIN3),dtype=np.float64)
      # if tags has 31 frames, len(tags)=31 from 0 to 30, then frame should be >= 0 and < len(tags)
      if frame < len(self.tags['cores']) and frame >= 0:
         f.seek(self.tags['cores'][frame])
         f.seek(4+fsize+4,1)
         for ivar in range(self.NVAR):
            f.seek(4,1)
            if ivar in varsIndexes:
               z[varsIndexes.index(ivar)] = unpack(endian+str(self.NPOIN3)+ftype,f.read(fsize*self.NPOIN3))
            else:
               f.seek(fsize*self.NPOIN3,1)
            f.seek(4,1)
      return z

   def alterEndian(self):
      if self.fole['endian'] == ">": self.fole['endian'] = "<"
      else: self.fole['endian'] = ">"

   def alterFloat(self):
      if self.fole['float'] == ('f',4): self.fole['float'] = ('d',8)
      else: self.fole['float'] = ('f',4)

   def alterVALUES(self,vars=None,mZ=1,pZ=0):
      if vars != None:
         self.alterZm = mZ; self.alterZp = pZ; self.alterZnames = vars.split(':')

   def appendHeaderSLF(self):
      f = self.fole['hook']
      endian = self.fole['endian']
      ftype,fsize = self.fole['float']
      # ~~ Write title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'i80si',80,self.TITLE,80))
     # ~~ Write NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'iiii',4+4,self.NBV1,self.NBV2,4+4))
      # ~~ Write variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      for i in range(self.NBV1):
         f.write(pack(endian+'i',32))
         f.write(pack(endian+'16s',self.VARNAMES[i]))
         f.write(pack(endian+'16s',self.VARUNITS[i]))
         f.write(pack(endian+'i',32))
      for i in range(self.NBV2):
         f.write(pack(endian+'i',32))
         f.write(pack(endian+'16s',self.CLDNAMES[i]))
         f.write(pack(endian+'16s',self.CLDUNITS[i]))
         f.write(pack(endian+'i',32))
      # ~~ Write IPARAM array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'i',4*10))
      for i in range(len(self.IPARAM)): f.write(pack(endian+'i',self.IPARAM[i]))
      f.write(pack(endian+'i',4*10))
      # ~~ Write DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if self.IPARAM[9] == 1:
         f.write(pack(endian+'i',4*6))
         for i in range(6): f.write(pack(endian+'i',self.DATETIME[i]))
         f.write(pack(endian+'i',4*6))
      # ~~ Write NELEM3, NPOIN3, NDP3, NPLAN ~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'6i',4*4,self.NELEM3,self.NPOIN3,self.NDP3,1,4*4))  #/!\ where is NPLAN ?
      # ~~ Write the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'i',4*self.NELEM3*self.NDP3))
      f.write(pack(endian+str(self.NELEM3*self.NDP3)+'i',*(self.IKLE3.ravel()+1)))
      f.write(pack(endian+'i',4*self.NELEM3*self.NDP3))
      # ~~ Write the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'i',4*self.NPOIN3))
      f.write(pack(endian+str(self.NPOIN3)+'i',*(self.IPOB3)))
      f.write(pack(endian+'i',4*self.NPOIN3))
      # ~~ Write the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'i',fsize*self.NPOIN3))
      #f.write(pack(endian+str(self.NPOIN3)+ftype,*(np.tile(self.MESHX,self.NPLAN))))
      for i in range(self.NPLAN): f.write(pack(endian+str(self.NPOIN2)+ftype,*(self.MESHX)))
      f.write(pack(endian+'i',fsize*self.NPOIN3))
      # ~~ Write the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack(endian+'i',fsize*self.NPOIN3))
      #f.write(pack(endian+str(self.NPOIN3)+ftype,*(np.tile(self.MESHY,self.NPLAN))))
      for i in range(self.NPLAN): f.write(pack(endian+str(self.NPOIN2)+ftype,*(self.MESHY)))
      f.write(pack(endian+'i',fsize*self.NPOIN3))

   def appendCoreTimeSLF( self,t ):
      f = self.fole['hook']
      endian = self.fole['endian']
      ftype,fsize = self.fole['float']
      # Print time record
      if type(t) == type(0.0): f.write(pack(endian+'i'+ftype+'i',fsize,t,fsize))
      else: f.write(pack(endian+'i'+ftype+'i',fsize,self.tags['times'][t],fsize))

   def appendCoreVarsSLF( self,VARSOR ):
      f = self.fole['hook']
      endian = self.fole['endian']
      ftype,fsize = self.fole['float']
      # Print variable records
      for v in VARSOR:
         f.write(pack(endian+'i',fsize*self.NPOIN3))
         f.write(pack(endian+str(self.NPOIN3)+ftype,*(v)))
         f.write(pack(endian+'i',fsize*self.NPOIN3))

   def putContent( self,fileName,showbar=True ):
      self.fole.update({ 'name': fileName })
      self.fole.update({ 'hook': open(fileName,'wb') })
      ibar = 0
      if showbar: pbar = ProgressBar(maxval=len(self.tags['times'])).start()
      self.appendHeaderSLF()
      for t in range(len(self.tags['times'])):
         ibar += 1
         self.appendCoreTimeSLF(t)
         self.appendCoreVarsSLF(self.getVALUES(t))
         if showbar: pbar.update(ibar)
      self.fole['hook'].close()
      if showbar: pbar.finish()

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #   Tool Box
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   def getVALUES( self,t ):
      VARSOR = self.getVariablesAt( t,self.VARINDEX )
      for v in self.alterZnames:
         for iv in range(len(self.VARNAMES)):
            if v.lower() in self.VARNAMES[iv].lower(): VARSOR[iv] = self.alterZm * VARSOR[iv] + self.alterZp
         for iv in range(len(self.CLDNAMES)):
            if v.lower() in self.CLDNAMES[iv].lower(): VARSOR[iv+self.NBV1] = self.alterZm * VARSOR[iv+self.NBV1] + self.alterZp
      return VARSOR

   def getSERIES( self,nodes,varsIndexes=[],showbar=True ):
      f = self.file['hook']
      endian = self.file['endian']
      ftype,fsize = self.file['float']
      if varsIndexes == []: varsIndexes = self.VARINDEX
      # ~~ Ordering the nodes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      # This assumes that nodes starts at 1
      onodes = np.sort(np.array( zip(range(len(nodes)),nodes), dtype=[ ('0',int),('1',int) ] ),order='1')
      # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if fsize == 4: z = np.zeros((len(varsIndexes),len(nodes),len(self.tags['cores'])),dtype=np.float32)
      else: z = np.zeros((len(varsIndexes),len(nodes),len(self.tags['cores'])),dtype=np.float64)
      f.seek(self.tags['cores'][0])
      if showbar: pbar = ProgressBar(maxval=len(self.tags['cores'])).start()
      for t in range(len(self.tags['cores'])):
         f.seek(self.tags['cores'][t])
         f.seek(4+fsize+4,1)
         if showbar: pbar.update(t)
         for ivar in range(self.NVAR):
            f.seek(4,1)
            if ivar in varsIndexes:
               jnod = onodes[0]
               f.seek(fsize*(jnod[1]-1),1)
               z[varsIndexes.index(ivar),jnod[0],t] = unpack(endian+ftype,f.read(fsize))[0]
               for inod in onodes[1:]:
                  f.seek(fsize*(inod[1]-jnod[1]-1),1)
                  z[varsIndexes.index(ivar),inod[0],t] = unpack(endian+ftype,f.read(fsize))[0]
                  jnod = inod
               f.seek(fsize*self.NPOIN3-fsize*jnod[1],1)
            else:
               f.seek(fsize*self.NPOIN3,1)
            f.seek(4,1)
      if showbar: pbar.finish()
      return z

   def setKDTree(self,set=False):
      if set or self.tree == None:
         #from scipy.spatial import cKDTree
         isoxy = np.column_stack((np.sum(self.MESHX[self.IKLE2],axis=1)/3.0,np.sum(self.MESHY[self.IKLE2],axis=1)/3.0))
         self.tree = cKDTree(isoxy)

   def setMPLTri(self,set=False):
      if set or self.neighbours == None or self.edges == None:
         #from matplotlib.tri import Triangulation
         mpltri = Triangulation(self.MESHX,self.MESHY,self.IKLE2).get_cpp_triangulation()
         self.neighbours = mpltri.get_neighbors()
         self.edges = mpltri.get_edges()

   def __del__(self):
      if self.file['name'] != '': self.file['hook'].close()

class SELAFINS:

   def __init__(self):
      self.slfs = []
      self.slf = None
      self.suite = True
      self.merge = True

   def add(self,fileName):
      slf = SELAFIN(fileName)
      if self.slf == None: self.slf = slf
      self.slfs.append(slf)
      self.suite = self.isSuite()
      self.merge = self.isMerge()

   def isSuite(self):
      same = True
      for slf in self.slfs[1:]:
         for v in slf.VARNAMES: same = same and ( v in self.slfs[0].VARNAMES )
         for v in slf.CLDNAMES: same = same and ( v in self.slfs[0].CLDNAMES )
      return same

   def isMerge(self):
      same = True
      for slf in self.slfs[1:]:
         mmax = 1.e-5 + np.max( slf.tags['times'] ) + np.max( self.slfs[0].tags['times'] )
         accuracy = np.power(10.0, -5+np.floor(np.log10(mmax)))  #/!\ max always positive
         if len(slf.tags['times']) != len(self.slfs[0].tags['times']): same = False
         else:
            same = same and ( accuracy > \
               np.max( slf.tags['times'] - self.slfs[0].tags['times'] ) - np.min( slf.tags['times'] - self.slfs[0].tags['times'] ) )
      return same

   def pop(self,index=0):
      index = max( 0,min(index,len(self.slfs)-1) )
      return self.slfs.pop(self.slfs[index])

   def putContent(self,fileName): # TODO: files also have to have the same header
      if self.suite and self.merge:
         if len(self.slfs) == 2:  # /!\ difference only between two files
            self.slf.fole.update({ 'hook': open(fileName,'wb') })
            self.slf.fole['name'] = fileName
            ibar = 0; pbar = ProgressBar(maxval=len(self.slf.tags['times'])).start()
            self.slf.appendHeaderSLF()
            for t in range(len(self.slf.tags['times'])):
               ibar += 1
               self.slf.appendCoreTimeSLF(t)
               self.slf.appendCoreVarsSLF(self.slf.getVALUES(t)-self.slfs[1].getVALUES(t))
               pbar.update(ibar)
            pbar.finish()
         else: self.slf.putContent(fileName) # just a copy
      elif self.suite:
         self.slf.fole.update({ 'hook': open(fileName,'wb') })
         self.slf.fole['name'] = fileName
         ibar = 0; pbar = ProgressBar(maxval=len(self.slf.tags['times'])).start()
         self.slf.appendHeaderSLF()
         for t in range(len(self.slf.tags['times'])):
            ibar += 1
            time = self.slf.tags['times'][t]
            self.slf.appendCoreTimeSLF(t)
            self.slf.appendCoreVarsSLF(self.slf.getVALUES(t))
            pbar.update(ibar)
         pbar.finish()
         for slf in self.slfs:
            slf.fole = self.slf.fole
            ibar = 0; pbar = ProgressBar(maxval=len(slf.tags['times'])).start()
            for t in range(len(slf.tags['times'])):
               if slf.tags['times'][t] > time:
                  ibar += 1
                  time = slf.tags['times'][t]
                  slf.appendCoreTimeSLF(t)
                  slf.appendCoreVarsSLF(slf.getVALUES(t))
                  pbar.update(ibar)
            pbar.finish()
         self.slf.fole['hook'].close()
      elif self.merge:
         self.slf.fole.update({ 'hook': open(fileName,'wb') })
         self.slf.fole['name'] = fileName
         for slf in self.slfs[1:]:
            slf.fole = self.slf.fole
            idvars = []
            for v in range(len(slf.VARNAMES)):
               if v not in self.slf.VARNAMES:
                  idvars.append(v)
                  self.slf.VARNAMES.append(slf.VARNAMES[v])
                  self.slf.VARUNITS.append(slf.VARUNITS[v])
            for v in range(len(slf.CLDNAMES)):
               if v not in self.slf.CLDNAMES:
                  idvars.append(v+slf.NBV1)
                  self.slf.CLDNAMES.append(slf.CLDNAMES[v])
                  self.slf.CLDUNITS.append(slf.CLDUNITS[v])
            slf.VARINDEX = idvars
            self.slf.NBV1 = len(self.slf.VARNAMES)
            self.slf.NBV2 = len(self.slf.CLDNAMES)
         ibar = 0; pbar = ProgressBar(maxval=len(self.slf.tags['times'])).start()
         self.slf.appendHeaderSLF()
         for t in range(len(self.slf.tags['times'])):
            ibar += 1
            self.slf.appendCoreTimeSLF(t)
            self.slf.appendCoreVarsSLF(self.slf.getVALUES(t))
            for slf in self.slfs[1:]:
               self.slf.appendCoreVarsSLF(slf.getVALUES(t))
            pbar.update(ibar)
         pbar.finish()
         self.slf.fole['hook'].close()
      elif len(self.slf.tags['times']) == 1 and len(self.slfs) == 2:
      # self.slf will be distributed over the time frames of the scond other
         self.slf.fole.update({ 'hook': open(fileName,'wb') })
         self.slf.fole['name'] = fileName
         slf = self.slfs[1]
         slf.fole = self.slf.fole
         idvars = []
         for v in range(len(slf.VARNAMES)):
            if v not in self.slf.VARNAMES:
               idvars.append(v)
               self.slf.VARNAMES.append(slf.VARNAMES[v])
               self.slf.VARUNITS.append(slf.VARUNITS[v])
         for v in range(len(slf.CLDNAMES)):
            if v not in self.slf.CLDNAMES:
               idvars.append(v+slf.NBV1)
               self.slf.CLDNAMES.append(slf.CLDNAMES[v])
               self.slf.CLDUNITS.append(slf.CLDUNITS[v])
         slf.VARINDEX = idvars
         self.slf.NBV1 = len(self.slf.VARNAMES)
         self.slf.NBV2 = len(self.slf.CLDNAMES)
         ibar = 0; pbar = ProgressBar(maxval=len(slf.tags['times'])).start()
         self.slf.appendHeaderSLF()
         for t in range(len(slf.tags['times'])):
            ibar += 1
            slf.appendCoreTimeSLF(slf,t)
            self.slf.appendCoreVarsSLF(self.slf.getVALUES(0))
            slf.appendCoreVarsSLF(slf.getVALUES(t))
            pbar.update(ibar)
         pbar.finish()
         self.slf.fole['hook'].close()
      else:
         print "Does not know how to merge your files. Try either:"
         print "    + to make sure your files have the same time support"
         print "    + to make sure your files have the same variables"
         sys.exit(1)

   def __del__(self):
      if self.slf != None: del self.slf
      if self.slfs != []:
         for slf in self.slfs: del slf

class PARAFINS(SELAFINS):

   def __init__(self,fileName,root=None):
      SELAFINS.__init__(self)
      # ~~> The main slf is based on the header of the GEO file
      self.slf = SELAFIN(fileName)
      self.file = self.slf.file
      self.fole = self.slf.fole
      if root != None:
         # ~~> Loading the individual headers
         self.addRoot(root)
         # ~~> Making sure there are all inter-compatible
         if self.suite and self.merge:
            self.slf.tags = self.slfs[0].tags
            self.slf.NBV1 = self.slfs[0].NBV1; self.slf.VARNAMES = self.slfs[0].VARNAMES; self.slf.VARUNITS = self.slfs[0].VARUNITS
            self.slf.NBV2 = self.slfs[0].NBV2; self.slf.CLDNAMES = self.slfs[0].CLDNAMES; self.slf.CLDUNITS = self.slfs[0].CLDUNITS
            self.slf.NVAR = self.slf.NBV1 + self.slf.NBV2
            self.slf.VARINDEX = range(self.slf.NVAR)
         else:
            print "... Incompatibilities between files for ",path.basename(root)
            sys.exit(1)
         # ~~> Create the corresponding map
         self.mapPOIN = np.zeros(self.slf.NPOIN3,dtype=np.int)
         for i,slf in zip(range(len(self.slfs)),self.slfs): self.mapPOIN[slf.IPOB3-1] = i

   def alterEndian(self): self.slf.alterEndian()

   def alterFloat(self): self.slf.alterFloat()

   def addRoot(self,root):
      # ~~> list all entries
      diroot = path.dirname(root)
      if path.dirname(root).strip() == '': diroot = getcwd()
      root = path.join(diroot,path.basename(root))
      slfnames = glob.glob(root+'?????-?????')
      # ~~> match expression
      if slfnames == []:
         print "... Could not find any sub-files to the root: ",root
         return []
      npsize = len(slfnames)
      for nptime in range(npsize):
         fo = root+'{0:05d}-{1:05d}'.format(npsize-1,nptime)
         if not fo in slfnames:
            print "... Could not find the following sub-file in the list: ",fo
            return []
      print '      +> Reading the header from the following partitions:'
      for fle in sorted(slfnames):
         print '         ~> '+path.basename(fle)
         slf = SELAFIN(fle)
         self.slfs.append(slf)
      return

   def getPALUES(self,t):
      ftype,fsize = self.file['float']
      if len(self.slfs) > 0:
         if fsize == 4: VARSOR = np.zeros((self.slf.NBV1+self.slf.NBV2,self.slf.NPOIN3),dtype=np.float32)
         else: VARSOR = np.zeros((self.slf.NBV1+self.slf.NBV2,self.slf.NPOIN3),dtype=np.float64)
         for slf in self.slfs:
            VARSUB = slf.getVALUES(t)
            for v in range(self.slf.NVAR): VARSOR[v][slf.IPOB3-1] = VARSUB[v]
      else: VARSOR = self.slf.getVALUES(t)
      return VARSOR

   def getSERIES(self,nodes,varsIndexes=[]):
      ftype,fsize = self.file['float']
      if varsIndexes == []: varsIndexes = self.slf.VARINDEX
      if len(self.slfs) > 0:
         if fsize == 4: z = np.zeros((len(varsIndexes),len(nodes),len(self.slf.tags['cores'])),dtype=np.float32)
         else: z = np.zeros((len(varsIndexes),len(nodes),len(self.slf.tags['cores'])),dtype=np.float64)
         mproc = self.mapPOIN[nodes]
         print '      +> Extracting time series from the following partitions:'
         for islf,slf in zip(range(len(self.slfs)),self.slfs):
            if not islf in mproc: continue
            # ~~> Filter the list of nodes according to sub IPOBO
            subGnodes = np.compress( mproc==islf, np.array( zip(range(len(nodes)),nodes), dtype=[ ('r',int),('n',int) ] ) )
            subLnodes = np.searchsorted(np.sort(slf.IPOB2),subGnodes['n']) + 1 # /!\ why does this work in a sorted way ?
            print '         ~> ',len(subLnodes),' nodes from partition ',islf
            # ~~> Get the series from individual sub-files
            subz = slf.getSERIES(subLnodes,varsIndexes)
            # ~~> Reorder according to original list of nodes
            for v in range(len(varsIndexes)): z[v][subGnodes['r']] = subz[v]
         return z
      else: return self.slf.getSERIES(nodes)  # ,varsIndexes not necessary

   def putContent(self,fileName,showbar=True): # TODO: files also have to have the same header
      self.slf.fole.update({ 'hook': open(fileName,'wb') })
      ibar = 0
      if showbar: pbar = ProgressBar(maxval=len(self.slf.tags['times'])).start()
      self.slf.appendHeaderSLF()
      # ~~> Time stepping
      for t in range(len(self.slf.tags['times'])):
         ibar += 1
         self.slf.appendCoreTimeSLF(t) # Time stamps
         self.slf.appendCoreVarsSLF(self.getPALUES(t))
         if showbar: pbar.update(ibar)
      self.slf.fole['hook'].close()
      if showbar: pbar.finish()

   def cutContent(self,root,showbar=True):
      islf = SELAFIN(root)
      print '      +> Writing the core of the following partitions:'
      for slf in self.slfs: #TODO: do this loop in python parallel with a bottle neck at islf.getVALUES(t)
         sub = deepcopy(slf)
         sub.fole.update({ 'endian': islf.fole['endian'] })
         sub.fole.update({ 'float': islf.fole['float'] })
         ftype,fsize = islf.fole['float']
         # ~~ Conversion to local islf ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         # you know the geom is 2D
         # keep the IPOBO2, X2D, Y2D and IKLE2 and replace the rest
         sub.NPLAN = islf.NPLAN
         sub.IPARAM = islf.IPARAM

         # ~~> matching partitions
         if self.slf.NPOIN2 == islf.NPOIN2:
            sub.NDP2 = islf.NDP2
            sub.NDP3 = islf.NDP3
            sub.NPOIN3 = sub.NPOIN2*islf.NPLAN
            if islf.NPLAN > 1:
               sub.NELEM3 = sub.NELEM2*(islf.NPLAN-1)
               sub.IPOB3 = np.ravel(np.add(np.repeat(sub.IPOB2,islf.NPLAN).reshape((sub.NPOIN2,islf.NPLAN)),sub.NPOIN2*np.arange(islf.NPLAN)).T)
               sub.IKLE3 = \
                  np.repeat(sub.NPOIN2*np.arange(islf.NPLAN-1),sub.NELEM2*islf.NDP3).reshape((sub.NELEM2*(islf.NPLAN-1),islf.NDP3)) + \
                  np.tile(np.add(np.tile(sub.IKLE2,2),np.repeat(sub.NPOIN2*np.arange(2),sub.NDP2)),(islf.NPLAN-1,1))
            else:
               sub.NELEM3 = sub.NELEM2
               sub.IPOB3 = sub.IPOB2
               sub.IKLE3 = sub.IKLE2
            indices = sub.IPOB2-1

         # ~~> filtered partitions / non reversable !
         else:
            # Intersection with the local domain (sub of slfs): the intersection could be empty
            intsect = np.in1d(islf.IPOB2,np.sort(sub.IPOB2))
            # The new compressed IPOBO
            sub.IPOB2 = np.compress( intsect, islf.IPOB2 )
            # Those node numbers of the islf you keep ~> converting True/False into indices
            indices = np.arange(len(islf.IPOB2),dtype=np.int)[intsect]
            # Set the array that only includes elements of islf.IKLE2 with at least two nodes in the subdomain
            GKLE2 = islf.IKLE2[np.where( np.sum(np.in1d(islf.IKLE2,np.sort(indices)).reshape(islf.NELEM2,islf.NDP2),axis=1) == islf.NDP2 )]
            # re-numbering IKLE2 as a local connectivity matrix
            KNOLG = np.unique( np.ravel(GKLE2) )
            KNOGL = dict(zip( KNOLG,range(len(KNOLG)) ))
            sub.IKLE2 = - np.ones_like(GKLE2,dtype=np.int)
            for k in range(len(GKLE2)):
               for ki in range(islf.NDP2): sub.IKLE2[k][ki] = KNOGL[GKLE2[k][ki]]    # /!\ sub.IKLE2 has a local numbering, fit to the boundary elements
            # Set the remaining integers
            sub.NPOIN2 = len(sub.IPOB2)
            sub.NELEM2 = len(sub.IKLE2)
            sub.NDP2 = islf.NDP2
            sub.NDP3 = islf.NDP3
            sub.NPOIN3 = sub.NPOIN2*islf.NPLAN
            if islf.NPLAN > 1:
               sub.NELEM3 = sub.NELEM2*(islf.NPLAN-1)
               sub.IPOB3 = np.ravel(np.add(np.repeat(sub.IPOB2,islf.NPLAN).reshape((sub.NPOIN2,islf.NPLAN)),sub.NPOIN2*np.arange(islf.NPLAN)).T)
               sub.IKLE3 = \
                  np.repeat(sub.NPOIN2*np.arange(islf.NPLAN-1),sub.NELEM2*islf.NDP3).reshape((sub.NELEM2*(islf.NPLAN-1),islf.NDP3)) + \
                  np.tile(np.add(np.tile(sub.IKLE2,2),np.repeat(sub.NPOIN2*np.arange(2),sub.NDP2)),(islf.NPLAN-1,1))
            else:
               sub.NELEM3 = sub.NELEM2
               sub.IPOB3 = sub.IPOB2
               sub.IKLE3 = sub.IKLE2
            # Set the remaining floats
            sub.MESHX = islf.MESHX[indices]
            sub.MESHY = islf.MESHY[indices]

         # ~~ Addition of variables from islf ~~~~~~~~~~~~~~~~~~~~~~
         sub.TITLE = islf.TITLE
         sub.DATETIME = islf.DATETIME
         sub.VARNAMES = islf.VARNAMES; sub.VARUNITS = islf.VARUNITS
         sub.CLDNAMES = islf.CLDNAMES; sub.CLDUNITS = islf.CLDUNITS
         sub.NBV1 = islf.NBV1; sub.NBV2 = islf.NBV2
         sub.NVAR = sub.NBV1+sub.NBV2
         # ~~ putContent ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         fileName = path.basename(sub.file['name']).replace(self.slf.file['name'],root)
         sub.fole.update({ 'hook': open(fileName,'wb') })
         sub.appendHeaderSLF()
         print '         ~> '+path.basename(fileName)
         # ~~> Time stepping
         sub.tags['times'] = islf.tags['times']
         if fsize == 4: VARSORS = np.zeros((sub.NVAR,sub.NPOIN3),dtype=np.float32)
         else: VARSORS = np.zeros((sub.NVAR,sub.NPOIN3),dtype=np.float64)
         for t in range(len(islf.tags['times'])):
            sub.appendCoreTimeSLF(t) # Time stamps
            for ivar,var in zip(range(sub.NVAR),islf.getVALUES(t)):
               for n in range(sub.NPLAN): VARSORS[ivar][n*sub.NPOIN2:(n+1)*sub.NPOIN2] = var[n*islf.NPOIN2:(n+1)*islf.NPOIN2][indices]
            sub.appendCoreVarsSLF(VARSORS)
         sub.fole['hook'].close()

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$09-Sep-2011 08:51:29$"

if __name__ == "__main__":
   debug = False

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)
