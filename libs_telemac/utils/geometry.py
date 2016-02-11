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
      An accuracy has been introduced because Python does not seem
      to be accurate with sums and multiplications
"""
"""@history 07/12/2011 -- Sebastien E. Bourban
      Addition of 3 new geometrical tools:
      + getSegmentLineIntersection (different from getSegmentIntersection)
      + getPlaneEquation (of the form Z = a*X + b*Y + c)
      + getTriangleArea
"""
"""@history 07/01/2012 -- Sebastien E. Bourban
      Addition of a few geometrical tools, working on angles:
      + getConeAngle ( based on arctan2 )
      + getConeSinAngle ( S = ac.sin(B)/2 = det / 2 )
"""
"""@history 14/02/2012 -- Sebastien E. Bourban, Laure C. Grignon
      Addition of the isIsidePoly method to define whether a point is
      inside of a polygon based on the ray casting method
"""
"""@brief
      Tools for trivial geometrical operations
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
import numpy as np
import math

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def isCCW((x1,y1),(x2,y2),(x3,y3)):
   return (y3-y1)*(x2-x1) > (y2-y1)*(x3-x1)

"""@brief
   Returns the coordinate of the point at the intersection
      of two segments, defined by (p1,p2) and (p3,p4)
"""
def getSegmentIntersection( (x1,y1),(x2,y2),(x3,y3),(x4,y4) ):

   det = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
   if det == 0: return []

   # ~~> Using the mlab tools
   #if mlab.segments_intersect( ((x1,y1),(x2,y2)),((x3,y3),(x4,y4)) ):
   #   x0 = ((x3-x4)*(x1*y2-y1*x2)-(x1-x2)*(x3*y4-y3*x4))/det
   #   y0 = ((y3-y4)*(x1*y2-y1*x2)-(y1-y2)*(x3*y4-y3*x4))/det
   #   return [[x0,y0],getNorm2((x0,y0),(x4,y4))/getNorm2((x3,y3),(x4,y4))]
   #return []

   # ~~> Using the clock-wise argument
   #if isCCW((x1,y1),(x3,y3),(x4,y4)) != isCCW((x2,y2),(x3,y3),(x4,y4)) \
   #   and isCCW((x1,y1),(x2,y2),(x3,y3)) != isCCW((x1,y1),(x2,y2),(x4,y4)):
   #   x0 = ((x3-x4)*(x1*y2-y1*x2)-(x1-x2)*(x3*y4-y3*x4))/det
   #   y0 = ((y3-y4)*(x1*y2-y1*x2)-(y1-y2)*(x3*y4-y3*x4))/det
   #   return [[x0,y0],getNorm2((x0,y0),(x4,y4))/getNorm2((x3,y3),(x4,y4))]
   #return []

   # ~~> Using the bounding box method
   x0 = ((x3-x4)*(x1*y2-y1*x2)-(x1-x2)*(x3*y4-y3*x4))/det
   y0 = ((y3-y4)*(x1*y2-y1*x2)-(y1-y2)*(x3*y4-y3*x4))/det
   accuracy = 0
#   accuracy = np.power(10.0, -5  +np.floor(np.log10(abs(x1+x2+x3+x4))))
   if ( min(x1,x2)-x0 ) > accuracy or ( x0-max(x1,x2) ) > accuracy: return []
   if ( min(x3,x4)-x0 ) > accuracy or ( x0-max(x3,x4) ) > accuracy: return []
#   accuracy = np.power(10.0, -5  +np.floor(np.log10(abs(y1+y2+y3+y4))))
   if ( min(y1,y2)-y0 ) > accuracy or ( y0-max(y1,y2) ) > accuracy: return []
   if ( min(y3,y4)-y0 ) > accuracy or ( y0-max(y3,y4) ) > accuracy: return []
   return [[x0,y0],getNorm2((x0,y0),(x2,y2))/getNorm2((x1,y1),(x2,y2))]

"""@brief
   Returns the coordinate of the point at the intersection
      of one segments defined by (p1,p2) and one line (p3,p4)
"""
def getSegmentLineIntersection( (x1,y1),(x2,y2),(x3,y3),(x4,y4) ):

   det = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
   if det == 0: return []
   x0 = ((x3-x4)*(x1*y2-y1*x2)-(x1-x2)*(x3*y4-y3*x4))/det
   y0 = ((y3-y4)*(x1*y2-y1*x2)-(y1-y2)*(x3*y4-y3*x4))/det
   accuracy = np.power(10.0, -5+np.floor(np.log10(abs(x1+x2+x3+x4))))
   if ( min(x1,x2)-x0 ) > accuracy or ( x0-max(x1,x2) ) > accuracy: return []
   accuracy = np.power(10.0, -5+np.floor(np.log10(abs(y1+y2+y3+y4))))
   if ( min(y1,y2)-y0 ) > accuracy or ( y0-max(y1,y2) ) > accuracy: return []

   return [[x0,y0]]

"""
   Find the equation of the plane defined by 3 points.
   The form of the equation is: Z = a*X + b*Y + c
"""
def getNorm2( (x1,y1), (x2,y2) ):
   return np.sqrt( np.power(x1-x2,2) + np.power(y1-y2,2))

def getPlaneEquation( (x1,y1,z1),(x2,y2,z2),(x3,y3,z3) ):

   det = x1*( y2-y3 ) + y1*( x3-x2 ) + ( x2*y3 - y2*x3 )
   a = ( z1*( y2-y3 ) + z2*( y3-y1 ) + z3*( y1-y2 ) )/det
   b = ( z1*( x3-x2 ) + z2*( x1-x3 ) + z3*( x2-x1 ) )/det
   c = ( z1*( x2*y3 - y2*x3 ) + z2*( y1*x3-x1*y3 ) + z3*( x1*y2-y1*x2 ) )/det

   return a,b,c

