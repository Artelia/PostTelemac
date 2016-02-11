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
"""@history 26/12/2011 -- Sebastien E. Bourban
"""
"""@brief
      Tools for trivial polygon operations
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
from os import path
import numpy as np
sys.path.append( path.join( path.dirname(sys.argv[0]), '..' ) )
# ~~> dependencies towards other modules
from config import OptionParser
# ~~> dependencies towards other pytel/modules
from utils.geometry import getConeAngle,isClose,getNorm2
from utils.progressbar import SubProgressBar
from parsers.parserKenue import InS

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#
def joinSegments(polyLines):

   polyGones = []
   while polyLines != []:
      # ~~> starting point
      e = polyLines[0]
      a,b = e[0],e[len(e)-1]
      # ~~> case of closed line
      if a == b:
         polyGones.append(e[1:])
         polyLines.pop(0)
         continue
      # ~~> iterative process
      iline = 1
      ei = polyLines[iline]
      while b != ei[0]:
         iline += 1
         ei = polyLines[iline]
      # ~~> merging the two segments
      e.extend(ei[1:])
      polyLines[0] = e
      polyLines.pop(iline)

   return polyGones

def smoothSubdivise(poly,vals,type,weight):

   ptwice = np.zeros((2*len(poly)-1+type,2))
   #vtwice = np.zeros((2*len(poly)-1+type,2,len(lavs)))
   # ~~> save original set
   for i in range(len(poly)): ptwice[2*i] = poly[i]
   # ~~> include intermediates
   for i in range(len(poly)-1): ptwice[2*i+1]  = ( poly[i]+poly[i+1] )/2.
   if type!=0: ptwice[2*len(poly)-1]  = ( poly[0]+poly[len(poly)-1] )/2.
   # ~~> weighted-average of the original
   for i in range(len(poly)-1)[1:]: ptwice[2*i] = weight*ptwice[2*i] + (1-weight)*( ptwice[2*i-1]+ptwice[2*i+1] )/2.
   if type!=0:
      ptwice[0] = weight*ptwice[0] + (1-weight)*( ptwice[len(ptwice)-1]+ptwice[1] )/2.
      ptwice[len(ptwice)-2] = weight*ptwice[len(ptwice)-2] + (1-weight)*( ptwice[len(ptwice)-1]+ptwice[len(ptwice)-3] )/2.

   return ptwice,vals,type

def removeDuplicates(poly,type): # /!\ does not work anymore
   found = True
   while found:
      i = 0; found = False
      while i < len(poly)-1:
         if isClose( poly[i],poly[i+1],size=10 ):
            found = True
            poly = np.delete(poly,i+1,0)
         i += 1
   if len(poly) == 1: return [],0
   elif len(poly) == 2: return [],0 #poly,0
   else:
      if type != 0:
         if isClose( poly[len(poly)-1],poly[0],size=10 ): poly = np.delete(poly,len(poly)-1,0)
      if len(poly) < 3: return [],0 #poly,0
      return poly,type

def removeDuplilines(poly,type):
   p = []; t = []; stencil = 1000
   sbar = SubProgressBar(maxval=len(poly)).start()
   found = False
   for i in range(len(poly)):
      for j in range(len(poly))[i+2:i+2+stencil]:
         if isClose( poly[i],poly[j] ):
            ia = (i+1)%len(poly)
            ib = (j-1)%len(poly)
            if isClose( poly[ia],poly[ib] ):
               poly1,ptmp1,poly2,ptmp2,poly3 = np.split(poly,[i,ia,ib,j])
               p.append(np.concatenate((poly1, poly3), axis=0))
               if type == 1: t.append(1)
               p.append(poly2)
               t.append(1)
               found = True
         if found: break
      if found: break
      sbar.update(i)
   sbar.finish()
   if p == []:
      p.append(poly); t.append(type)
   return p,v,t

def removeDuplangles(poly,vals,type): # /!\ does not work anymore

   found = True
   while found:
      i = 0; found = False
      while i < len(poly)-3:
         if 1 > 180*abs( getConeAngle( poly[i],poly[i+1],poly[i+2] ) )/np.pi:
            poly = np.delete(poly,i+1,0)
            found = True
         if 1 > 180*abs( getConeAngle( poly[i+1],poly[i+2],poly[i+3] ) )/np.pi:
            poly = np.delete(poly,i+2,0)
            found = True
         i += 2
   if len(poly) < 3: return [],0 #poly,0
   return poly,type

def subsampleDistance(poly,type,dist):

   found = True
   while found:
      i = 0; found = False
      while i < len(poly)-1:
         if dist > getNorm2( poly[i],poly[i+1] ):
            poly[i] = ( poly[i]+poly[i+1] )/2.
            poly = np.delete(poly,i+1,0)
            vals[i] = ( vals[i]+vals[i+1] )/2.
            vals = np.delete(vals,i+1,0)
            found = True
         i += 1
   if len(poly) == 1: return [],[],0
   elif len(poly) == 2: return [],[],0 #poly,0
   else:
      if type!=0:
         if dist > getNorm2( poly[len(poly)-1],poly[0] ):
            poly[len(poly)-1] = ( poly[len(poly)-1]+poly[0] )/2.
            poly = np.delete(poly,0,0)
            vals[len(vals)-1] = ( vals[len(vals)-1]+vals[0] )/2.
            vals = np.delete(vals,0,0)
      if len(poly) < 3: return [],[],0 #poly,0
      return poly,vals,type

def subsampleAngle(poly,vals,type,angle):

   found = True
   while found:
      i = 0; found = False
      while i < len(poly)-4:
         if angle > 180*abs( abs(getConeAngle( poly[i],poly[i+1],poly[i+2] )) - np.pi )/np.pi:
            poly = np.delete(poly,i+1,0)
            vals = vals.pop(i+1)
            found = True
         if angle > 180*abs( abs(getConeAngle( poly[i+1],poly[i+2],poly[i+3] )) - np.pi )/np.pi:
            poly = np.delete(poly,i+2,0)
            vals = vals.pop(i+2)
            found = True
         i += 2
   if len(poly) < 3: return [],[],0 #poly,vals,0
   return poly,vals,type

def isClockwise(poly):
   # assumes that poly does not duplicate points
   wise = 0
   for i in range(len(poly)):
      z = ( poly[(i+1)%len(poly)][0]-poly[i][0] ) \
         *( poly[(i+2)%len(poly)][1]-poly[(i+1)%len(poly)][1] ) \
         - ( poly[(i+1)%len(poly)][1]-poly[i][1] ) \
         * ( poly[(i+2)%len(poly)][0]-poly[(i+1)%len(poly)][0] )
      if z > 0: wise += 1
      elif z < 0: wise -= 1
   return wise < 0

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$15-Nov-2011 08:51:29$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)

"""
Early work by S.E.Bourban ... will be replaced by more recent work from M.S.Turnbull

