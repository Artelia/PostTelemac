"""@author Sebastien E. Bourban
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
"""@history 11/11/2011 -- Sebastien E. Bourban
      Implementation of the important bits of METIS in python
"""
"""@brief
      This file contains the top level routines for the multilevel recursive
      bisection algorithm PMETIS.
      Copyright 1997-2009, Regents of the University of Minnesota
"""
"""@note
Graph Data Structure:

      All of the graph partitioning and sparse matrix ordering routines in
   METIS take as input the adjacency structure of the graph and the weights of
   the vertices and edges (if any).
      The adjacency structure of the graph is stored using the compressed
   storage format (CSR). The CSR format is a widely used scheme for storing
   sparse graphs. In this format the adjacency structure of a graph with n
   vertices and m edges is represented using two arrays xadj and adjncy.
      The xadj array is of size n + 1 whereas the adjncy array is of size 2m
   (this is because for each edge between vertices v and u we actually store
   both (v; u) and (u; v)). The adjacency structure of the graph is stored as
   follows. Assuming that vertex numbering starts from 0 (C style), then the
   adjacency list of vertex i is stored in array adjncy starting at index
   xadj[i] and ending at (but not including) index xadj[i+1] (i.e.,
   adjncy[xadj[i]] through and including adjncy[xadj[i+1]-1]). That is, for
   each vertex i, its adjacency list is stored in consecutive locations in the
   array adjncy, and the array xadj is used to point to where it begins and
   where it ends.

Weight Data Structure:

      The weights of the vertices (if any) are stored in an additional array
   called vwgt. If ncon is the number of weights associated with each vertex,
   the array vwgt contains n * ncon elements (recall that n is the number of
   vertices). The weights of the ith vertex are stored in ncon consecutive
   entries starting at location vwgt[i * ncon]. Note that if each vertex has
   only a single weight, then vwgt will contain n elements, and vwgt[i] will
   store the weight of the 22ith vertex. The vertex-weights must be integers
   greater or equal to zero. If all the vertices of the graph have the same
   weight (i.e., the graph is unweighted), then the vwgt can be set to NULL.
   The weights of the edges (if any) are stored in an additional array called
   adjwgt. This array contains 2melements, and the weight of edge adjncy[j]
   is stored at location adjwgt[j]. The edge-weights must be integers greater
   than zero. If all the edges of the graph have the same weight (i.e., the
   graph is unweighted), then the adjwgt can be set to NULL

Mesh Data Structure:

      All of the mesh partitioning and mesh conversion routines in METIS take
   as input the element node array of a mesh. This element node array is stored
   using a pair of arrays called eptr and eind, which are similar to the xadj
   and adjncy arrays used for storing the adjacency structure of a graph.
      The size of the eptr array is n+1, where n is the number of elements in
   the mesh. The size of the eind array is of size equal to the sum of the
   number of nodes in all the elements of the mesh. The list of nodes belonging
   to the ith element of the mesh are stored in consecutive locations of eind
   starting at position eptr[i] up to (but not including) position eptr[i+1].
      This format makes it easy to specify meshes of any type of elements,
   including meshes with mixed element types that have different number of
   nodes per element. As it was the case with the format of the mesh file, the
   ordering of the nodes in each element is not important.
