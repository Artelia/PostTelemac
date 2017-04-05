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
"""@history 30/08/2014 -- Sebastien E. Bourban
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
from optparse import Values
import numpy as np
# ~~> dependencies towards other pytel/modules
from parsers.parserStrings import parseArrayFrame,parseArrayPoint,parseArrayGrid
from parsers.parserCSV import CSV
from parsers.parserSortie import Sortie
from parsers.parserSELAFIN import SELAFIN,getValueHistorySLF,getValuePolylineSLF,subsetVariablesSLF,getValuePolyplanSLF
from samplers.meshes import xysLocateMesh,sliceMesh


# _____                  ___________________________________________
# ____/ General Toolkit /__________________________________________/
#

def getKDTree(MESHX,MESHY,IKLE):
   from scipy.spatial import cKDTree
   isoxy = np.column_stack((np.sum(MESHX[IKLE],axis=1)/3.0,np.sum(MESHY[IKLE],axis=1)/3.0))
   return cKDTree(isoxy)

def getMPLTri(MESHX,MESHY,IKLE):
   from matplotlib.tri import Triangulation
   mpltri = Triangulation(MESHX,MESHY,IKLE).get_cpp_triangulation()
   return mpltri.get_neighbors(),mpltri.get_edges()

def whatTimeSLF(instr,ctimes):
   # instr ~ what['time']: list of frames or (times,) delimited by ';'
   # ctimes ~ slf.tags['cores']: list of time
   return parseArrayFrame(instr,len(ctimes))
   # TODO: check that you are not breaking anything
   #t = parseArrayFrame(instr,len(ctimes))
   #if len(t) != 1: print '... the time definition should only have one frame in this case. It is: ',instr,'. I will assume you wish to plot the last frame.'
   #return [ t[len(t)-1] ]

def whatVarsSLF(instr,vnames):
# instr ~ what['vars']: list of pairs "variable:support" delimited by ';'
# vnames ~ slf.VARNAMES: list of variables names from the SELAFIN file
   vars = []; vtypes = []
   for var in instr.split(';'):
      v,vtype = var.split(':')
      vars.append( v ); vtypes.append( vtype )
   return subsetVariablesSLF(';'.join(vars),vnames),vtypes

def whatSample(inspl,box):
   grids = []
   plans = []
   for grid in parseArrayGrid(inspl,box):
      if grid[0][0] == grid[1][0]:
         print '... same min(x)=',grid[0][0],' and max(x)=',grid[1][0],' values in: ',inspl,'. I cannot create a box.'
         continue # TODO: add exception
      if grid[0][1] == grid[1][1]:
         print '... same min(y)=',grid[0][1],' and max(y)=',grid[1][1],' values in: ',inspl,'. I cannot create a box.'
         continue # TODO: add exception
      if len(grid[0]) > 2:
         if grid[0][2] == grid[1][2]:
            print '... same min(z)=',grid[0][2],' and max(z)=',grid[1][2],' values in: ',inspl,'. I cannot create a box.'
            continue # TODO: add exception
         mx,my,mz = np.meshgrid(np.linspace(grid[0][0], grid[1][0], grid[-1][0]+1),np.linspace(grid[0][1], grid[1][1], grid[-1][1]+1),np.linspace(grid[0][2], grid[1][2], grid[-1][2]+1))
         grids.append((len(mx[0][0]),len(mx[0]),len(mx),np.concatenate(mx),np.concatenate(my),np.concatenate(mz)))
      else:
         mx,my = np.meshgrid(np.linspace(grid[0][0], grid[1][0], grid[-1][0]+1),np.linspace(grid[0][1], grid[1][1], grid[-1][1]+1))
         grids.append((len(mx[0]),len(mx),np.concatenate(mx),np.concatenate(my)))
         if len(grid[-1]) == 3: plans = grid[2]
   return grids,plans

def setQuad(grids):
   MESHX = []; MESHY = []
   IKLE = []
   for dimx,dimy,x,y in grids:
      IKLE.extend(([ i+j*dimx,i+1+j*dimx,i+1+(j+1)*dimx,i+(j+1)*dimx ] for j in range(dimy-1) for i in range(dimx-1) ))
      MESHX.extend(x)
      MESHY.extend(y)
   return np.array(IKLE),np.array(MESHX),np.array(MESHY)

def splitQuad2Triangle(IKLE):
   # split each quad into triangles
   return np.delete(np.concatenate((IKLE,np.roll(IKLE,2,axis=1))),np.s_[3::],axis=1)

# _____                        _____________________________________
# ____/ Primary Casts:Extract /____________________________________/
#

class castSELAFIN(SELAFIN): # /!\ does not support PARAFINS yet -- because of the print order of print Core

   # ~~> Standard SELAFIN file
   #def __init__(self,f):
   #   SELAFIN.__init__(self,f)

   def castHistoryAtPoints(self,whatVARS,whatTIME,whatPOINTS):

      # ~~> Extract data
      # whatVARS: list of pairs variables:support delimited by ';' (/!\ support is ignored)
      vars = subsetVariablesSLF(whatVARS,self.VARNAMES)
      # whatTIME: list of frames or (times,) delimited by ';'
      t = parseArrayFrame(whatTIME,len(self.tags['cores']))
      # whatPOINTS: could be list delimited by ';', of:
      #    + points (x;y),
      #    + 2D points (x;y) bundled within (x;y)#n or (x;y)@d#n, delimited by ';'
      #      where n is a plan number and d is depth from that plane (or the surface by default)
      support2d = []; zps = []
      pAP = parseArrayPoint(whatPOINTS,self.NPLAN)
      for xyi,zpi in pAP:
         if type(xyi) == type(()): support2d.append( xysLocateMesh(xyi,self.IKLE2,self.MESHX,self.MESHY,self.tree,self.neighbours) )
         else: support2d.append( xyi )
         zps.append( zpi )
      support3d = zip(support2d,zps)
      # - support2d[i][0] is either the node or the triplet of nodes for each element including (x,y)
      # - support2d[i][1] is the plan or depth definition
      data = getValueHistorySLF(self.file,self.tags,t,support3d,self.NVAR,self.NPOIN3,self.NPLAN,vars)

      # ~~> Draw/Dump data
      return ('Time (s)',self.tags['times'][t]), \
         [('',[n.replace(' ','_').replace(',',';') for n in vars[1]],[(str(n[0])+':'+str(m)).replace(' ','').replace(',',';') for n in pAP for m in n[1]],data)]

   def castProfileAtPolyline(self,whatVARS,whatTIME,whatPOINTS):

      # ~~> Extract data
      # what['vars']: list of pairs variables:support2d delimited by ';'
      vars = subsetVariablesSLF(whatVARS,self.VARNAMES)
      # what['time']: list of frames or (times,) delimited by ';'
      t = parseArrayFrame(whatTIME,len(self.tags['cores']))
      # what['extract']: could be list delimited by ';', of:
      #    + points (x;y),
      #    + 2D points (x;y) bundled within (x;y)#n or (x;y)@d#n, delimited by ';'
      #      where n is a plan number and d is depth from that plane (or the surface by default)
      xyo = []; zpo = []
      for xyi,zpi in parseArrayPoint(whatPOINTS,self.NPLAN):
         if type(xyi) == type(()): xyo.append(xyi)
         else: xyo.append( (self.MESHX[xyi],self.MESHY[xyi]) )
         for p in zpi:                         # /!\ common deinition of plans
            if p not in zpo: zpo.append(p)     # /!\ only allowing plans for now
      xys,support2d = sliceMesh(xyo,self.IKLE2,self.MESHX,self.MESHY,self.tree)
      # - support2d[i][0] is either the douplets of nodes for each edges crossing with the polyline
      # - support2d[i][1] is the plan or depth definition
      support3d = [ (s2d,zpo) for s2d in support2d ]  # common vertical definition to all points
      data = getValuePolylineSLF(self.file,self.tags,t,support3d,self.NVAR,self.NPOIN3,self.NPLAN,vars)
      # Distance d-axis
      distot = 0.0
      d = [ distot ]
      for xy in range(len(xys)-1):
         distot += np.sqrt( np.power(xys[xy+1][0]-xys[xy][0],2) + np.power(xys[xy+1][1]-xys[xy][1],2) )
         d.append(distot)
      # ~~> Draw/Dump data
      return ('Distance (m)',d),[('v-section',vars[1],self.tags['times'][t],zpo,data)]

   def castVMeshAtPolyline(self,whatTIME,whatPOINTS):

      # whatPOINTS: could be list delimited by ';', of:
      #    + points (x;y),
      #    + 2D points (x;y) bundled within (x;y)#n or (x;y)@d#n, delimited by ';'
      #      where n is a plan number and d is depth from that plane (or the surface by default)
      xyo = []; zpo = []
      for xyi,zpi in parseArrayPoint(whatPOINTS,self.NPLAN):
         if xyi == []:
            print '... I could not find anything to extract in "',what["extract"].strip(),'" as support for the cross section.'
            sys.exit(1)
         if type(xyi) == type(()): xyo.append(xyi)
         else: xyo.append( (self.MESHX[xyi],self.MESHY[xyi]) )
         for p in zpi:                         # /!\ common deinition of plans
            if p not in zpo: zpo.append(p)     # /!\ only allowing plans for now

      # ~~> Extract horizontal cross MESHX
      xys,support2d = sliceMesh(xyo,self.IKLE2,self.MESHX,self.MESHY,self.tree)
      support3d = []
      for s2d in support2d: support3d.append( (s2d,zpo) )   # common vertical definition to all points
      # Distance d-axis
      distot = 0.0
      d = [ distot ]
      for xy in range(len(xys)-1):
         distot += np.sqrt( np.power(xys[xy+1][0]-xys[xy][0],2) + np.power(xys[xy+1][1]-xys[xy][1],2) )
         d.append(distot)
      MESHX = np.repeat(d,len(zpo))

      # ~~>  Extract MESHZ for more than one time frame
      varz = subsetVariablesSLF('z',self.VARNAMES)
      t = whatTimeSLF(whatTIME,self.tags['cores'])
      MESHZ = np.ravel( getValuePolylineSLF(self.file,self.tags,t,support3d,self.NVAR,self.NPOIN3,self.NPLAN,varz)[0][0].T )

      # ~~>  Connect with IKLE, keeping quads
      IKLE = []
      for j in range(len(d)-1):
         for i in range(len(zpo)-1):
            IKLE.append([ i+j*len(zpo),i+(j+1)*len(zpo),i+1+(j+1)*len(zpo),i+1+j*len(zpo) ])
      IKLE = np.array(IKLE)

      return IKLE,MESHX,MESHZ, support3d

   def castVMeshAtPolyline_Plane(self,whatTIME,whatPOINTS):

      # whatPOINTS: could be list delimited by ';', of:
      #    + points (x;y),
      #    + 2D points (x;y) bundled within (x;y)#n or (x;y)@d#n, delimited by ';'
      #      where n is a plan number and d is depth from that plane (or the surface by default)
      xyo = []; zpo = []
      for xyi,zpi in parseArrayPoint(whatPOINTS,self.NPLAN):
         if xyi == []:
            print '... I could not find anything to extract in "',what["extract"].strip(),'" as support for the cross section.'
            sys.exit(1)
         if type(xyi) == type(()): xyo.append(xyi)
         else: xyo.append( (self.MESHX[xyi],self.MESHY[xyi]) )
         for p in zpi:                         # /!\ common deinition of plans
            if p not in zpo: zpo.append(p)     # /!\ only allowing plans for now

      # ~~> Extract horizontal cross MESHX
      xys,support2d = sliceMesh(xyo,self.IKLE2,self.MESHX,self.MESHY,self.tree)
      support3d = []
      for s2d in support2d: support3d.append( (s2d,zpo) )   # common vertical definition to all points

      # Distance d-axis
      distot = 0.0
      d = [ distot ]
      for xy in range(len(xys)-1):
         distot += np.sqrt( np.power(xys[xy+1][0]-xys[xy][0],2) + np.power(xys[xy+1][1]-xys[xy][1],2) )
         d.append(distot)

      newx = []
      newy = []
      for xy in range(len(xys)):
        newx.append(xys[xy][0])
        newy.append(xys[xy][1])

      MESHX = np.repeat(newx,len(zpo))
      MESHY = np.repeat(newy,len(zpo))

      # ~~>  Extract MESHZ for more than one time frame
      varz = subsetVariablesSLF('z',self.VARNAMES)
      t = whatTimeSLF(whatTIME,self.tags['cores'])
      MESHZ = np.ravel( getValuePolylineSLF(self.file,self.tags,t,support3d,self.NVAR,self.NPOIN3,self.NPLAN,varz)[0][0].T )

      # ~~>  Connect with IKLE, keeping quads
      IKLE = []
      for j in range(len(d)-1):
         for i in range(len(zpo)-1):
            IKLE.append([ i+j*len(zpo),i+(j+1)*len(zpo),i+1+(j+1)*len(zpo),i+1+j*len(zpo) ])
      IKLE = np.array(IKLE)

      return IKLE,MESHX,MESHY,MESHZ, support3d

   def castHMeshAtLevels(self,whatPOINTS):

      # whatPOINTS: could be list delimited by ';', of:
      #    + empty spatial location [],
      #    + bundled within []#n or []@d#n, delimited by ';'
      #      where n is a plan number and d is depth from that plane (or the surface by default)
      xyo = []; zpo = []
      for xyi,zpi in parseArrayPoint(whatPOINTS,self.NPLAN):
         #if xyi != []:
         #   print '... I will assume that all 2D nodes are considered at this stage.'
         #   sys.exit(1)
         for p in zpi:                         # /!\ common definition of plans
            if p not in zpo: zpo.append(p)     # /!\ only allowing plans for now

      return self.IKLE2,self.MESHX,self.MESHY, zpo

   def castVMeshAtLevels(self,whatTIME,whatPOINTS):

      t = whatTimeSLF(whatTIME,self.tags['cores'])
      zpo = self.castHMeshAtLevels(whatPOINTS)[3]
      # whatVARS: is set here for Z
      vars = []
      for vname in self.VARNAMES:
         if 'ELEVATION' in vname: vars = subsetVariablesSLF('ELEVATION',self.VARNAMES)
         if 'COTE Z' in vname: vars = subsetVariablesSLF('COTE Z',self.VARNAMES)
         if 'WATER DEPTH' in vname: vars = subsetVariablesSLF('WATER DEPTH',self.VARNAMES)
         if 'HAUTEUR D\'EAU' in vname: vars = subsetVariablesSLF('HAUTEUR D\'EAU',self.VARNAMES)
         if 'FREE SURFACE' in vname: vars = subsetVariablesSLF('FREE SURFACE',self.VARNAMES)
         if 'SURFACE LIBRE' in vname: vars = subsetVariablesSLF('SURFACE LIBRE',self.VARNAMES)
      if vars == []:
         print '... Could not find [\'ELEVATION\'] or [\'COTE Z\'] in ',self.VARNAMES
         print '   +> Your file may not be a 3D file (?)'
         sys.exit(1)
      return self.IKLE3,self.MESHX,self.MESHY,getValuePolyplanSLF(self.file,self.tags,t,zpo,self.NVAR,self.NPOIN3,self.NPLAN,vars)[0][0]

   def castHValueAtLevels(self,whatVARS,whatTIME,whatPOINTS):

      t = whatTimeSLF(whatTIME,self.tags['cores'])
      # whatVARS: list of pairs variables:support2d delimited by ';'
      vars = subsetVariablesSLF(whatVARS,self.VARNAMES)
      # whatPOINTS: could be list delimited by ';', of:
      #    + points (x;y),
      #    + 2D points (x;y) bundled within (x;y)#n or (x;y)@d#n, delimited by ';'
      #      where n is a plan number and d is depth from that plane (or the surface by default)
      xyo = []; zpo = []
      for xyi,zpi in parseArrayPoint(whatPOINTS,self.NPLAN):
         if xyi == [] or type(xyi) == type(()): xyo.append(xyi)
         else: xyo.append( (self.MESHX[xyi],self.MESHY[xyi]) )
         for p in zpi:                         # /!\ common deinition of plans
            if p not in zpo: zpo.append(p)     # /!\ only allowing plans for now
      if len(zpo) != 1: print '... the vertical definition should only have one plan in this case. It is: ',whatPOINTS,'. I will assume you wish to plot the higher plane.'
      # could be more than one variables including v, but only one time frame t and one plan
      data = getValuePolyplanSLF(self.file,self.tags,t,zpo,self.NVAR,self.NPOIN3,self.NPLAN,vars)
      VARSORS = []
      for ivar in range(len(data)): VARSORS.append( data[ivar][0][0] ) # TODO: give me more time

      return VARSORS

   def castValues(self,whatVARS,whatTIME):

      ftype,fsize = self.file['float']
      # /!\ For the moment, only one frame at a time
      ts = whatTimeSLF(whatTIME,self.tags['cores'])
      # whatVARS: list of pairs variables:support2d delimited by ';'
      varsIndexes,varsName = subsetVariablesSLF(whatVARS,self.VARNAMES)
      if fsize == 4: VARSORS = np.zeros((len(ts),len(varsIndexes),self.NPOIN3),dtype=np.float32)
      else: VARSORS = np.zeros((len(ts),len(varsIndexes),self.NPOIN3),dtype=np.float64)
      for it in range(len(ts)): VARSORS[it] = self.getVariablesAt( ts[it],varsIndexes )
      return VARSORS

# _____                         ____________________________________
# ____/ Primary Classes:Cast /___________________________________/
#

class Caster:

   def __init__(self, caster={'object':{},'obdata':{}}):
      self.object = caster['object']  # refered to by file names
      self.obdata = caster['obdata']  # refered to data extracted in layers

   def add(self,typl,what):
      # ~~> cast already prepared becasue .add is always called
      if typl == '': return
      # ~~> bundling of the layers becasue .add is always called
      if what["xref"] not in self.obdata.keys():
         obdata = Values()
         obdata.type = ''
         obdata.unit = []
         obdata.support = []
         obdata.function = []
         obdata.values = []
         self.obdata.update({ what["xref"]:obdata })
      # ~~> file references
      if what['file'] in self.object.keys(): return
      # ~~> unexplored teritory
      if 'sortie' in typl.lower():
         self.object.update({ what['file']:Sortie(what['file']) })
      elif 'csv' in typl.lower():
         self.object.update({ what['file']:CSV(what['file']) })
      elif 'tif' in typl.lower() or 'jpg' in typl.lower()  \
        or 'gif' in typl.lower() or 'png' in typl.lower()   \
        or 'bmp' in typl.lower():
         self.object.update({ what['file']:'image' })
      # ~~> SELAFIN file
      elif 'SELAFIN' in typl.upper() or 'slf' in typl.lower():
         slf = castSELAFIN(what['file'])
         slf.setKDTree()
         slf.setMPLTri()
         self.object.update({ what['file']:slf })
      else: # TODO: raise exception
         print '... do not know how to extract from this format: ' + typl
         sys.exit(1)

   def set(self,vref,cast):
      if vref in self.obdata.keys():
         print '... cast reference already used: ' + vref
         sys.exit(1)
      self.obdata.update({ vref:cast })

   def get(self,typl,what):
      if typl == '':
         if what['file'] in self.obdata.keys(): return self.obdata[what['file']]
         print '... I did not cast the following reference: ' + what['file']
         sys.exit(1)
      if what['file'] not in self.object: # TODO: raise exception
         print '... the cast does not include reference to your file : ' + what['file']
         sys.exit(1)
      if what['type'][0:2].lower() == '1d': return self.get1D(typl,what)
      elif what['type'][0:2].lower() == '2d': return self.get2D(typl,what)
      elif what['type'][0:2].lower() == '3d': return self.get3D(typl,what)
      else: # TODO: raise exception
         print '... do not know how to extract from this key: ' + what['type'][0:2]
         sys.exit(1)

   def get1D(self,typl,what):
      obj = self.object[what['file']]
      if 'sortie' in typl.lower():
         # what['vars']: list of pairs variables:support delimited by ';'
         #title = obj.parseNameOfStudy()
         time,values = obj.getValueHistorySortie(what["vars"])
         self.obdata[what["xref"]] = Values({'type':what['type'],
               'unit':time[0], 'support':time[1],
               'function':values[0][0:-1], 'values':values[0][-1] })
      elif 'csv' in typl.lower():
         # what['vars']: list of pairs variables:support delimited by ';'
         dist,values = obj.getColumns(what["vars"])
         self.obdata[what["xref"]] = Values({'type':what['type'],
               'unit':dist[0], 'support':dist[1],
               'function':values[0][0:-1], 'values':values[0][-1] })
      # ~~> SELAFIN file
      elif 'SELAFIN' in typl.upper() or 'slf' in typl.lower():
         # ~~> 1D time history from 2D or 3D results
         if what['type'].split(':')[1] == 'history':
            time,values = obj.castHistoryAtPoints(what["vars"],what["time"],what["extract"])
            self.obdata[what["xref"]] = Values({'type':what['type'],
               'unit':time[0], 'support':time[1],
               'function':values[0][0:-1], 'values':values[0][-1] })
         # ~~> 1D spatial profiles from 2D or 3D results
         elif what['type'].split(':')[1] == 'v-section':
            dist,values = obj.castProfileAtPolyline(what["vars"],what["time"],what["extract"])
            self.obdata[what["xref"]] = Values({'type':what['type'],
               'unit':dist[0], 'support':dist[1],
               'function':values[0][0:-1], 'values':values[0][-1] })
            # values[0][-1] is of the shape:
            #  [ [ [ [x0,x1,.]p0,[x0,x1,.]p1,. ]t0, [ [x0,x1,.]p0,[x0,x1,.]p1,. ]t1,. ]v0,
            #    [ [ [x0,x1,.]p0,[x0,x1,.]p1,. ]t0, [ [x0,x1,.]p0,[x0,x1,.]p1,. ]t1,. ]v1,
            #    ... ]
         else:
            print '... do not know how to draw this SELAFIN type: ' + what['type']
            sys.exit(1)
      else: # TODO: raise exception
         print '... do not know how to extract from this format: ' + what['type']
         sys.exit(1)
      return self.obdata[what["xref"]]

   def get2D(self,typl,what):
      obj = self.object[what['file']]

      # /!\ WACLEO: Temporary fix because TOMAWAC's IOs names are not yet standard TELEMAC
      if 'WACLEO' in typl.upper() or \
         'SELAFIN' in typl.upper() or \
         'slf' in typl.lower():
         ftype,fsize = obj.file['float']

         if what['type'].split(':')[1] == 'v-section':

            # ~~> Extract data
            IKLE4,MESHX,MESHZ, support3d = obj.castVMeshAtPolyline(what["time"],what["extract"])
            # split each quad into triangles
            IKLE3 = splitQuad2Triangle(IKLE4)
            vars,vtypes = whatVarsSLF(what['vars'],obj.VARNAMES)
            time = whatTimeSLF(what['time'],obj.tags['cores'])
            tree = getKDTree(MESHX,MESHZ,IKLE3)
            tria = getMPLTri(MESHX,MESHZ,IKLE3)[0]
            data = getValuePolylineSLF(obj.file,obj.tags,time,support3d,obj.NVAR,obj.NPOIN3,obj.NPLAN,vars)

            # ~~> Possible sampling of the data
            if what["sample"] != '':
               supMESHX = MESHX; supMESHZ = MESHZ
               MESHX = []; MESHZ = []
               IKLE4 = []; support2d = []
               grids,n = whatSample(what["sample"],[(min(supMESHX),min(supMESHZ)),(max(supMESHX),max(supMESHZ))])
               for dimx,dimy,x,y in grids:
                  for xyi in np.dstack((x,y))[0]:
                     support2d.append( xysLocateMesh(xyi,IKLE3,supMESHX,supMESHZ,tree,tria) )
                  IKLE4.extend(([ i+j*dimx,i+1+j*dimx,i+1+(j+1)*dimx,i+(j+1)*dimx ] for j in range(dimy-1) for i in range(dimx-1) ))
                  MESHX.extend(x)
                  MESHZ.extend(y)
               IKLE4 = np.asarray(IKLE4)
               IKLE3 = splitQuad2Triangle(IKLE4)
               MESHX = np.asarray(MESHX)
               MESHZ = np.asarray(MESHZ)

            # ~~> Loop on variables
            for v,vtype in zip(vars,vtypes):

               VARSORS = []
               for ivar in range(len(vars[0])): VARSORS.append( np.ravel(data[ivar][0].T) )

               # ~~> Re-sampling
               if what["sample"] != '':
                  if fsize == 4: data = np.zeros((len(vars[0]),len(support2d)),dtype=np.float32)
                  else: data = np.zeros((len(vars[0]),len(support2d)),dtype=np.float64)
                  for ivar in range(len(vars[0])):
                     for ipt in range(len(support2d)):
                        ln,bn = support2d[ipt]
                        data[ivar][ipt] = 0.0
                        for inod in range(len(bn)):                  # /!\ node could be outside domain
                           if ln[inod] >=0: data[ivar][ipt] += bn[inod]*VARSORS[ivar][ln[inod]]
                  VARSORS = data

               # ~~> Draw/Dump (multiple options possible)
               if "wire" in vtype or "grid" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE4],MESHZ[IKLE4])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE4],MESHZ[IKLE4]))
               if "mesh" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE3],MESHZ[IKLE3])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE3],MESHZ[IKLE3]))
               if "map" in vtype or "label" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHZ,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHZ,IKLE3),VARSORS
               if "arrow" in vtype or "vector" in vtype or "angle" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHZ,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHZ,IKLE3),VARSORS

         elif what['type'].split(':')[1] == 'p-section':

            # ~~> Extract data
            IKLE3,MESHX,MESHY, zpo = obj.castHMeshAtLevels(what['extract'])
            if obj.NDP2 == 4: IKLE3 = splitQuad2Triangle(IKLE3)
            IKLE4 = IKLE3
            vars,vtypes = whatVarsSLF(what['vars'],obj.VARNAMES)
            tree = obj.tree
            tria = obj.neighbours

            # ~~> Possible re-sampling
            support2d = []
            if what["sample"] != '':
               supMESHX = MESHX; supMESHY = MESHY
               MESHX = []; MESHY = []
               IKLE4 = []; support2d = []
               grids,n = whatSample(what["sample"],[(min(supMESHX),min(supMESHY)),(max(supMESHX),max(supMESHY))])
               for dimx,dimy,x,y in grids:
                  for xyi in np.dstack((x,y))[0]:
                     support2d.append( xysLocateMesh(xyi,IKLE3,supMESHX,supMESHY,tree,tria) )
                  IKLE4.extend(([ i+j*dimx,i+1+j*dimx,i+1+(j+1)*dimx,i+(j+1)*dimx ] for j in range(dimy-1) for i in range(dimx-1) ))
                  MESHX.extend(x)
                  MESHY.extend(y)
               IKLE4 = np.asarray(IKLE4)
               IKLE3 = splitQuad2Triangle(IKLE4)
               MESHX = np.asarray(MESHX)
               MESHY = np.asarray(MESHY)

            # ~~> Loop on variables
            for var in what["vars"].split(';'):
               v,vtype = var.split(':')

               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Extract variable data for only one time frame and one plane
               VARSORS = obj.castHValueAtLevels(v,what['time'],what['extract'])
               # ~~> Re-sampling
               if support2d != []:
                  if fsize == 4: data = np.zeros((len(vars[0]),len(support2d)),dtype=np.float32)
                  else: data = np.zeros((len(vars[0]),len(support2d)),dtype=np.float64)
                  for ivar in range(len(vars[0])):
                     for ipt in range(len(support2d)):
                        ln,bn = support2d[ipt]
                        data[ivar][ipt] = 0.0
                        for inod in range(len(bn)):                  # /!\ node could be outside domain
                           if ln[inod] >=0: data[ivar][ipt] += bn[inod]*VARSORS[ivar][ln[inod]]
                  VARSORS = data
               # ~~> Draw/Dump (multiple options possible)
               if "wire" in vtype or "grid" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE4],MESHY[IKLE4])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE4],MESHY[IKLE4]))
               if "mesh" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE3],MESHY[IKLE3])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE3],MESHY[IKLE3]))
               if "map" in vtype or "label" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHY,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,IKLE3),VARSORS
               elif "arrow" in vtype or "vector" in vtype or "angle" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHY,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,IKLE3),VARSORS
               else: print '... do not know how to draw this SELAFIN type: ' + vtype

         elif what['type'].split(':')[1] == '':

            # ~~> Extract data
            IKLE3 = obj.IKLE3
            MESHX = obj.MESHX
            MESHY = obj.MESHY
            if obj.NDP2 == 4: IKLE3 = splitQuad2Triangle(IKLE3)
            IKLE4 = IKLE3
            vars,vtypes = whatVarsSLF(what['vars'],obj.VARNAMES)
            tree = obj.tree
            tria = obj.neighbours

            # ~~> Possible re-sampling
            support2d = []
            if what["sample"] != '':
               supMESHX = MESHX; supMESHY = MESHY
               MESHX = []; MESHY = []
               IKLE4 = []; support2d = []
               grids,n = whatSample(what["sample"],[(min(supMESHX),min(supMESHY)),(max(supMESHX),max(supMESHY))])
               for dimx,dimy,x,y in grids:
                  for xyi in np.dstack((x,y))[0]:
                     support2d.append( xysLocateMesh(xyi,IKLE3,supMESHX,supMESHY,tree,tria) )
                  IKLE4.extend(([ i+j*dimx,i+1+j*dimx,i+1+(j+1)*dimx,i+(j+1)*dimx ] for j in range(dimy-1) for i in range(dimx-1) ))
                  MESHX.extend(x)
                  MESHY.extend(y)
               IKLE4 = np.asarray(IKLE4)
               IKLE3 = splitQuad2Triangle(IKLE4)
               MESHX = np.asarray(MESHX)
               MESHY = np.asarray(MESHY)

            # ~~> Loop on variables
            varNames = []
            for var in what["vars"].split(';'):
               v,vtype = var.split(':')
               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Extract variable data for only one plane
               VARSORS = obj.castValues(v,what['time'])
               # Get value of the timestep
               time = obj.tags['times'][whatTimeSLF(what['time'],obj.tags['cores'])]
               if v == '':
                  varNames = obj.VARNAMES
               else:
                  varNames.append(v)
               # ~~> Re-sampling
               if support2d != []:
                  if fsize == 4: data = np.zeros(VARSORS.shape,dtype=np.float32)
                  else: data = np.zeros(VARSORS.shape,dtype=np.float64)
                  for itime in range(len(VARSORS)):
                     for ivar in range(len(vars[0])):
                        for ipt in range(len(support2d)):
                           ln,bn = support2d[ipt]
                           for inod in range(len(bn)):                  # /!\ node could be outside domain
                              if ln[inod] >=0: data[itime][ivar][ipt] += bn[inod]*VARSORS[itime][ivar][ln[inod]]
                  VARSORS = data
               # ~~> Draw/Dump (multiple options possible)
               if "wire" in vtype or "grid" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE4],MESHY[IKLE4])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE4],MESHY[IKLE4]))
               if "mesh" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE3],MESHY[IKLE3])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE3],MESHY[IKLE3]))
               if "map" in vtype or "label" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHY,IKLE3),
                     'function':'none', 'values':VARSORS,'names':varNames,
                     'time':time})
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,IKLE3),VARSORS
               elif "arrow" in vtype or "vector" in vtype or "angle" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHY,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,IKLE3),VARSORS
               else: print '... do not know how to draw this SELAFIN type: ' + vtype
          

         # ~~> unkonwn
         else: # TODO: raise exception
            print '... do not know how to do this type of extraction: ' + what['type'].split(':')[1]

      # ~~> unkonwn
      else: # TODO: raise exception
         print '... do not know how to extract from this format: ' + typl

   def get3D(self,typl,what):
      obj = self.object[what['file']]

      if 'SELAFIN' in typl.upper() or \
         'slf' in typl.lower():
         ftype,fsize = obj.file['float']

         # TODO: range of plans and resample within a 2d and a 3d box.
         if what['type'].split(':')[1] == 'i-surface':

            # ~~> Extract data
            IKLE2 = obj.IKLE2
            IKLE3 = obj.IKLE3
            MESHX = np.tile(obj.MESHX,obj.NPLAN)
            MESHY = np.tile(obj.MESHY,obj.NPLAN)
            IKLE4 = IKLE3
            MESHZ = obj.castVMeshAtLevels(what["time"],what["extract"])[3].ravel()
            tree = obj.tree
            tria = obj.neighbours

            # ~~> Possible re-sampling
            if what["sample"] != '':
               support2d = []
               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Spatial 2D
               supMESHX = MESHX[0:obj.NPOIN2]; supMESHY = MESHY[0:obj.NPOIN2]
               MESHX = []; MESHY = []
               IKLE4 = []; support2d = []
               grids,plans = whatSample(what["sample"],[(min(supMESHX),min(supMESHY)),(max(supMESHX),max(supMESHY)),[0,obj.NPLAN]])
               if len(plans) < 2:
                  print '... you have to have more than one plan in '+what["sample"]+' for the smapling of a 3d volume'
                  sys.exit(1)
               for dimx,dimy,x,y in grids:
                  for xyi in np.dstack((x,y))[0]:
                     support2d.append( xysLocateMesh(xyi,IKLE2,supMESHX,supMESHY,tree,tria) )
                  IKLE4.extend((
                     [ i+j*dimx+k*dimx*dimy,i+1+j*dimx+k*dimx*dimy,i+1+(j+1)*dimx+k*dimx*dimy,i+(j+1)*dimx+k*dimx*dimy,
                     i+j*dimx+(k+1)*dimx*dimy,i+1+j*dimx+(k+1)*dimx*dimy,i+1+(j+1)*dimx+(k+1)*dimx*dimy,i+(j+1)*dimx+(k+1)*dimx*dimy ]
                     for k in range(len(plans)-1) for j in range(dimy-1) for i in range(dimx-1) ))
                  MESHX.extend(( x for k in range(len(plans)) ))
                  MESHY.extend(( y for k in range(len(plans)) ))
               IKLE4 = np.asarray(IKLE4)
               MESHX = np.asarray(MESHX)
               MESHY = np.asarray(MESHY)
               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Vertical component
               if fsize == 4: data = np.zeros((len(plans),len(support2d)),dtype=np.float32)
               else: data = np.zeros((len(plans),len(support2d)),dtype=np.float64)
               for ipt in range(len(support2d)):
                  ln,bn = support2d[ipt]
                  for inod in range(len(bn)):  # /!\ node could be outside domain
                     for iplan in range(len(plans)):
                        if ln[inod] >=0: data[iplan][ipt] += bn[inod]*MESHZ[iplan][ln[inod]]
               MESHZ = data.ravel()

            # ~~> Loop on variables
            for var in what["vars"].split(';'):
               v,vtype = var.split(':')

               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Extract variable data for only one time frame and one plane
               VARSORS = obj.castValues(v,what['time'])
               # ~~> Draw/Dump (multiple options possible)
               if "wire" in vtype or "grid" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE4],MESHY[IKLE4],MESHZ[IKLE4])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
               if "mesh" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE4],MESHY[IKLE4],MESHZ[IKLE4])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
               if "map" in vtype or "label" in vtype or "contour" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHY,MESHZ,IKLE4),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
               elif "arrow" in vtype or "vector" in vtype or "angle" in vtype or "streamline" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHY,MESHZ,IKLE4),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
               else: print '... do not know how to draw this SELAFIN type: ' + vtype

         elif what['type'].split(':')[1] == 'p-section':

            # ~~> Extract data
            IKLE3,MESHX,MESHY,zpo = obj.castHMeshAtLevels(what['extract'])
            if obj.NDP2 == 4: IKLE3 = splitQuad2Triangle(IKLE3)
            IKLE4 = IKLE3
            vars,vtypes = whatVarsSLF(what['vars'],obj.VARNAMES)
            tree = obj.tree
            tria = obj.neighbours

            MESHZ = obj.castVMeshAtLevels(what["time"],what["extract"])[3].ravel()

            # ~~> Possible re-sampling
            support2d = []
            if what["sample"] != '':
               supMESHX = MESHX; supMESHY = MESHY
               MESHX = []; MESHY = []
               IKLE4 = []
               grids,n = whatSample(what["sample"],[(min(supMESHX),min(supMESHY)),(max(supMESHX),max(supMESHY))])
               for dimx,dimy,x,y in grids:
                  for xyi in np.dstack((x,y))[0]:
                     support2d.append( xysLocateMesh(xyi,IKLE3,supMESHX,supMESHY,tree,tria) )
                  IKLE4.extend(([ i+j*dimx,i+1+j*dimx,i+1+(j+1)*dimx,i+(j+1)*dimx ] for j in range(dimy-1) for i in range(dimx-1) ))
                  MESHX.extend(x)
                  MESHY.extend(y)
               IKLE4 = np.asarray(IKLE4)
               IKLE3 = splitQuad2Triangle(IKLE4)
               MESHX = np.asarray(MESHX)
               MESHY = np.asarray(MESHY)

            # ~~> Loop on variables
            for var in what["vars"].split(';'):
               v,vtype = var.split(':')

               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Extract variable data for only one time frame and one plane
               VARSORS = obj.castHValueAtLevels(v,what['time'],what['extract'])
               # ~~> Re-sampling
               if support2d != []:
                  if fsize == 4: data = np.zeros((len(vars[0]),len(support2d)),dtype=np.float32)
                  else: data = np.zeros((len(vars[0]),len(support2d)),dtype=np.float64)
                  for ivar in range(len(vars[0])):
                     for ipt in range(len(support2d)):
                        ln,bn = support2d[ipt]
                        data[ivar][ipt] = 0.0
                        for inod in range(len(bn)):                  # /!\ node could be outside domain
                           if ln[inod] >=0: data[ivar][ipt] += bn[inod]*VARSORS[ivar][ln[inod]]
                  VARSORS = data
                  supMESHZ = MESHZ
                  if fsize == 4: MESHZ = np.zeros(len(support2d),dtype=np.float32)
                  else: MESHZ = np.zeros(len(support2d),dtype=np.float64)
                  for ipt in range(len(support2d)):
                     ln,bn = support2d[ipt]
                     MESHZ[ipt] = 0.0
                     for inod in range(len(bn)):                  # /!\ node could be outside domain
                        if ln[inod] >=0: MESHZ[ipt] += bn[inod]*supMESHZ[ln[inod]]
               # ~~> Draw/Dump (multiple options possible)
               if "map" in vtype or "label" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHY,MESHZ,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,MESHZ,IKLE3),VARSORS
               elif "arrow" in vtype or "vector" in vtype or "angle" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHY,MESHZ,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,MESHZ,IKLE3),VARSORS
               else: print '... do not know how to draw this SELAFIN type: ' + vtype

         elif what['type'].split(':')[1] == 'v-section':

            # ~~> Extract data
            IKLE4,MESHX,MESHY,MESHZ, support3d = obj.castVMeshAtPolyline_Plane(what["time"],what["extract"])

            # split each quad into triangles
            IKLE3 = splitQuad2Triangle(IKLE4)
            vars,vtypes = whatVarsSLF(what['vars'],obj.VARNAMES)
            time = whatTimeSLF(what['time'],obj.tags['cores'])
            tree = getKDTree(MESHX,MESHZ,IKLE3)
            tria = getMPLTri(MESHX,MESHZ,IKLE3)[0]
            data = getValuePolylineSLF(obj.file,obj.tags,time,support3d,obj.NVAR,obj.NPOIN3,obj.NPLAN,vars)

            # ~~> Possible sampling of the data
            # No resampling yet

            # ~~> Loop on variables
            for v,vtype in zip(vars,vtypes):

               VARSORS = []
               for ivar in range(len(vars[0])): VARSORS.append( np.ravel(data[ivar][0].T) )

               # ~~> Re-sampling
               # No resampling yet

               # ~~> Draw/Dump (multiple options possible)
               if "map" in vtype or "label" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHY,MESHZ,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHZ,IKLE3),VARSORS
               if "arrow" in vtype or "vector" in vtype or "angle" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHY,MESHZ,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHZ,IKLE3),VARSORS

         elif what['type'].split(':')[1] == '':

            # ~~> Extract data
            IKLE3 = obj.IKLE3
            MESHX = obj.MESHX
            MESHY = obj.MESHY
            if obj.NDP2 == 4: IKLE3 = splitQuad2Triangle(IKLE3)
            IKLE4 = IKLE3
            vars,vtypes = whatVarsSLF(what['vars'],obj.VARNAMES)
            tree = obj.tree
            tria = obj.neighbours

            # ~~> Possible re-sampling
            support2d = []
            #if what["sample"] != '':
            #   supMESHX = MESHX; supMESHY = MESHY
            #   MESHX = []; MESHY = []
            #   IKLE4 = []; support2d = []
            #   grids,n = whatSample(what["sample"],[(min(supMESHX),min(supMESHY)),(max(supMESHX),max(supMESHY))])
            #   for dimx,dimy,x,y in grids:
            #      for xyi in np.dstack((x,y))[0]:
            #         support2d.append( xysLocateMesh(xyi,IKLE3,supMESHX,supMESHY,tree,tria) )
            #      IKLE4.extend(([ i+j*dimx,i+1+j*dimx,i+1+(j+1)*dimx,i+(j+1)*dimx ] for j in range(dimy-1) for i in range(dimx-1) ))
            #      MESHX.extend(x)
            #      MESHY.extend(y)
            #   IKLE4 = np.asarray(IKLE4)
            #   IKLE3 = splitQuad2Triangle(IKLE4)
            #   MESHX = np.asarray(MESHX)
            #   MESHY = np.asarray(MESHY)

            # ~~> Loop on variables
            for var in what["vars"].split(';'):
               v,vtype = var.split(':')

               # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
               # ~~> Extract variable data for only one plane
               VARSORS = obj.castValues(v,what['time'])
               # ~~> Re-sampling
               if support2d != []:
                  if fsize == 4: data = np.zeros(VARSORS.shape,dtype=np.float32)
                  else: data = np.zeros(VARSORS.shape,dtype=np.float64)
                  for itime in range(len(VARSORS)):
                     for ivar in range(len(vars[0])):
                        for ipt in range(len(support2d)):
                           ln,bn = support2d[ipt]
                           for inod in range(len(bn)):                  # /!\ node could be outside domain
                              if ln[inod] >=0: data[itime][ivar][ipt] += bn[inod]*VARSORS[itime][ivar][ln[inod]]
                  VARSORS = data
               # ~~> Draw/Dump (multiple options possible)
               if "wire" in vtype or "grid" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE4],MESHY[IKLE4])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE4],MESHY[IKLE4]))
               if "mesh" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'wire', 'support':np.dstack((MESHX[IKLE3],MESHY[IKLE3])),
                     'function':'none', 'values':[] })
                  return self.obdata[what["xref"]]
                  # return np.dstack((MESHX[IKLE3],MESHY[IKLE3]))
               if "map" in vtype or "label" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'map', 'support':(MESHX,MESHY,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,IKLE3),VARSORS
               elif "arrow" in vtype or "vector" in vtype or "angle" in vtype:
                  self.obdata[what["xref"]] = Values({'type':what['type'],
                     'unit':'vector', 'support':(MESHX,MESHY,IKLE3),
                     'function':'none', 'values':VARSORS })
                  return self.obdata[what["xref"]]
                  # return (MESHX,MESHY,IKLE3),VARSORS
               else: print '... do not know how to draw this SELAFIN type: ' + vtype

         # ~~> unknown
         else: # TODO: raise exception
            print '... do not know how to do this type of extraction: ' + what['type'].split(':')[1]

      # ~~> unknown
      else: # TODO: raise exception
         print '... do not know how to extract from this format: ' + typl


# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$13-Jul-2014 08:51:29$"

if __name__ == "__main__":

   sys.exit(0)
