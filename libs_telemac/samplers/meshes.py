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
"""@history 12/12/2012 -- Sebastien E. Bourban
     Many methods developped for application to meshes. The latest
        one being about subdivision of meshes.
"""
"""@brief
      Tools for sampling and interpolating through triangular meshes
"""
"""@details
         Contains ...
"""
"""@history 20/06/2013 -- Sebastien E. Bourban
      A new method, sliceMesh, now replaces crossMesh and all of the
         Ray Tracing algorithms. The later will remain for the fame and
         maybe for future uses, but sliveMesh should now be used.
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
from os import path
import numpy as np
import math
from scipy.spatial import cKDTree
import matplotlib.path as mplPath
from scipy.spatial import Delaunay
from matplotlib.tri import Triangulation
sys.path.append( path.join( path.dirname(sys.argv[0]), '..' ) )
# ~~> dependencies towards other modules
from config import OptionParser
# ~~> dependencies towards other pytel/modules
from parsers.parserSELAFIN import SELAFIN
from utils.progressbar import ProgressBar
from utils.geometry import isCCW,getSegmentIntersection,getBarycentricWeights,isInsideTriangle,getDistancePointToLine
from samplers.polygons import isClockwise,joinSegments

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def nearLocateMesh(xyo,IKLE,MESHX,MESHY,tree=None):
   """
   Requires the scipy.spatial and the matplotlib.tri packages to be loaded.
    - Will use already computed tree or re-create it if necessary.
    - Will use already computed neighbourhood or re-create it if necessary.
   This function return the element number for the triangle including xyo=(xo,yo)
      or -1 if the (xo,yo) is outside the mesh
   Return: the element, the barycentric weights, and the tree and the neighbourhood if computed
   """
   # ~~> Create the KDTree of the iso-barycentres
   if tree == None:
      isoxy = np.column_stack((np.sum(MESHX[IKLE],axis=1)/3.0,np.sum(MESHY[IKLE],axis=1)/3.0))
      tree = cKDTree(isoxy)
   # ~~> Find the indices corresponding to the nearest elements to the points
   inear = -1
   for d,i in zip(*tree.query(xyo,8)):
      ax,bx,cx = MESHX[IKLE[i]]
      ay,by,cy = MESHY[IKLE[i]]
      w = isInsideTriangle( xyo,(ax,ay),(bx,by),(cx,cy),nomatter=True )
      if w != []: return i,w,tree
      if inear < 0:
         inear = i
         dnear = d
      if dnear > d:
         inear = i
         dnear = d

   # ~~> Find the indices and weights corresponding to the element containing the point
   ax,bx,cx = MESHX[IKLE[inear]]
   ay,by,cy = MESHY[IKLE[inear]]

   return inear,isInsideTriangle( xyo,(ax,ay),(bx,by),(cx,cy),nomatter=False ),tree

def dichoLocateMesh(rank,e1,xy1,e2,xy2,IKLE,MESHX,MESHY,tree):
   """
   Will find at least one point between xy1 and xy2 that is within the mesh
   """
   # ~~ Position the middle point ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   xyo = [ ( xy1[0]+xy2[0] )/2.0,( xy1[1]+xy2[1] )/2.0 ]
   eo,bo,tree = nearLocateMesh(xyo,IKLE,MESHX,MESHY,tree)
   if bo != []: return True,eo,xyo,bo

   # ~~ Limit the number of useless dichotomies ~~~~~~~~~~~~~~~~~~~~
   rank = rank + 1
   if rank > 3: return False,eo,xyo,bo

   # ~~ Sub-segments ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   found,ej,xyj,bj = dichoLocateMesh(rank,e1,xy1,eo,xyo,IKLE,MESHX,MESHY,tree)
   if found: return found,ej,xyj,bj
   found,ej,xyj,bj = dichoLocateMesh(rank,eo,xyo,e2,xy2,IKLE,MESHX,MESHY,tree)
   if found: return found,ej,xyj,bj

   return False,eo,xyo,bo

def xyTraceMesh(inear,xyi,xyo,IKLE,MESHX,MESHY,neighbours=None):
   """
   Requires the matplotlib.tri package to be loaded.
    - Will use already computed neighbourhood or re-create it if necessary.
   This function return the element number for the triangle including xyo=(xo,yo)
      or -1 if the (xo,yo) is outside the mesh. It creates the neighbouring connectivity
      map and ray-traces from xyi to xyo
   Return: whether xyo was found within the mesh, the (nearest) element, the
      associated barycentric weights, and the neighbourhood if computed
   """
   if neighbours == None:
      neighbours = Triangulation(MESHX,MESHY,IKLE).get_cpp_triangulation().get_neighbors()
   found,ray = traceRay2XY(IKLE,MESHX,MESHY,neighbours,inear,xyi,inear,xyo)

   return found,ray,neighbours

def subdivideMesh(IKLE,MESHX,MESHY):
   """
   Requires the matplotlib.tri package to be loaded.
    - Will use already computed edges or re-create it if necessary.
   This function return a new tuple IKLE,MESHX,MESHY where each triangle has been
      subdivided in 4.
   """
   # ~~> Singling out edges
   from matplotlib.tri import Triangulation
   edges = Triangulation(MESHX,MESHY,IKLE).get_cpp_triangulation().get_edges()

   # ~~> Memory allocation for new MESH
   IELEM = len(IKLE); IPOIN = len(MESHX); IEDGE = len(edges)
   JKLE = np.zeros((IELEM*4,3),dtype=np.int)       # you subdivide every elements by 4
   MESHJ = np.zeros((IEDGE,2),dtype=np.int)        # you add one point on every edges

   # ~~> Lookup tables for node numbering on common edges
   pa,pb = edges.T
   k1b,k1a = np.sort(np.take(IKLE,[0,1],axis=1)).T
   indx1 = np.searchsorted(pa,k1a)
   jndx1 = np.searchsorted(pa,k1a,side='right')
   k2b,k2a = np.sort(np.take(IKLE,[1,2],axis=1)).T
   indx2 = np.searchsorted(pa,k2a)
   jndx2 = np.searchsorted(pa,k2a,side='right')
   k3b,k3a = np.sort(np.take(IKLE,[2,0],axis=1)).T
   indx3 = np.searchsorted(pa,k3a)
   jndx3 = np.searchsorted(pa,k3a,side='right')

   # ~~> Building one triangle at a time /!\ Please get this loop parallelised
   j = 0
   for i in range(IELEM):
      k1 = indx1[i]+np.searchsorted(pb[indx1[i]:jndx1[i]],k1b[i])
      k2 = indx2[i]+np.searchsorted(pb[indx2[i]:jndx2[i]],k2b[i])
      k3 = indx3[i]+np.searchsorted(pb[indx3[i]:jndx3[i]],k3b[i])
      # ~~> New connectivity JKLE
      JKLE[j] = [IKLE[i][0],IPOIN+k1,IPOIN+k3]
      JKLE[j+1] = [IKLE[i][1],IPOIN+k2,IPOIN+k1]
      JKLE[j+2] = [IKLE[i][2],IPOIN+k3,IPOIN+k2]
      JKLE[j+3] = [IPOIN+k1,IPOIN+k2,IPOIN+k3]
      # ~~> New interpolation references for values and coordinates
      MESHJ[k1] = [IKLE[i][0],IKLE[i][1]]
      MESHJ[k2] = [IKLE[i][1],IKLE[i][2]]
      MESHJ[k3] = [IKLE[i][2],IKLE[i][0]]
      j += 4

   # ~~> Reset IPOBO while you are at it
   MESHX = np.resize(MESHX,IPOIN+IEDGE)
   MESHY = np.resize(MESHY,IPOIN+IEDGE)
   MESHX[IPOIN:] = np.sum(MESHX[MESHJ],axis=1)/2.
   MESHY[IPOIN:] = np.sum(MESHY[MESHJ],axis=1)/2.
   neighbours = Triangulation(MESHX,MESHY,JKLE).get_cpp_triangulation().get_neighbors()
   JPOBO = np.zeros(IPOIN+IEDGE,np.int)
   for n in range(IELEM*4):
      s1,s2,s3 = neighbours[n]
      e1,e2,e3 = JKLE[n]
      if s1 < 0:
        JPOBO[e1] = e1+1
        JPOBO[e2] = e2+1
      if s2 < 0:
        JPOBO[e2] = e2+1
        JPOBO[e3] = e3+1
      if s3 < 0:
        JPOBO[e3] = e3+1
        JPOBO[e1] = e1+1

   return JKLE,MESHX,MESHY,JPOBO,MESHJ

def traceRay2XY(IKLE,MESHX,MESHY,neighbours,ei,xyi,en,xyn):
   """
   This assumes that you cannot go back on your ray.
   """
   # ~~> latest addition to the ray
   ax,bx,cx = MESHX[IKLE[en]]
   ay,by,cy = MESHY[IKLE[en]]
   bi = getBarycentricWeights( xyi,(ax,ay),(bx,by),(cx,cy) )
   pnt = {'n':1, 'xy':[xyi], 'e':[en], 'b':[bi],
      'd':[np.power(xyi[0]-xyn[0],2) + np.power(xyi[1]-xyn[1],2)]}

   # ~~> convergence on distance to target xyn
   accuracy = np.power(10.0, -5+np.floor(np.log10(abs(ax+bx+cx+ay+by+cy))))
   if pnt['d'][0] < accuracy: return True,pnt

   # ~~> get the ray through to the farthest neighbouring edges
   ks = []; ds = []
   for k in [0,1,2]:
      xyj = getSegmentIntersection( (MESHX[IKLE[en][k]],MESHY[IKLE[en][k]]),(MESHX[IKLE[en][(k+1)%3]],MESHY[IKLE[en][(k+1)%3]]),xyi,xyn )
      if xyj == []: continue         # there are no intersection with that edges
      ej = neighbours[en][k]
      if ej == ei: continue          # you should not back track on your ray
      xyj = xyj[0]
      dij = np.power(xyi[0]-xyj[0],2) + np.power(xyi[1]-xyj[1],2)
      ks.append(k)
      ds.append(dij)
   if ds != []:
      k = ks[np.argmax(ds)]
      ej = neighbours[en][k]
      xyj = getSegmentIntersection( (MESHX[IKLE[en][k]],MESHY[IKLE[en][k]]),(MESHX[IKLE[en][(k+1)%3]],MESHY[IKLE[en][(k+1)%3]]),xyi,xyn )[0]
      djn = np.power(xyn[0]-xyj[0],2) + np.power(xyn[1]-xyj[1],2)

      # ~~> Possible recursive call
      if True or djn > accuracy:    # /!\ this may be a problem
         if ej < 0:
            # you have reach the end of the line
            bj = getBarycentricWeights( xyj,(ax,ay),(bx,by),(cx,cy) )
            pnt['n'] += 1; pnt['xy'].insert(0,xyj); pnt['e'].insert(0,en); pnt['b'].insert(0,bj); pnt['d'].insert(0,djn)
            return djn<accuracy,pnt
         else:
            found,ray = traceRay2XY(IKLE,MESHX,MESHY,neighbours,en,xyj,ej,xyn)
            ray['n'] += 1; ray['xy'].append(xyi); ray['e'].append(en); ray['b'].append(bi); ray['d'].append(dij)
            return found,ray

   # ~~> convergence on having found the appropriate triangle
   bn = isInsideTriangle( xyn,(ax,ay),(bx,by),(cx,cy) )
   if bn != []:
      pnt['n'] += 1; pnt['xy'].insert(0,xyn); pnt['e'].insert(0,en); pnt['b'].insert(0,bn); pnt['d'].insert(0,0.0)
      return True,pnt

   # ~~> you should not be here !
   return False,pnt

def xysLocateMesh(xyo,IKLE,MESHX,MESHY,tree=None,neighbours=None):

   # ~~> get to the nearest element
   oet = -1; obr = [0.0,0.0,0.0]
   eo,bo,tree = nearLocateMesh(np.array(xyo),IKLE,MESHX,MESHY,tree)
   if bo == []:
      found,ray,neighbours = xyTraceMesh(eo,[np.sum(MESHX[IKLE[eo]])/3.0,np.sum(MESHY[IKLE[eo]])/3.0],xyo,IKLE,MESHX,MESHY,neighbours)
      if found:
         obr = ray['b'][ray['n']]
         oet = ray['e'][ray['n']]
   else:
      obr = bo
      oet = eo

   if oet == -1: return [-1,-1,-1],obr
   return IKLE[oet],obr

def crossMesh(polyline,IKLE,MESHX,MESHY,tree=None,neighbours=None):
   """
   """
   # ~~ Intersection nodes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   ipt = []; iet = []; ibr = []

   # ~~ Locate nodes of the polyline ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   xyo = polyline[0]
   eo,bo,tree = nearLocateMesh(xyo,IKLE,MESHX,MESHY,tree)

   for i in range(len(polyline)-1):
      xyi = polyline[i+1]
      ei,bi,tree = nearLocateMesh(xyi,IKLE,MESHX,MESHY,tree)
      if bo == [] and bi == []:
         rank = 0
         found,ej,xyj,bj = dichoLocateMesh(rank,eo,xyo,ei,xyi,IKLE,MESHX,MESHY,tree)
         if not found:
            print '... Could not find easily an intersection with the mesh'
            sys.exit(1)
         found,rayo,neighbours = xyTraceMesh(ej,xyj,xyo,IKLE,MESHX,MESHY,neighbours)
         #print 'raya'
         for j in range(rayo['n'])[:-1]:
            #print rayo['e'][j],rayo['xy'][j]
            ipt.append(rayo['xy'][j]); iet.append(rayo['e'][j]); ibr.append(rayo['b'][j])
         found,rayi,neighbours = xyTraceMesh(ej,xyj,xyi,IKLE,MESHX,MESHY,neighbours)
         #print 'rayb'
         for j in range(rayi['n'])[(rayi['n']-1)::-1]:
            #print rayi['e'][j],rayi['xy'][j]
            ipt.append(rayi['xy'][j]); iet.append(rayi['e'][j]); ibr.append(rayi['b'][j])
      elif bi == [] and bo != []:
         found,rayi,neighbours = xyTraceMesh(eo,xyo,xyi,IKLE,MESHX,MESHY,neighbours)
         #print 'rayc'
         for j in range(rayi['n'])[(rayi['n']-1)::-1]:
            #print rayi['e'][j],rayi['xy'][j]
            ipt.append(rayi['xy'][j]); iet.append(rayi['e'][j]); ibr.append(rayi['b'][j])
      elif bi != [] and bo == []:
      # it is necessary to reverse the ray for a case with first end outside
         found,rayo,neighbours = xyTraceMesh(ei,xyi,xyo,IKLE,MESHX,MESHY,neighbours)
         #print 'rayd'
         for j in range(rayo['n']): #[(rayo['n']-1)::-1]:
            #print rayo['e'][j],rayo['xy'][j]
            ipt.append(rayo['xy'][j]); iet.append(rayo['e'][j]); ibr.append(rayo['b'][j])
      else:
         found,rayi,neighbours = xyTraceMesh(eo,xyo,xyi,IKLE,MESHX,MESHY,neighbours)
         #print 'rayi',rayi
         for j in range(rayi['n'])[(rayi['n']-1)::-1]:
            #print rayi['e'][j],rayi['xy'][j]
            ipt.append(rayi['xy'][j]); iet.append(rayi['e'][j]); ibr.append(rayi['b'][j])

      xyo = xyi; bo = bi; eo = ei

   return (ipt,iet,ibr),tree,neighbours


def sliceMesh(polyline,IKLE,MESHX,MESHY,tree=None):
   """
   A new method to slice through a triangular mesh (replaces crossMesh)
   """
   from matplotlib.tri import Triangulation
   xys = []
   douplets = []
   # ~~> Calculate the minimum mesh resolution
   dxy = math.sqrt(min(np.square(np.sum(np.fabs(MESHX[IKLE]-MESHX[np.roll(IKLE,1)]),axis=1)/3.0) + \
            np.square(np.sum(np.fabs(MESHY[IKLE]-MESHY[np.roll(IKLE,1)]),axis=1)/3.0)))
   accuracy = np.power(10.0, -8+np.floor(np.log10(dxy)))

   xyo = np.array(polyline[0])
   for i in range(len(polyline)-1):
      xyi = np.array(polyline[i+1])
      dio = math.sqrt(sum(np.square(xyo-xyi)))

      # ~~> Resample the line to that minimum mesh resolution
      rsmpline = np.dstack((np.linspace(xyo[0],xyi[0],num=int(dio/dxy)),np.linspace(xyo[1],xyi[1],num=int(dio/dxy))))[0]
      nbpoints = len(rsmpline)
      nbneighs = min( 8,len(IKLE) )
      # ~~> Filter closest 8 elements (please create a good mesh) as a halo around the polyline
      halo = np.zeros((nbpoints,nbneighs),dtype=np.int)
      for i in range(nbpoints):
         d,e = tree.query(rsmpline[i],nbneighs)
         halo[i] = e
      halo = np.unique(halo)

      # ~~> Get the intersecting halo (on a smaller mesh connectivity)
      edges = Triangulation(MESHX,MESHY,IKLE[halo]).get_cpp_triangulation().get_edges()

      # ~~> Last filter, all nodes that are on the polyline
      olah = []
      nodes = np.unique(edges)
      for node in nodes:  # TODO(jcp): replace by numpy calcs
         if getDistancePointToLine((MESHX[node],MESHY[node]),xyo,xyi) < accuracy: olah.append(node)
      ijsect = zip(olah,olah)
      xysect = [(MESHX[i],MESHY[i]) for i in olah]
      lmsect = [ (1.0,0.0) for i in range(len(ijsect)) ]
      mask = np.zeros((len(edges),2),dtype=bool)
      for i in olah:
         mask = np.logical_or( edges == i  , mask )
      edges = np.compress(np.logical_not(np.any(mask,axis=1)),edges,axis=0)

      # ~~> Intersection with remaining edges
      for edge in edges:
         xyj = getSegmentIntersection( (MESHX[edge[0]],MESHY[edge[0]]),(MESHX[edge[1]],MESHY[edge[1]]),xyo,xyi )
         if xyj != []:
            ijsect.append(edge)     # nodes from the mesh
            xysect.append(tuple(xyj[0]))   # intersection (xo,yo)
            lmsect.append((xyj[1],1.0-xyj[1]))   # weight along each each

      # ~~> Final sorting along keys x and y
      xysect = np.array(xysect, dtype=[('x', '<f4'), ('y', '<f4')])
      xysort = np.argsort(xysect, order=('x','y'))

      # ~~> Move on to next point
      for i in xysort:
         xys.append( xysect[i] )
         douplets.append( (ijsect[i],lmsect[i]) )
      xyo = xyi

   return xys,douplets

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$12-Dec-2012 08:51:29$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)