"""
# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
from os import path,getcwd
import numpy as np
# ~~> dependencies towards other siblings
from progressbar import ProgressBar
from files import getFileContent
# ~~> dependencies towards one level up modules
sys.path.append( path.join( path.dirname(sys.argv[0]), '..' ) ) # clever you !
from parsers.parserSELAFIN import CONLIM,SELAFIN,subsetVariablesSLF
from parsers.parserKenue import putInS

# _____                          ___________________________________
# ____/ Primary SELAFIN Classes /__________________________________/
#

class splitSELAFIN():

   def __init__(self,SLFfileName,CLMfileName,SEQfileName='',splitCONLIM=False,DOMfileRoot=''):

      print '\n... Acquiring global files'
      # ~~> Acquire global CONLIM file
      print '    +> CONLIM file'
      self.clm = CONLIM(CLMfileName)
      self.isCONLIM = splitCONLIM

      # ~~> Acquire global SELAFIN file
      print '    +> SELAFIN file'
      self.slf = SELAFIN(SLFfileName)

      # ~~> Acquire global SELAFIN file
      if SEQfileName != '':
         print '    +> SEQUENCE file'
         self.NPARTS,self.NSPLIT,self.KSPLIT = self.getSplitFromSequence(np.array( getFileContent(SEQfileName), dtype='<i4' ))
      else:
         self.NPARTS,self.NSPLIT,self.KSPLIT = self.getSplitFromNodeValues('PROCESSORS')

      print '\n... Split by elements in ',self.NPARTS,' parts\n'

      # ~~> Clean inconsistencies in boundary segments
      self.IPOBO,self.NSPLIT,self.KSPLIT = self.setSplitForBoundaries(self.NSPLIT,self.clm.KFRGL,self.KSPLIT)

      self.PINTER,self.PNHALO,self.PNODDS = \
         self.setSplitForElements( self.IPOBO,self.NPARTS,self.NSPLIT,self.KSPLIT )
      self.slfn = self.copyCommonData()

      # ~~> Optional output file names
      self.isDOMAIN = DOMfileRoot

   #   Make a copy of common information for sub-meshes
   def copyCommonData(self):

      SLFn = SELAFIN('')
      #   Meta data
      SLFn.TITLE = self.slf.TITLE
      SLFn.file = self.slf.file
      SLFn.IPARAM = self.slf.IPARAM
      #   Time
      SLFn.DATETIME = self.slf.DATETIME
      SLFn.tags = self.slf.tags
      #   Variables
      SLFn.NBV1 = self.slf.NBV1
      SLFn.VARNAMES = self.slf.VARNAMES
      SLFn.VARUNITS = self.slf.VARUNITS
      SLFn.NBV2 = self.slf.NBV2
      SLFn.CLDNAMES = self.slf.CLDNAMES
      SLFn.CLDUNITS = self.slf.CLDUNITS
      SLFn.NVAR = self.slf.NVAR
      SLFn.VARINDEX = range(self.slf.NVAR)
      #   Unchanged numbers
      SLFn.NPLAN = self.slf.NPLAN
      SLFn.NDP2 = self.slf.NDP2
      SLFn.NDP3 = self.slf.NDP3

      return SLFn

   #   Split based on a sequence of parts, one for each element (result from METIS)
   def getSplitFromSequence(self,KSPLIT):

      # ~~> NPARTS is the number of parts /!\ does not check continuity vs. missing parts
      NPARTS = max(*KSPLIT)

      NSPLIT = np.zeros( self.slf.NPOIN2 ,dtype=np.int )
      for part in range(NPARTS):
         k = np.compress(KSPLIT==(part+1),range(len(self.slf.IKLE)))
         NSPLIT[self.slf.IKLE[k]] = KSPLIT[k]

      return NPARTS,NSPLIT-1,KSPLIT-1

   #   Split based on the variable PROCESSORS, defined at the nodes
   def getSplitFromNodeValues(self,var):

      # ~~> Filter for 'PROCESSORS' as input to the getVariablesAt method
      i,vn = subsetVariablesSLF(var,self.slf.VARNAMES)
      if i == []:
         print '... Could not find ',var,', you may need another split method'
         sys.exit()
      # ~~> NSPLIT is the interger value of the variable PROCESSORS (time frame 0)
      NSPLIT = np.array( self.slf.getVariablesAt( 0,i )[0], dtype=np.int)

      # ~~> NPARTS is the number of parts /!\ does not check continuity vs. missing parts
      NPARTS = max(*NSPLIT) + 1   # User numbering NSPLIT starts from 0

      KSPLIT = np.minimum(*(NSPLIT[self.slf.IKLE].T))

      return NPARTS,NSPLIT,KSPLIT

   def setSplitForBoundaries(self,NSPLIT,KFRGL,KSPLIT):

      # ~~> Join up the global boundary nodes with the halo elements
      IPOBO = np.zeros(self.slf.NPOIN2,dtype=np.int)
      IPOBO[KFRGL.keys()] = np.array(KFRGL.values(),dtype=np.int)+1  # this is so the nonzero search is easier

      # ~~> Cross check partition quality -- step 1
      found = True; nloop = 0
      while found:
         found = False; nloop += 1
         for k in range(len(self.slf.IKLE)):
            e = self.slf.IKLE[k]
            if KSPLIT[k] != max( NSPLIT[e] ):
               for p1,p2,p3 in zip([0,1,2],[1,2,0],[2,0,1]):
                  if NSPLIT[e[p1]] != KSPLIT[k] and NSPLIT[e[p2]] != KSPLIT[k]:
                     if IPOBO[e[p1]] != 0 and IPOBO[e[p2]] != 0:
                        print '       ~> correcting boundary segment at iteration: ',nloop,(e[p1],e[p2]),k,KSPLIT[k],e,NSPLIT[e]
                        NSPLIT[e[p1]] = NSPLIT[e[p3]]
                        NSPLIT[e[p2]] = NSPLIT[e[p3]]
                        KSPLIT[k] = NSPLIT[e[p3]]
                        found = True

      # ~~> Cross check partition quality -- step 2
      found = True; nloop = 0
      while found:
         found = False; nloop += 1
         for k in range(len(self.slf.IKLE)):
            e = self.slf.IKLE[k]
            if min( NSPLIT[e] ) != max( NSPLIT[e] ) and KSPLIT[k] != min( NSPLIT[e] ):
               print '       ~> correcting internal segment at iteration: ',nloop,k,KSPLIT[k],e,NSPLIT[e]
               KSPLIT[k] = min( NSPLIT[e] )
               found = True

      return IPOBO,NSPLIT,KSPLIT

   #   Split based on the variable PROCESSORS, defined at the nodes
   def setSplitForElements(self,IPOBO,NPARTS,NSPLIT,KSPLIT):

      SNHALO = dict([ (i,[]) for i in range(NPARTS) ])
      PNODDS = dict([ (i,[]) for i in range(NPARTS) ])
      SINTER = dict([ (i,[]) for i in range(NPARTS) ])

      # ~~> Internal segments separating parts
      pbar = ProgressBar(maxval=len(self.slf.IKLE)).start()
      for k in range(len(self.slf.IKLE)):
         e = self.slf.IKLE[k]
         # Case 1: you are at an internal boundary element
         if KSPLIT[k] != max( NSPLIT[e] ):
            for p1,p2 in zip([0,1,2],[1,2,0]):
               if NSPLIT[e[p1]] != KSPLIT[k] and NSPLIT[e[p2]] != KSPLIT[k]:
                  SINTER[KSPLIT[k]].append((e[p1],e[p2]))
                  SINTER[min(NSPLIT[e[p1]],NSPLIT[e[p2]])].append((e[p2],e[p1]))
         # Case 2: you may be at an external boundary element
         if np.count_nonzero( IPOBO[e] ) > 1:
            for p1,p2 in zip([0,1,2],[1,2,0]):
               if IPOBO[e[p1]] != 0 and IPOBO[e[p2]] != 0: # multiplier is not possible
                  if IPOBO[e[p1]] + 1 == IPOBO[e[p2]]: SNHALO[KSPLIT[k]].append((e[p1],e[p2]))
                  else: PNODDS[KSPLIT[k]].append([e[p1],e[p2]])
         pbar.update(k)
      pbar.finish()

      # ~~> Clean-up of funny segments looping on themselves
      for part in range(NPARTS):

         # ~~> Quickly checking through to remove duplicate segments
         found = True
         while found:
            found = False
            INTER = np.array( SINTER[part], dtype=[ ('h',int),('t',int) ] )
            HEADT = np.argsort( INTER['h'] )
            HLINK = np.searchsorted(INTER['h'][HEADT],INTER['t'][HEADT])
            w = 0
            while w < len(HLINK):
               if HLINK[w] < len(HLINK):
                  if INTER['h'][HEADT[w]] == INTER['t'][HEADT[HLINK[w]]] and INTER['t'][HEADT[w]] == INTER['h'][HEADT[HLINK[w]]]:
                     print '       ~> Removing dupicate segments in part: ',part,SINTER[part][HEADT[w]],SINTER[part][HEADT[HLINK[w]]]
                     if HEADT[w] > HEADT[HLINK[w]]:
                        SINTER[part].pop(HEADT[w])
                        SINTER[part].pop(HEADT[HLINK[w]])
                     else:
                        SINTER[part].pop(HEADT[HLINK[w]])
                        SINTER[part].pop(HEADT[w])
                     found = True
                     break
               w += 1

      return SINTER,SNHALO,PNODDS

   def getIKLE(self,npart):

      # ~~> get IKLE for that part ... still with global element numbers
      GIKLE = np.compress( self.KSPLIT==npart,self.slf.IKLE,axis=0 )
      KELLG = np.compress( self.KSPLIT==npart,range(len(self.slf.IKLE)),axis=0 )
      # ~~> KNOLG(NPOIN3) gives the global node number such that
      #   for i = 1,NPOIN3: Fwrite(i) = Fread(KNOLG(i)) and is ordered
      KNOLG,indices = np.unique( np.ravel(GIKLE), return_index=True )
      KNOGL = dict(zip( KNOLG,range(len(KNOLG)) ))
      LIKLE = - np.ones_like(GIKLE,dtype=np.int)
      pbar = ProgressBar(maxval=len(GIKLE)).start()
      for k in range(len(GIKLE)):
         LIKLE[k] = [ KNOGL[GIKLE[k][0]], KNOGL[GIKLE[k][1]], KNOGL[GIKLE[k][2]] ]
         pbar.update(k)
      pbar.finish()

      return LIKLE,KELLG,KNOLG

   def resetPartition(self,part,PINTER,KSPLIT):

      MASKER = np.zeros(self.slf.NPOIN2,dtype=np.int)
      for p in PINTER: MASKER[p] = np.arange(len(p))+1 # PINTER is ordered

      KIKLE = np.compress(np.maximum(*(MASKER[self.slf.IKLE].T))>=0,range(len(self.slf.IKLE)))
      #KIKLE = np.compress(np.count_nonzero(MASKER[self.slf.IKLE],axis=1)>2,range(len(self.slf.IKLE))) # /!\ does not work ?
      pbar = ProgressBar(maxval=len(KIKLE)).start()
      for k in KIKLE:
         e = self.slf.IKLE[k]
         if np.count_nonzero( MASKER[e] ) < 2 or KSPLIT[k] == part: continue
         for p1,p2 in zip([0,1,2],[1,2,0]):
            if MASKER[e[p1]] > 0 and MASKER[e[p2]] > 0 and MASKER[e[p2]] > MASKER[e[p1]]:
               print '       ~> Warning for element of part: ',part,'(was:',KSPLIT[k],') ',k,e
               #KSPLIT[k] = part
         pbar.update(k)
      pbar.finish()

      return KSPLIT

   def joinPairs(self,polyLines):

      INTER = np.array( polyLines, dtype=[ ('h',int),('t',int) ] )
      IDONE = np.ones( len(polyLines),dtype=np.int )
      polyA = []; polyZ = []; polyL = []

      # ~~> Finding the endings
      HEADT = np.argsort( INTER['h'] ) # knowing that INTER[HEADT] is sorted by the head
      HLINK = np.searchsorted(INTER['h'][HEADT],INTER['t'][HEADT]) # INTER['h'][HEADT] is sorted
      # ... HLINK[w] for w in INTER['t'] gives you the position of INTER['t'][w] in INTER['h'][HEADT]
      w = min(np.compress(np.not_equal(IDONE,IDONE*0),range(len(HEADT))))
      po = INTER['h'][HEADT[w]]; pe = INTER['t'][HEADT[w]]; IDONE[w] = 0
      polyA.append(po)
      swapMinMax = True
      while True:
         if HLINK[w] < len(INTER):
            if INTER['t'][HEADT][w] == INTER['h'][HEADT][HLINK[w]]:
               w = HLINK[w]
               pe = INTER['t'][HEADT][w]; IDONE[w] = 0
         if pe not in polyA:
            if HLINK[w] < len(INTER):
               if INTER['t'][HEADT][w] != po and INTER['t'][HEADT][w] == INTER['h'][HEADT][HLINK[w]]: continue
            if po == pe: polyL.append(pe)
            else:
               if pe not in polyZ: polyZ.append(pe)
         else:
            polyA.append(po)
         if np.count_nonzero(IDONE) == 0: break
         if swapMinMax:
            w = max(np.compress(np.not_equal(IDONE,IDONE*0),range(len(HEADT))))
         else:
            w = min(np.compress(np.not_equal(IDONE,IDONE*0),range(len(HEADT))))
         swapMinMax = not swapMinMax
         po = INTER['h'][HEADT[w]]; pe = INTER['t'][HEADT[w]]; IDONE[w] = 0
         polyA.append(po)

      # ~~> Finding the sources
      TAILT = np.argsort( INTER['t'] ) # knowing that INTER[TAILT] is sorted by the tail
      TLINK = np.searchsorted(INTER['t'][TAILT],INTER['h'][TAILT]) # INTER['h'][HEADT] is sorted
      # ... TLINK[w] for w in polyZ gives you the position of polyZ[w] in INTER['t'][TAILT]

      polyGones = []
      # ~~> Finding the sources of non-looping lines
      TAILS = np.searchsorted(INTER['t'][TAILT],polyZ)
      for w in TAILS:
         p = [INTER['t'][TAILT[w]]]
         while True:
            if INTER['h'][TAILT][w] == INTER['t'][TAILT][TLINK[w]]:
               po = [INTER['h'][TAILT][w]]
               po.extend(p)
               p = po; w = TLINK[w]
            if TLINK[w] < len(INTER):
               if INTER['h'][TAILT][w] == INTER['t'][TAILT][TLINK[w]]: continue
            po = [INTER['h'][TAILT][w]]
            po.extend(p)
            p = po
            break
         polyGones.append(p)

      # ~~> Finding the sources of looping lines
      LOOPS = np.searchsorted(INTER['t'][TAILT],polyL)
      for w in LOOPS:
         p = [INTER['t'][TAILT[w]]]
         while True:
            if INTER['h'][TAILT][w] == INTER['t'][TAILT][TLINK[w]]:
               po = [INTER['h'][TAILT][w]]
               po.extend(p)
               p = po; w = TLINK[w]
            if INTER['h'][TAILT][w] != p[len(p)-1]: continue
            po = [INTER['h'][TAILT][w]]
            po.extend(p)
            p = po
            break
         polyGones.append(p)

      return polyGones

   def joinSegments(self,polyLines):

      polyGones = []
      maxbar = max(len(polyLines),1)
      pbar = ProgressBar(maxval=maxbar).start()
      while polyLines != []:
         # ~~> starting point
         e = polyLines[0]
         le = len(e)
         a,b = e[0],e[len(e)-1]
         # ~~> case of closed line
         if a == b:
            polyGones.append(e[0:len(e)]) # /!\ here you keep the duplicated point
            polyLines.pop(0)
            continue
         # ~~> iterative process
         for ei,iline in zip(polyLines[1:],range(len(polyLines))[1:]):
            # ~~> merging the two segments
            if b == ei[0]:
               polyLines[0] = e[0:len(e)]     # copy !
               polyLines[0].extend(ei[1:])
               polyLines.pop(iline)
               break
            if a == ei[len(ei)-1]:
               polyLines[0] = ei[0:len(ei)]   # copy !
               polyLines[0].extend(e[1:])
               polyLines.pop(iline)
               break
         # ~~> completed search
         if le == len(polyLines[0]):
            polyGones.append(e[0:len(e)])
            polyLines.pop(0)
         pbar.update(maxbar-len(polyLines))
      pbar.finish()

      return polyGones

   def tetrisOddSegments(self,main,odds):

      polyGones = []
      lo = len(odds)
      while main != []:
         # ~~> starting point
         e = main[0]
         le = len(e)
         a,b = e[0],e[len(e)-1]
         # ~~> case of closed line
         if a == b:
            polyGones.append(e[0:len(e)]) # /!\ here you keep the duplicated point
            main.pop(0)
            continue
         # ~~> iterative process
         for ei,iline in zip(odds,range(len(odds))):
            # ~~> merging the two segments
            if b == ei[0]:
               main[0] = e[0:len(e)]
               main[0].extend(ei[1:])
               odds.pop(iline)
               break
            if a == ei[len(ei)-1]:
               main[0] = ei[0:len(ei)]
               main[0].extend(e[1:])
               odds.pop(iline)
               break
         # ~~> completed search
         if le == len(main[0]):
            polyGones.append(e[0:len(e)])
            main.pop(0)

      # ~~> removing the over-constrained elements
      for p in polyGones:
         if len(p) > 3:
            j = 2
            while j < len(p):
               if p[j-2] == p[j]:
                  p.pop(j-2)
                  p.pop(j-2)
               j += 1

      return polyGones

   #   Filter poly according to IPOBO on that part.
   #   ~> gloseg: is the ensemble of either closed islands or
   #      open external boundary segments
   #   Note: filtering now seems to mean that to have done a lot of work for nothing
   def globalSegments(self,poly):
      gloseg = []
      for p in poly:
         pA = p[0]; pZ = p[len(p)-1]; closed = False
         if pA == pZ and self.IPOBO[pA] != 0: closed = True
         iA = 0; iZ = 0
         ploseg = []
         for i in p:
            if self.IPOBO[i] != 0: # moves the counter along for external points
               iZ += 1
            elif iZ != 0: # you have just found the end of an external segment
               ploseg.append(p[iA:iA+iZ])
               iA += iZ+1
               iZ = 0
            else:
               iA += 1
         if iZ != 0:
            if closed and len(ploseg) > 0:
               i = p[iA:iA+iZ]
               i.extend(ploseg[0][1:]) # remove duplicate
               ploseg[0] = i
            else: ploseg.append(p[iA:iA+iZ])
         gloseg.extend(ploseg)
      return gloseg

   def putContent(self):

      # ~~> Extension for parallel file names
      fmtn = '00000' + str(self.NPARTS-1)
      fmtn = fmtn[len(fmtn)-5:]

      print '\n... Split the boundary connectivity'
      # ~~> Assemble internal and external segments
      polyCLOSED = dict([ (i,[]) for i in range(self.NPARTS) ])
      polyFILTER = dict([ (i,[]) for i in range(self.NPARTS) ])
      polyGLOSED = []
      for part in range(self.NPARTS): # this could be done in parallel

         print '    +> Joining up boundary segments for part: ',part+1
         # ~~> Joining up boundaries for sub-domains
         print '       ~> main internal segments'
         self.PINTER[part] = self.joinPairs(self.PINTER[part])
         print '       ~> main external segments'
         polyHALO = self.joinPairs(self.PNHALO[part])
         polyHALO.extend(self.PINTER[part])
         polyHALO = self.joinSegments(polyHALO)
         print '       ~> odd segments'
         polyODDS = self.joinSegments(self.PNODDS[part])
         print '       ~> stitching with the odd ones'
         polyGones = self.tetrisOddSegments(polyHALO,polyODDS)
         print '       ~> final closure'
         polyCLOSED[part] = self.joinSegments(polyGones)

         # ~~> Building up the entire picture
         polyFILTER[part] = self.globalSegments(polyCLOSED[part])
         polyGLOSED.extend( polyFILTER[part] )

      # ~~> Joining up boundaries for the global domain (Note: seems counter productive but is not)
      polyGLOSED = self.joinSegments(polyGLOSED)

      if self.isDOMAIN != '':
         print '\n... Printing the domain split into a series of i2s files'
         # ~~> Convert node numbers into x,y
         for part in range(self.NPARTS):
            print '    +> part ',part+1,' of ',self.NPARTS
            polyXY = []
            for pg in range(len(polyCLOSED[part])):
               pxy = []
               for pt in range(len(polyCLOSED[part][pg])):
                  n = polyCLOSED[part][pg][pt]
                  pxy.append([ self.slf.MESHX[n],self.slf.MESHY[n] ])
               polyXY.append(pxy)
            # ~~> Write polygons to double check
            fmti = '00000' + str(part)
            fmti = fmti[len(fmti)-5:]
            fileName = path.join(path.dirname(self.slf.fileName),self.isDOMAIN+fmtn+'-'+fmti+'.i2s')
            putInS(fileName,[],'i2s',polyXY)

         # ~~> Convert node numbers into x,y
         polyXY = []
         for pg in range(len(polyGLOSED)):
            pxy = []
            for pt in range(len(polyGLOSED[pg])):
               n = polyGLOSED[pg][pt]
               pxy.append([ self.slf.MESHX[n],self.slf.MESHY[n] ])
            polyXY.append(pxy)
         # ~~> Write polygons to double check
         fileName = path.join(path.dirname(self.slf.fileName),self.isDOMAIN+'.i2s')
         putInS(fileName,[],'i2s',polyXY)

      print '\n... Final check to the element partitioning'
      for part in range(self.NPARTS): # this could be done in parallel
         self.KSPLIT = self.resetPartition(part,self.PINTER[part],self.KSPLIT)

      if self.isDOMAIN != '':
         # ~~> This is optional
         print '\n... Printing the domain split into a SELAFIN'
         fileRoot,fileExts = path.splitext(self.slf.fileName)
         self.slf.fole = open(fileRoot+'_PROCS'+fileExts,'wb')
         self.slf.appendHeaderSLF()
         self.slf.appendCoreTimeSLF(0)
         VARSOR = self.slf.getVALUES(0)
         for v in range(self.slf.NVAR): VARSOR[v] = self.NSPLIT
         self.slf.appendCoreVarsSLF(VARSOR)
         self.slf.fole.close()

      print '\n... Storing the global liquid boundary numbering (NUMLIQ)'
      # ~~> Implying NUMLIQ and the number NFRLIQ based on the joined-up lines
      self.clm.setNUMLIQ(polyGLOSED)

      print '\n... Split the mesh connectivity'
      # ~~> Preliminary set up for LIKLE, KNOLG and KEMLG by parts
      LIKLE = dict([ (i,[]) for i in range(self.NPARTS) ])
      KELLG = dict([ (i,[]) for i in range(self.NPARTS) ])
      KNOLG = dict([ (i,[]) for i in range(self.NPARTS) ])
      for part in range(self.NPARTS):
         print '    +> re-ordering IKLE for part ',part+1
         LIKLE[part],KELLG[part],KNOLG[part] = self.getIKLE(part)

      # ~~> CONLIM file: Preliminary set up of IFAPAR and ISEG for all parts
      IFAPAR = dict([ (i,{}) for i in range(self.NPARTS) ])

      ISEG = {}
      #   Organising ISEG for easier call: part 1
      for part in range(self.NPARTS):
         for i in polyFILTER[part]:
            if i[0] == i[len(i)-1]: continue                # /!\ you are here adding one !
            if i[0] in ISEG.keys(): ISEG[i[0]].update({ part:i[1]+1 })
            else: ISEG.update({ i[0]:{ part:i[1]+1 } })
            if i[len(i)-1] in ISEG.keys(): ISEG[i[len(i)-1]].update({ part:-i[len(i)-2]-1 })
            else: ISEG.update({ i[len(i)-1]:{ part:-i[len(i)-2]-1 } })
      #   Switching parts of ISEG for final call: part 2
      for i in ISEG.keys():
         if len(ISEG[i]) != 2:
            print '... You have a boundary node surounded with more than two boundary segments: ',i
            sys.exit()
         parts = ISEG[i].keys()
         ISEG[i] = { parts[0]:ISEG[i][parts[1]], parts[1]:ISEG[i][parts[0]] }

      # ~~> CONLIM file: Preliminary set up of NPTIR for all parts
      NPTIR = dict([ (i,{}) for i in range(self.NPARTS) ])
      for part in range(self.NPARTS):
         for p in self.PINTER[part]: NPTIR[part].update( dict([ (i,[]) for i in p ]) )
      parts = range(self.NPARTS)
      while parts != []:
         part = parts[0]
         parts.pop(0)
         for ip in NPTIR[part].keys():
            for ipart in parts:
               if ip in NPTIR[ipart].keys():
                  NPTIR[part][ip].append(ipart)
                  NPTIR[ipart][ip].append(part)

      print '... Split of the SELAFIN file'
      for part in range(self.NPARTS):
         fmti = '00000' + str(part)
         fmti = fmti[len(fmti)-5:]
         print '    +> part ',part+1,' of ',self.NPARTS

         self.slfn.IKLE2 = LIKLE[part]
         self.slfn.NELEM2 = len(LIKLE[part])
         self.slfn.NPOIN2 = len(KNOLG[part])
         # ~~> IPARAM has two new values: 8:NPTFR and 9:NPTIR
         self.slfn.IPARAM[7] = len(np.unique(np.concatenate(polyFILTER[part])))
         self.slfn.IPARAM[8] = len(NPTIR[part])
         # ~~> IPOBO (or IRAND) converted into KNOLG[part]
         self.slfn.IPOBO = KNOLG[part]+1

         print '       ~> filtering the MESH'
         # ~~> GEO file: MESH coordinates
         self.slfn.MESHX = np.zeros(self.slfn.NPOIN2,dtype=np.float32)
         self.slfn.MESHY = np.zeros(self.slfn.NPOIN2,dtype=np.float32)
         self.slfn.MESHX = self.slf.MESHX[KNOLG[part]]
         self.slfn.MESHY = self.slf.MESHY[KNOLG[part]]

         # ~~> GEO file: File names
         fileRoot,fileExts = path.splitext(self.slf.fileName)
         self.slfn.fileName = fileRoot+fmtn+'-'+fmti+fileExts

         # ~~> GEO file: Printing
         print '       ~> printing: ',self.slfn.fileName
         self.slfn.fole = open(self.slfn.fileName,'wb')
         self.slfn.appendHeaderSLF()
         LVARSOR = np.zeros((self.slfn.NVAR,self.slfn.NPOIN2),dtype=np.float32)
         for t in range(len(self.slf.tags['times'])):
            self.slfn.appendCoreTimeSLF(t)
            VARSOR = self.slf.getVALUES(t)
            for v in range(self.slfn.NVAR): LVARSOR[v] = VARSOR[v][KNOLG[part]]
            self.slfn.appendCoreVarsSLF(LVARSOR)
         self.slfn.fole.close()

      if not self.isCONLIM: return

      print '\n... Connect elements across internal boundaries (IFAPAR)'
      for part in range(self.NPARTS):
         print '    +> part ',part+1,' of ',self.NPARTS
         # ~~> CONLIM file: Preliminary set up of PEHALO elements accross internal boundaries
         PEHALO = {}; SEHALO = {}
         #   Step 1: find out about the primary elements and loop through IKLE
         self.NSPLIT *= 0
         MASKER = NPTIR[part].keys()
         self.NSPLIT[MASKER] += 1

         print '       ~> Assembling primary elements with other side'
         # Sub Step 1: Assembling all edges from the other sides
         maxbar = 0; ibar = 0
         for ip in range(self.NPARTS): maxbar += len(LIKLE[ip])
         pbar = ProgressBar(maxval=maxbar).start()
         for otherpart in range(self.NPARTS):
            if otherpart == part: continue        # all parts are still positive at this stage
            for k in range(len(LIKLE[otherpart])):
               ibar += 1
               e = self.slf.IKLE[KELLG[otherpart][k]]
               if np.count_nonzero( self.NSPLIT[e] ) < 2: continue
               for p1,p2 in zip([1,2,0],[0,1,2]):    # reverse order because looking from the other side
                  if self.NSPLIT[e[p1]] > 0 and self.NSPLIT[e[p2]] > 0:
                     if not PEHALO.has_key((e[p1],e[p2])): PEHALO.update({ (e[p1],e[p2]):[0,[]] })
                     PEHALO[(e[p1],e[p2])][1].append(k)
                     PEHALO[(e[p1],e[p2])][1].append(otherpart)
               pbar.update(ibar)
         # Sub Step 2: Assembling all edges from the primary side (there are three times more of them)
         for k in range(len(LIKLE[part])):
            ibar += 1
            j = KELLG[part][k]
            e = self.slf.IKLE[j]
            if np.count_nonzero( self.NSPLIT[e] ) < 2: continue
            for p1,p2,p3 in zip([0,1,2],[1,2,0],[2,0,1]):
               if self.NSPLIT[e[p1]] > 0 and self.NSPLIT[e[p2]] > 0:
                  if PEHALO.has_key((e[p1],e[p2])):  # the good side opposes the dark side
                     PEHALO[(e[p1],e[p2])][0] = k
                     if self.NSPLIT[e[p3]] == 0: self.NSPLIT[e[p3]] = -1
                     if self.NSPLIT[e[p3]] == -1:
                        if not SEHALO.has_key((e[p1],e[p3])): SEHALO.update({ (e[p1],e[p3]):[] })
                        SEHALO[(e[p1],e[p3])].append(k)
                        if not SEHALO.has_key((e[p2],e[p3])): SEHALO.update({ (e[p2],e[p3]):[] })
                        SEHALO[(e[p2],e[p3])].append(k)
                     else: # self.NSPLIT[e[p3]] must be 2 !
                        if not SEHALO.has_key((e[p3],e[p1])): SEHALO.update({ (e[p3],e[p1]):[] })
                        if k not in SEHALO[(e[p3],e[p1])]: SEHALO[(e[p3],e[p1])].append(k)
                        if not SEHALO.has_key((e[p2],e[p3])): SEHALO.update({ (e[p2],e[p3]):[] })
                        if k not in SEHALO[(e[p2],e[p3])]: SEHALO[(e[p2],e[p3])].append(k)
                     if self.KSPLIT[j] >= 0: self.KSPLIT[j] = -(self.KSPLIT[j]+1)     # /!\ This is very dangerous but necessary
            pbar.update(ibar)
         pbar.finish()
         # Sub Step 3: Final clean up of the other side ? no need but check later for (ei)[0] == 0
         #   Step 2: find out about the secondary elements on IKLE ( local LIKLE ? )
         print '       ~> Assembling secondary elements of that side'
         pbar = ProgressBar(maxval=len(LIKLE[part])).start()
         for k in range(len(LIKLE[part])):
            j = KELLG[part][k]
            e = self.slf.IKLE[j]
            if self.KSPLIT[j] != part: continue
            if np.count_nonzero( self.NSPLIT[e] ) < 2: continue
            for i in [0,1,2]:
               ii = (i+1)%3
               if self.NSPLIT[e[i]] > 0 and self.NSPLIT[e[ii]] < 0 and SEHALO.has_key((e[i],e[ii])): SEHALO[(e[i],e[ii])].append(k) # correct orientation
               if self.NSPLIT[e[i]] > 0 and self.NSPLIT[e[ii]] > 0 and SEHALO.has_key((e[ii],e[i])): SEHALO[(e[ii],e[i])].append(k) # opposite orientation
               ii = (i+2)%3
               if self.NSPLIT[e[i]] > 0 and self.NSPLIT[e[ii]] < 0 and SEHALO.has_key((e[i],e[ii])): SEHALO[(e[i],e[ii])].append(k) # correct orientation
               if self.NSPLIT[e[i]] > 0 and self.NSPLIT[e[ii]] > 0 and SEHALO.has_key((e[i],e[ii])): SEHALO[(e[i],e[ii])].append(k) # opposite orientation
            if self.KSPLIT[j] < 0: self.KSPLIT[j] = -self.KSPLIT[j] - 1    # /!\ back to a safe place
            pbar.update(k)
         pbar.finish()
         #   Step 3: finally cross reference information between SEHALO and PEHALO
         print '       ~> Combining sides surrounding the halo-elements'
         for ie in PEHALO.keys():
            if PEHALO[ie][0] == 0: continue
            k = PEHALO[ie][0]      # element number in its local part numbering
            if not IFAPAR[part].has_key(k): IFAPAR[part].update({ k:[-2,-1,-2,-1,-2,-1] })
            j = KELLG[part][k]
            e = self.slf.IKLE[j]
            for p1,p2 in zip([0,1,2],[1,2,0]):
               if SEHALO.has_key((e[p1],e[p2])):
                  if len(SEHALO[(e[p1],e[p2])]) > 1:
                     if SEHALO[(e[p1],e[p2])][0] == k: IFAPAR[part][k][2*p1] = SEHALO[(e[p1],e[p2])][1]
                     if SEHALO[(e[p1],e[p2])][1] == k: IFAPAR[part][k][2*p1] = SEHALO[(e[p1],e[p2])][0]
                     IFAPAR[part][k][1+2*p1] = part
               if SEHALO.has_key((e[p2],e[p1])):
                  if len(SEHALO[(e[p2],e[p1])]) > 1:
                     if SEHALO[(e[p2],e[p1])][0] == k: IFAPAR[part][k][2*p1] = SEHALO[(e[p2],e[p1])][1]
                     if SEHALO[(e[p2],e[p1])][1] == k: IFAPAR[part][k][2*p1] = SEHALO[(e[p2],e[p1])][0]
                     IFAPAR[part][k][1+2*p1] = part
               if ie == (e[p1],e[p2]):
                  IFAPAR[part][k][2*p1] = PEHALO[ie][1][0]
                  IFAPAR[part][k][1+2*p1] = PEHALO[ie][1][1]

      # ~~> CONLIM file: Write to file ... pfuuuuuh ... this is it !
      print '\n... Split of the CONLIM files'
      for part in range(self.NPARTS):
         fmti = '00000' + str(part)
         fmti = fmti[len(fmti)-5:]

         print '    +> part: ',part+1,' of ',self.NPARTS
         # ~~> CONLIM file: Set the filter
         INDEX = np.zeros_like(self.clm.INDEX,dtype=np.int)
         for contour in polyFILTER[part]:
            # ~~> Closed contour: no need to change ISEG
            if contour[0] == contour[len(contour)-1]:
               for c in contour[1:]: INDEX[self.clm.KFRGL[c]] = self.clm.KFRGL[c]+1
            # ~~> Open contour: need to change ISEG with neighbours
            else:
               for c in contour[0:]: INDEX[self.clm.KFRGL[c]] = self.clm.KFRGL[c]+1
               iA = self.clm.KFRGL[contour[0]]
               self.clm.POR['is'][iA] = ISEG[contour[0]][part]
               self.clm.POR['xs'][iA] = self.slf.MESHX[abs(ISEG[contour[0]][part])-1]  # /!\ MESHX start at 0
               self.clm.POR['ys'][iA] = self.slf.MESHY[abs(ISEG[contour[0]][part])-1]  # /!\ MESHY start at 0
               iA = self.clm.KFRGL[contour[len(contour)-1]]
               self.clm.POR['is'][iA] = ISEG[contour[len(contour)-1]][part]
               self.clm.POR['xs'][iA] = self.slf.MESHX[abs(ISEG[contour[len(contour)-1]][part])-1]
               self.clm.POR['ys'][iA] = self.slf.MESHY[abs(ISEG[contour[len(contour)-1]][part])-1]
         self.clm.INDEX = INDEX

         # ~~> CONLIM file: Set the NPTIR and CUTs
         self.clm.NPTIR = NPTIR[part]

         # ~~> CONLIM file: Set the IFAPAR
         self.clm.IFAPAR = IFAPAR[part]

         # ~~> CONLIM file
         fileRoot,fileExts = path.splitext(self.clm.fileName)
         print '       ~> printing: ',fileRoot+fmtn+'-'+fmti+fileExts
         self.clm.putContent(fileRoot+fmtn+'-'+fmti+fileExts)

      return

# _____                        _____________________________________
# ____/ Primary METIS Classes /____________________________________/
#
class Graph():

   # Graph size constants
   nvtxs     = -1
   nedges    = -1
   ncon      = -1
   mincut    = -1
   minvol    = -1
   nbnd      = -1

   # Memory for the graph structure
   xadj      = None # = imalloc(snvtxs+1, "SetupSplitGraph: xadj");
   vwgt      = None # = imalloc(sgraph->ncon*snvtxs, "SetupSplitGraph: vwgt");
   adjncy    = None # = imalloc(snedges,  "SetupSplitGraph: adjncy");
   adjwgt    = None # = imalloc(snedges,  "SetupSplitGraph: adjwgt");
   label     = None # = imalloc(snvtxs,   "SetupSplitGraph: label");
   cmap      = None
   tvwgt     = None # = imalloc(sgraph->ncon, "SetupSplitGraph: tvwgt");
   invtvwgt  = None # = rmalloc(sgraph->ncon, "SetupSplitGraph: invtvwgt");

   # By default these are set to true, but the can be explicitly changed afterwards
   free_xadj   = 1
   free_vwgt   = 1
   free_vsize  = 1
   free_adjncy = 1
   free_adjwgt = 1

   # Memory for the partition/refinement structure
   where     = None
   pwgts     = None
   id        = None
   ed        = None
   bndptr    = None
   bndind    = None
   nrinfo    = None
   ckrinfo   = None
   vkrinfo   = None

   # Linked-list structure
   coarser   = None
   finer     = None

"""
"Usage: mpmetis [options] meshfile nparts",
" ",
" Required parameters",
"    meshfile    Stores the mesh to be partitioned.",
"    nparts      The number of partitions to split the mesh.",
" ",
" Optional parameters",
"  -gtype=string",
"     Specifies the graph to be used for computing the partitioning",
"     The possible values are:",
"        dual     - Partition the dual graph of the mesh [default]",
"        nodal    - Partition the nodal graph of the mesh",
" ",
"  -ptype=string",
"     Specifies the scheme to be used for computing the k-way partitioning.",
"     The possible values are:",
"        rb       - Recursive bisectioning",
"        kway     - Direct k-way partitioning [default]",
" ",
"  -ctype=string",
"     Specifies the scheme to be used to match the vertices of the graph",
"     during the coarsening.",
"     The possible values are:",
"        rm       - Random matching",
"        shem     - Sorted heavy-edge matching [default]",
" ",
"  -iptype=string [applies only when -ptype=rb]",
"     Specifies the scheme to be used to compute the initial partitioning",
"     of the graph.",
"     The possible values are:",
"        grow     - Grow a bisection using a greedy strategy [default]",
"        random   - Compute a bisection at random",
" ",
"  -objtype=string [applies only when -ptype=kway]",
"     Specifies the objective that the partitioning routines will optimize.",
"     The possible values are:",
"        cut      - Minimize the edgecut [default]",
"        vol      - Minimize the total communication volume",
" ",
"  -contig [applies only when -ptype=kway]",
"     Specifies that the partitioning routines should try to produce",
"     partitions that are contiguous. Note that if the input graph is not",
"     connected this option is ignored.",
" ",
"  -minconn [applies only when -ptype=kway]",
"     Specifies that the partitioning routines should try to minimize the",
"     maximum degree of the subdomain graph, i.e., the graph in which each",
"     partition is a node, and edges connect subdomains with a shared",
"     interface.",
" ",
"  -tpwgts=filename",
"     Specifies the name of the file that stores the target weights for",
"     each partition. By default, all partitions are assumed to be of ",
"     the same size.",
" ",
"  -ufactor=int",
"     Specifies the maximum allowed load imbalance among the partitions.",
"     A value of x indicates that the allowed load imbalance is 1+x/1000.",
"     For ptype=rb, the load imbalance is measured as the ratio of the ",
"     2*max(left,right)/(left+right), where left and right are the sizes",
"     of the respective partitions at each bisection. ",
"     For ptype=kway, the load imbalance is measured as the ratio of ",
"     max_i(pwgts[i])/avgpwgt, where pwgts[i] is the weight of the ith",
"     partition and avgpwgt is the sum of the total vertex weights divided",
"     by the number of partitions requested.",
"     For ptype=rb, the default value is 1 (i.e., load imbalance of 1.001).",
"     For ptype=kway, the default value is 30 (i.e., load imbalance of 1.03).",
" ",
"  -ncommon=int",
"     Specifies the common number of nodes that two elements must have",
"     in order to put an edge between them in the dual graph. Default is 1.",
" ",
"  -niter=int",
"     Specifies the number of iterations for the refinement algorithms",
"     at each stage of the uncoarsening process. Default is 10.",
" ",
"  -ncuts=int",
"     Specifies the number of different partitionings that it will compute.",
"     The final partitioning is the one that achieves the best edgecut or",
"     communication volume. Default is 1.",
" ",
"  -nooutput",
"     Specifies that no partitioning file should be generated.",
" ",
"  -seed=int",
"     Selects the seed of the random number generator.  ",
" ",
"  -dbglvl=int      ",
"     Selects the dbglvl.  ",
" ",
"  -help",
"     Prints this message.",
""
"""
# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$29-Feb-2012 08:51:29$"

if __name__ == "__main__":

   PWD = getcwd()
   partelName = path.join(PWD,'PARTEL.PAR')
   if not path.exists(partelName):
      print '... could not find the PARTEL.PAR file in ',PWD
      sys.exit()
   files = getFileContent(partelName)
   fileSLF = path.join(PWD,files[0].strip())
   if not path.exists(fileSLF):
      print '... could not find the file ',fileSLF,' in ',PWD
      sys.exit()
   fileCLM = path.join(PWD,files[1].strip())
   if not path.exists(fileCLM):
      print '... could not find the file ',fileCLM,' in ',PWD
      sys.exit()
   fileSEQ = path.join(PWD,'RESULT_SEQ_METIS')
   if not path.exists(fileSEQ): fileSEQ = ''
   splitCONLIM = False
   if len(files) > 5: splitCONLIM = ( int(files[5].strip()) == 1 )
   writeDOMAIN = ''
   if len(files) > 6:
      if int(files[6].strip()) == 1: writeDOMAIN = 'T2DBND'
   slfs = splitSELAFIN( fileSLF,fileCLM,fileSEQ,splitCONLIM=splitCONLIM,DOMfileRoot=writeDOMAIN )
   slfs.putContent()

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit()
