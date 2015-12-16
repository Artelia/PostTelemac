"""@author Christopher J. Cawthorn and Sebastien E. Bourban
"""
"""@note ... this work is based on a collaborative effort between
  .________.                                                          ,--.
  |        |                                                      .  (  (
  |,-.    /   HR Wallingford                EDF - LNHE           / \_ \_/ .--.
  /   \  /    Howbery Park,                 6, quai Watier       \   )   /_   )
   ,.  `'     Wallingford, Oxfordshire      78401 Cedex           `-'_  __ `--
  /  \   /    OX10 8BA, United Kingdom      Chatou, France        __/ \ \ `.
 /    `-'|    www.hrwallingford.com         innovation.edf.com   |    )  )  )
!________!                                                        `--'   `--
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

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
from struct import unpack,pack
import sys
from os import path,getcwd
import glob
import numpy as np
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
   v = vars.split(';')
   for ivar in range(len(v)):
      vi = v[ivar].split(':')[0]
      for jvar in range(len(ALLVARS)):
         if vi.lower() in ALLVARS[jvar].lower():  #.strip()
            ids.append(jvar)
            names.append(ALLVARS[jvar].strip())
   if len(ids) < len(v):
      print "... Could not find ",v," in ",ALLVARS
      print "   +> may be you forgot to switch name spaces into underscores in your command ?"
      sys.exit()

   return ids,names

def getValueHistorySLF( f,tags,time,(le,ln,bn),NVAR,NPOIN3,(varsIndexes,varsName) ):

   # ~~ Subset time ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # /!\ History requires 2 values, both values should be integers starting from 0 to -1, just like frame
   if len(time) != 2:
      print "... A time history needs 2 frames. You seem to wish to extract ",len(time)," frame(s)."
      sys.exit()
   for i in range(len(time)):
      if time[i] < 0: time[i] = max( 0, len(tags['cores']) + time[i] )
      else: time[i] = min( time[i], len(tags['cores'])-1 )
   subset = []
   for t in range(len(tags['cores'])):
      if t >= time[0] and t <= time[1]: subset.append(t)
   if len(subset) < 3:
      print "... A time history needs 2 frames. I could not find any time stamps given the interval: ",time
      sys.exit()

   # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   z = np.zeros((len(varsIndexes),len(bn),len(subset)))
   for t in range(len(subset)):
      f.seek(tags['cores'][subset[t]])
      f.seek(4+4+4,1)
      for ivar in range(NVAR):
         f.seek(4,1)
         if ivar in varsIndexes:
            VARSOR = unpack('>'+str(NPOIN3)+'f',f.read(4*NPOIN3))
            for xy in range(len(bn)):
               z[varsIndexes.index(ivar)][xy][t] = bn[xy][0]*VARSOR[ln[xy][0]] + bn[xy][1]*VARSOR[ln[xy][1]] + bn[xy][2]*VARSOR[ln[xy][2]]
         else:
            f.seek(4*NPOIN3,1)
         f.seek(4,1)

   return ('Time (s)',tags['times'][subset]),z

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
            if insiders.has_key((e[k],e[(k+1)%3])):
               a,b = insiders[(e[k],e[(k+1)%3])]
               if a == i: neighbours[i][k] = b
               if b == i: neighbours[i][k] = a
            if insiders.has_key((e[(k+1)%3],e[k])):
               a,b = insiders[(e[(k+1)%3],e[k])]
               if a == i: neighbours[i][k] = b
               if b == i: neighbours[i][k] = a
      #pbar.write('    +> listing neighbours of edges completed',ibar)
      if showbar: pbar.finish()

   return neighbours

def getValuePolylineSLF(f,tags,time,(p,ln,bn),TITLE,NVAR,NPOIN3,(varsIndexes,varsName)):
   # TODO: rework subset of time with 3 frames or more, whether
   #    they define a range or a series of frames. The later is assumed for now
   # ~~ Subset time ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if len(time) < 1:
      print "... At least 1 frames is asked for."
      sys.exit()
   subset = []
   for i in range(len(time)):
      if time[i] < 0: subset.append(max( 0, len(tags['cores']) + time[i] ))
      else: subset.append(max( time[i], len(tags['cores'])-1 ))

   # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   z = np.zeros((len(varsIndexes),len(subset),len(p))) #,len(tags['cores'])))
   # ~~ Extract distances along ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # TODO: convert x into a numpy array calculation
   d = 0.0
   x = [ d ]
   for xy in range(len(p)-1):
      d = d + np.sqrt( np.power(p[xy+1][0]-p[xy][0],2) + np.power(p[xy+1][1]-p[xy][1],2) )
      x.append(d)
   # ~~ Extract data along line ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for it,t in zip(range(len(subset)),subset):   # /!\ assumes a series of frames
      f.seek(tags['cores'][t])
      f.read(4+4+4)
      for ivar in range(NVAR):
         f.read(4)
         if ivar in varsIndexes:
            VARSOR = unpack('>'+str(NPOIN3)+'f',f.read(4*NPOIN3))
            for xy in range(len(p)):
               z[varsIndexes.index(ivar)][it][xy] = bn[xy]*VARSOR[ln[xy][0]] + (1.0-bn[xy])*VARSOR[ln[xy][1]]
         else:
            f.read(4*NPOIN3)
         f.read(4)

   return ('Distance (m)',x),p,subset,z

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

   DATETIME = [1972,07,13,17,24,27]  # ... needed here because optional in SLF
   
   def __init__(self,fileName):
      self.fileName = fileName
      if fileName != '':
         self.file = open(fileName,'rb')
         # ~~> header parameters
         self.tags = { 'meta': self.file.tell() }
         self.getHeaderParametersSLF()
         # ~~> mesh and connectivity
         self.tags.update({ 'mesh': self.file.tell() })
         self.getHeaderMeshSLF()
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

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #   Parsing the Big-Endian binary file
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   def getHeaderParametersSLF(self):
      f = self.file
      # ~~ Read title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,self.TITLE,chk = unpack('>i80si',f.read(4+80+4))
      if l!=chk:
         print '... Cannot read the TITLE of your SELAFIN file'
         print '     +> Maybe it is the wrong file format or wrong Endian ?'
         sys.exit()
      # ~~ Read NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,self.NBV1,self.NBV2,chk = unpack('>iiii',f.read(4+8+4))
      self.NVAR = self.NBV1 + self.NBV2
      self.VARINDEX = range(self.NVAR)
      # ~~ Read variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      self.VARNAMES = []; self.VARUNITS = []
      for i in range(self.NBV1):
         l,vn,vu,chk = unpack('>i16s16si',f.read(4+16+16+4))
         self.VARNAMES.append(vn)
         self.VARUNITS.append(vu)
      self.CLDNAMES = []; self.CLDUNITS = []
      for i in range(self.NBV2):
         l,vn,vu,chk = unpack('>i16s16si',f.read(4+16+16+4))
         self.CLDNAMES.append(vn)
         self.CLDUNITS.append(vu)
      # ~~ Read IPARAM array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      d = unpack('>12i',f.read(4+40+4))
      self.IPARAM = np.asarray( d[1:11] )
      # ~~ Read DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      self.DATETIME = [1972,07,13,17,15,13]
      if self.IPARAM[9] == 1:
         d = unpack('>8i',f.read(4+24+4))
         self.DATETIME = np.asarray( d[1:9] )
      # ~~ Read NELEM3, NPOIN3, NDP3, NPLAN ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,self.NELEM3,self.NPOIN3,self.NDP3,self.NPLAN,chk = unpack('>6i',f.read(4+16+4))
      self.NELEM2 = self.NELEM3
      self.NPOIN2 = self.NPOIN3
      self.NDP2 = self.NDP3
      self.NPLAN = max( 1,self.NPLAN )
      if self.IPARAM[6] > 1:
         self.NPLAN = self.IPARAM[6] # /!\ How strange is that ?
         self.NELEM2 = self.NELEM3 / ( self.NPLAN - 1 )
         self.NPOIN2 = self.NPOIN3 / self.NPLAN
         self.NDP2 = self.NDP3 / 2

   def getHeaderMeshSLF(self):
      f = self.file
      # ~~ Read the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.IKLE3 = np.array( unpack('>'+str(self.NELEM3*self.NDP3)+'i',f.read(4*self.NELEM3*self.NDP3)) ) - 1
      f.seek(4,1)
      if self.NPLAN > 1: self.IKLE2 = np.compress( self.IKLE3 < self.NPOIN2, self.IKLE3 ).reshape((self.NELEM2,self.NDP2))
      self.IKLE3 = self.IKLE3.reshape((self.NELEM3,self.NDP3))
      if self.NPLAN == 1: self.IKLE2 = self.IKLE3
      # ~~ Read the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.IPOB3 = np.asarray( unpack('>'+str(self.NPOIN3)+'i',f.read(4*self.NPOIN3)) )
      f.seek(4,1)
      self.IPOB2 = self.IPOB3[0:self.NPOIN2]
      # ~~ Read the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.MESHX = np.asarray( unpack('>'+str(self.NPOIN3)+'f',f.read(4*self.NPOIN3))[0:self.NPOIN2] )
      f.seek(4,1)
      # ~~ Read the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
      f.seek(4,1)
      self.MESHY = np.asarray( unpack('>'+str(self.NPOIN3)+'f',f.read(4*self.NPOIN3))[0:self.NPOIN2] )
      f.seek(4,1)

   def getTimeHistorySLF(self):
      f = self.file
      ATs = []; ATt = []
      while True:
         try:
            ATt.append(f.tell())
            # ~~ Read AT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            f.seek(4,1)
            ATs.append(unpack('>f',f.read(4))[0])
            f.seek(4,1)
            # ~~ Skip Values ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            f.seek(self.NVAR*(4+4*self.NPOIN3+4),1)
         except:
            ATt.pop(len(ATt)-1)   # since the last record failed the try
            break
      self.tags.update({ 'cores': ATt })
      self.tags.update({ 'times': np.asarray(ATs) })

   def getVariablesAt( self,frame,varsIndexes ):
      f = self.file
      z = np.zeros((len(varsIndexes),self.NPOIN3))
      # if tags has 31 frames, len(tags)=31 from 0 to 30, then frame should be >= 0 and < len(tags)
      if frame < len(self.tags['cores']) and frame >= 0:
         f.seek(self.tags['cores'][frame])
         f.seek(4+4+4,1)
         for ivar in range(self.NVAR):
            f.seek(4,1)
            if ivar in varsIndexes:
               z[varsIndexes.index(ivar)] = unpack('>'+str(self.NPOIN3)+'f',f.read(4*self.NPOIN3))
            else:
               f.seek(4*self.NPOIN3,1)
            f.seek(4,1)
      return z

   def appendHeaderSLF(self):
      f = self.fole
      # ~~ Write title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>i80si',80,self.TITLE,80))
     # ~~ Write NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>iiii',4+4,self.NBV1,self.NBV2,4+4))
      # ~~ Write variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      for i in range(self.NBV1):
         f.write(pack('>i',32))
         f.write(pack('>16s',self.VARNAMES[i]))
         f.write(pack('>16s',self.VARUNITS[i]))
         f.write(pack('>i',32))
      for i in range(self.NBV2):
         f.write(pack('>i',32))
         f.write(pack('>16s',self.CLDNAMES[i]))
         f.write(pack('>16s',self.CLDUNITS[i]))
         f.write(pack('>i',32))
      # ~~ Write IPARAM array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>i',4*10))
      for i in range(len(self.IPARAM)): f.write(pack('>i',self.IPARAM[i]))
      f.write(pack('>i',4*10))
      # ~~ Write DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if self.IPARAM[9] == 1:
         f.write(pack('>i',4*6))
         for i in range(6): f.write(pack('>i',self.DATETIME[i]))
         f.write(pack('>i',4*6))
      # ~~ Write NELEM3, NPOIN3, NDP3, NPLAN ~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>6i',4*4,self.NELEM3,self.NPOIN3,self.NDP3,1,4*4))  #/!\ where is NPLAN ?
      # ~~ Write the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>i',4*self.NELEM3*self.NDP3))
      f.write(pack('>'+str(self.NELEM3*self.NDP3)+'i',*(n+1 for e in self.IKLE3 for n in e)))
      f.write(pack('>i',4*self.NELEM3*self.NDP3))
      # ~~ Write the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>i',4*self.NPOIN3))
      f.write(pack('>'+str(self.NPOIN3)+'i',*(self.IPOB3)))
      f.write(pack('>i',4*self.NPOIN3))
      # ~~ Write the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>i',4*self.NPOIN3))
      f.write(pack('>'+str(self.NPOIN3)+'f',*(np.tile(self.MESHX,self.NPLAN))))
      f.write(pack('>i',4*self.NPOIN3))
      # ~~ Write the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
      f.write(pack('>i',4*self.NPOIN3))
      f.write(pack('>'+str(self.NPOIN3)+'f',*(np.tile(self.MESHY,self.NPLAN))))
      f.write(pack('>i',4*self.NPOIN3))

   def appendCoreTimeSLF( self,t ):
      f = self.fole
      # Print time record
      f.write(pack('>ifi',4,self.tags['times'][t],4))

   def appendCoreVarsSLF( self,VARSOR ):
      f = self.fole
      # Print variable records
      for v in VARSOR:
         f.write(pack('>i',4*self.NPOIN3))
         f.write(pack('>'+str(self.NPOIN3)+'f',*(v)))
         f.write(pack('>i',4*self.NPOIN3))

   def putContent( self,fileName,showbar=True ):
      self.fole = open(fileName,'wb')
      ibar = 0
      if showbar: pbar = ProgressBar(maxval=len(self.tags['times'])).start()
      self.appendHeaderSLF()
      for t in range(len(self.tags['times'])):
         ibar += 1
         self.appendCoreTimeSLF(t)
         self.appendCoreVarsSLF(self.getVALUES(t))
         if showbar: pbar.update(ibar)
      self.fole.close()
      if showbar: pbar.finish()

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #   Tool Box
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   def getVALUES( self,t ):
      return self.getVariablesAt( t,self.VARINDEX )

   def getSERIES( self,nodes,varsIndexes=[],showbar=True ):
      f = self.file
      if varsIndexes == []: varsIndexes = self.VARINDEX
      # ~~ Ordering the nodes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      # This assumes that nodes starts at 1
      onodes = np.sort(np.array( zip(range(len(nodes)),nodes), dtype=[ ('0',int),('1',int) ] ),order='1')
      # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      z = np.zeros((len(varsIndexes),len(nodes),len(self.tags['cores'])))
      f.seek(self.tags['cores'][0])
      if showbar: pbar = ProgressBar(maxval=len(self.tags['cores'])).start()
      for t in range(len(self.tags['cores'])):
         f.seek(self.tags['cores'][t])
         f.seek(4+4+4,1)
         if showbar: pbar.update(t)
         for ivar in range(self.NVAR):
            f.seek(4,1)
            if ivar in varsIndexes:
               jnod = onodes[0]
               f.seek(4*(jnod[1]-1),1)
               z[varsIndexes.index(ivar),jnod[0],t] = unpack('>f',f.read(4))[0]
               for inod in onodes[1:]:
                  f.seek(4*(inod[1]-jnod[1]-1),1)
                  z[varsIndexes.index(ivar),inod[0],t] = unpack('>f',f.read(4))[0]
                  jnod = inod
               f.seek(4*self.NPOIN3-4*jnod[1],1)
            else:
               f.seek(4*self.NPOIN3,1)
            f.seek(4,1)
      if showbar: pbar.finish()
      return z

   def __del__(self): self.file.close()

class SELAFINS:

   def __init__(self):
      self.slfs = []
      self.slf = None

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
         max = 1.e-5 + np.max( slf.tags['times'] ) + np.max( self.slfs[0].tags['times'] )
         accuracy = np.power(10.0, -5+np.floor(np.log10(max)))  #/!\ max always positive
         same = same and ( accuracy > \
            np.max( slf.tags['times'] - self.slfs[0].tags['times'] ) - np.min( slf.tags['times'] - self.slfs[0].tags['times'] ) )
      return same

   def pop(self,index=0):
      index = max( 0,min(index,len(self.slfs)-1) )
      return slfs.pop(self.slfs[index])

   def putContent(self,fileName): # TODO: files also have to have the same header
      if self.suite and self.merge:
         if len(self.slfs) == 2:  # /!\ difference only between two files
            self.slf.fole = open(fileName,'wb')
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
         self.slf.fole = open(fileName,'wb')
         ibar = 0; pbar = ProgressBar(maxval=len(self.slf.tags['times'])).start()
         self.slf.appendHeaderSLF()
         for t in range(len(self.slf.tags['times'])):
            ibar += 1
            time = self.slf.tags['times'][t]
            self.slf.appendCoreTimeSLF(t)
            self.slf.appendCoreVarsSLF(getVALUES(t))
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
         self.slf.fole.close()
      elif self.merge:
         self.slf.fole = open(fileName,'wb')
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
         self.slf.fole.close()
      elif len(self.slf.tags['times']) == 1 and len(self.slfs) == 2:
      # self.slf will be distributed over the time frames of the scond other
         self.slf.fole = open(fileName,'wb')
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
         self.slf.fole.close()
      else:
         print "Does not know how to merge your files. Try either:"
         print "    + to make sure your files have the same time support"
         print "    + to make sure your files have the same variables"
         sys.exit()

   def __del__(self):
      if self.slf != None: SELAFIN.__del__(self.slf)
      if self.slfs != []:
         for slf in self.slfs: SELAFIN.__del__(slf)

class PARAFINS(SELAFINS):

   def __init__(self,fileName,root=None):
      SELAFINS.__init__(self)
      # ~~> The main slf is based on the header of the GEO file
      self.slf = SELAFIN(fileName)
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
            sys.exit()
         # ~~> Create the corresponding map
         self.mapPOIN = np.zeros(self.slf.NPOIN3,dtype=np.int)
         for i,slf in zip(range(len(self.slfs)),self.slfs): self.mapPOIN[slf.IPOB3-1] = i

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
      ibar = 0; pbar = ProgressBar(maxval=len(slfnames)).start()
      for file in sorted(slfnames):
         ibar += 1; pbar.write('         ~> '+path.basename(file),ibar)
         slf = SELAFIN(file)
         self.slfs.append(slf)
         pbar.update(ibar)
      pbar.finish()
      return

   def getPALUES(self,t):
      if len(self.slfs) > 0:
         VARSOR = np.zeros((self.slf.NBV1+self.slf.NBV2,self.slf.NPOIN3))
         for slf in self.slfs:
            VARSUB = slf.getVALUES(t)
            for v in range(self.slf.NVAR): VARSOR[v][slf.IPOB3-1] = VARSUB[v]
      else: VARSOR = self.slf.getVALUES(t)
      return VARSOR

   def getSERIES(self,nodes,varsIndexes=[]):
      if varsIndexes == []: varsIndexes = self.slf.VARINDEX
      if len(self.slfs) > 0:
         z = np.zeros((len(varsIndexes),len(nodes),len(self.slf.tags['cores'])))
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
      self.slf.fole = open(fileName,'wb')
      ibar = 0
      if showbar: pbar = ProgressBar(maxval=len(self.slf.tags['times'])).start()
      self.slf.appendHeaderSLF()
      # ~~> Time stepping
      for t in range(len(self.slf.tags['times'])):
         ibar += 1
         self.slf.appendCoreTimeSLF(t) # Time stamps
         self.slf.appendCoreVarsSLF(self.getPALUES(t))
         if showbar: pbar.update(ibar)
      self.slf.fole.close()
      if showbar: pbar.finish()

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Christopher J. Cawthor and Sebastien E. Bourban"
__date__ ="$09-Sep-2011 08:51:29$"

if __name__ == "__main__":
   debug = False

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit()