def getBarycentricWeights( (xo,yo),(x1,y1),(x2,y2),(x3,y3) ):

   det = ( y2-y3 ) * ( x1-x3 ) - ( y1-y3 ) * ( x2-x3 )
   if det == 0.0: return 0.0,0.0,1.0
   l1 = ( ( y2-y3 ) * ( xo-x3 ) + ( yo-y3 ) * ( x3-x2 ) )/det
   l2 = ( ( y3-y1 ) * ( xo-x3 ) + ( yo-y3 ) * ( x1-x3 ) )/det

   return l1, l2, 1.0 - l2 - l1

def getDistancePointToLine( (xo,yo),(x1,y1),(x2,y2) ):

   c2 = ( (x2-x1)*(x2-x1) + (y2-y1)*(y2-y1) )
   det = ( x2-x1 )*( y1-yo ) - ( x1-xo )*( y2-y1 )

   return abs(det) / math.sqrt(c2)

def getTriangleArea( (x1,y1),(x2,y2),(x3,y3) ):
   # half the vector product
   return 0.5 * math.abs( ( x2-x1 )*( y3-y1 ) - ( x3-x1 )*( y2-y1 ) )

def getConeSinAngle( (x1,y1),(x2,y2),(x3,y3) ):
   # S = ac.sin(B)/2 = det / 2
   a2 = ( (x2-x3)*(x2-x3) + (y2-y3)*(y2-y3) )
   c2 = ( (x2-x1)*(x2-x1) + (y2-y1)*(y2-y1) )
   ac = np.sqrt( a2*c2 )
   det = ( x1-x2 )*( y3-y2 ) - ( x3-x2 )*( y1-y2 ) # A to C
   return det / ac

def getConeAngle( (x1,y1),(x2,y2),(x3,y3) ):
   return np.arctan2( y2-y3,x2-x3 ) - np.arctan2( y2-y1,x2-x1 )
   """
   # S = ac.sin(B)/2 = det / 2
   # b2 = a2 + c2 - 2ac.cos(B)
   a2 = ( (x2-x3)*(x2-x3) + (y2-y3)*(y2-y3) )
   b2 = ( (x1-x3)*(x1-x3) + (y1-y3)*(y1-y3) )
   c2 = ( (x2-x1)*(x2-x1) + (y2-y1)*(y2-y1) )
   ac = np.sqrt( a2*c2 )
   det = ( x1-x2 )*( y3-y2 ) - ( x3-x2 )*( y1-y2 ) # A to C
   cosB = 0.5*( a2+c2-b2 ) / ac
   if det > 0: return np.arccos( cosB )
   if det < 0: return  2*np.pi - np.arccos( cosB )
   if cosB < 0: return np.pi
   return 0
   """

def isInsideTriangle( (xo,yo),(x1,y1),(x2,y2),(x3,y3), size=5, nomatter=False ):

   # ~~> Taking sides
   l1 = (xo-x2)*(y1-y2)-(x1-x2)*(yo-y2) < 0.0
   l2 = (xo-x3)*(y2-y3)-(x2-x3)*(yo-y3) < 0.0
   l3 = (xo-x1)*(y3-y1)-(x3-x1)*(yo-y1) < 0.0
   if l1 == l2 == l3:
      return getBarycentricWeights( (xo,yo),(x1,y1),(x2,y2),(x3,y3) )
   if nomatter: return getBarycentricWeights( (xo,yo),(x1,y1),(x2,y2),(x3,y3) )
   return []

   # ~~> Using barycentric weight
   #l1,l2,l3 = getBarycentricWeights( (xo,yo),(x1,y1),(x2,y2),(x3,y3) )
   #accuracy = np.power(10.0, -size+np.floor(np.log10(abs(l1+l2+l3))))
   ##if l1 >= 0.0 and l1 <= 1.0 and l2 >= 0.0 and l2 <= 1.0 and l3 >= 0.0 and l3 <= 1.0 : return [ l1, l2, l3 ]
   #if l1 >= -accuracy and l1 <= 1.0+accuracy and l2 >= -accuracy and l2 <= 1.0+accuracy and l3 >= -accuracy and l3 <= 1.0+accuracy : return [ l1, l2, l3 ]
   #if nomatter: return [ l1,l2,l3 ]
   #return []

def isInsidePoly( (xo,yo), poly, close=True ):
# ... by the "Ray Casting Method".
   inside = False
   p1 = poly[0]
   for j in range(len(poly)+1):
      p2 = poly[j%len(poly)]
      if yo >= min(p1[1],p2[1]):
         if yo <= max(p1[1],p2[1]):
            if xo <= max(p1[0],p2[0]):
               if p1[1] != p2[1]: xints = (yo-p1[1])*(p2[0]-p1[0])/(p2[1]-p1[1])+p1[0]
               if p1[0] == p2[0] or xo <= xints: inside = not inside
      p1 = p2
   if close:
      for p1 in poly:
         if isClose( [xo,yo],p1,size=10 ): inside = True
   return inside

def isClose( p1,p2,size=5 ):

   if ( p2 == [] or p1 == [] ): return False
   s = 1.e-5 + abs(max(p1)+max(p2))
   accuracy = np.power(10.0, -size+np.floor(np.log10(s)))

   return getNorm2( p1[0:2],p2[0:2] ) < accuracy

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