def cutAngleJoinSplit(poly,angle,dist,stencil):

   d2 = np.power(dist,2)     # ~~> d square will save some calculation time
   a2 = angle * np.pi / 180.
   remo = []                 # ~~> left over
   found = True
   while found:
      found = False
      iline = 0
      for s in range(stencil)[:int(2*stencil/3):-2]:   # ~~> here you start wit hthe larger stencil first
         iline = iline%len(poly)
         while iline < len(poly):
            #ibar = min((iline-stencil)%len(line)*len(line)/l0Line+stencil*l0Line,(maxStencil-4)*l0Line)
            # ~~> takes points on either sides (stencil)
            a,b,c = poly[(iline-s)%len(poly)],poly[iline%len(poly)],poly[(iline+s)%len(poly)]
            # ~~> calculates the "vision" angle -- (+):inlet; (-):headland assuming anti-clockwise
            cosac = getConeAngle( a,b,c )
            if abs(cosac) < a2 and cosac > 0:
               if getDistancePointToLine( c,b,a ) < dist or getDistancePointToLine( a,b,c ) < dist:
                  remo.append(poly[(iline-s)%len(poly):(iline+s)%len(poly)+1])
                  iline += stencil
               #   should use split / join
               #   poly = np.delete(poly,iline%len(line))
               #   print 'I can delete the following',a,b,c
               #   sys.exit(1)
               #   found += 1
               #   continue
            iline += 1
            #pbar.update(ibar)
         #pbar.write('Areas of interst found: '+str(found),ibar)
      #if found == 0: break
      #pbar.finish()

   return poly,remo
"""
