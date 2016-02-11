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
"""@history 15/11/2011 -- Sebastien E. Bourban
"""
"""@history 25/08/2013 -- Sebastien E. Bourban and Juliette C. Parisi
      Complete re-work of the definition of points and frames:
      - points can include 3D points with vairous vertical references to planes
      - frames can include ranges
      These are mainly used to parse the keys "extract" and "time" set in the
         XML files for the validation or the extraction of data.
"""
"""@history 23/09/2014 -- Sebastien E. Bourban
      parseArrayGrid has been split to include both 2D and 3D grids
"""
"""@brief
         Various method to parse strings into values, arrays, etc.
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import re
import sys
from fractions import gcd

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

rng2d = re.compile(r'(?P<n>[\d:+-]+)',re.I)
nod2d = re.compile(r'(?P<n>\d+)',re.I)
pnt2d = re.compile(r'\((?P<n>[^\(\)]+?)\)',re.I)
spl2d = re.compile(r'\{(?P<n>[^\(\)]+?)\}',re.I)

empty = re.compile(r'[\(\[][\)\]]',re.I)
plans = re.compile(r'\[(?P<n>[\d;,]+?)\]',re.I)
numbr = re.compile(r'(?P<n>[\d.+-dDeE]+?)')

simple = re.compile(r'(?P<n>([\d:+-]+|\([\d.+-dDeE]+?\)))')
complx = re.compile(r'(?P<n>(\d+|\{[\d.+-dDeE]+?[;,][\d.+-dDeE]+?\}|\([\d.+-dDeE]+?[;,][\d.+-dDeE]+?\)|[\[\(][\]\)])((?=[^#@])|[#@][\[\(].+?[\]\)]|[#@][^,;\[\(\)\]]+))',re.I)

squote = re.compile(r"(?P<squot>'.*?')") #,re.I)
dquote = re.compile(r'(?P<dquot>".*?")') #,re.I)

#gridxyn = re.compile(r'\((?P<minx>[\d.+-dDeE]+?)[;,](?P<miny>[\d.+-dDeE]+?)\)\((?P<maxx>[\d.+-dDeE]+?)[;,](?P<maxy>[\d.+-dDeE]+?)\)\{(?P<nx>\d+?)[;,](?P<ny>\d+?)\}',re.I)

# _____                       ______________________________________
# ____/ General Time Jumping /_____________________________________/
#

def parseArrayFrame(s,size=-1):
   """
   @brief     Decoding structure all in order
      The list of frames is delimiting points either by ',' or ';',
         and the ranges by ':'
      The output is an arry [..]. Each term is either:
         (a) an integer, representing a frame or a node or a plane for instance
         (b) a 1D-tuple of a real value, representing a time or a depth
         (c) a 3D-tuple of integers, representing an array range [0;-1;1] by default
   @examples of input / output
      '5'         =>  [5]
      '[4]'       =>  [4]
      '[5,6,7,0]' =>  [5, 6, 7, 0]
      '(5.6)'     =>  [(5.6,)]
      '(76);(4),[(3.3);4:14:2;0:6;8]'
                  =>  [(76.0,), (4.0,), (3.3,), (4, 14, 2), (0, 6, 1), 8]
   """
   frames = []

   # ~~ Special deal of all times ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if s == '[]':
      if size >= 0: return [ range(size) ]
      else: return [ [0,-1,1] ]

   # ~~ Identify individual frames ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for node in re.findall(simple,s+','):

      # ~~> Is it a time (t) or a frame / range
      t = node[1]
      proci = re.match(rng2d,t)
      procr = re.match(pnt2d,t)
      if proci:
         rt = proci.group('n').split(':')
         if len(rt) == 1:
            frameA = [ int(rt[0]) ]
            if size >= 0:
               if frameA[0] < 0: frameA[0] = max( 0, size + frameA[0] )
               else: frameA[0] = min( frameA[0], size-1 )
               frameA = range( frameA[0],frameA[0]+1,1 )
         else:
            if len(rt) == 2: frameA = [ int(rt[0]),int(rt[1]),1 ]
            if len(rt) == 3: frameA = [ int(rt[0]),int(rt[1]),int(rt[2]) ]
            if size >= 0:
               if frameA[0] < 0: frameA[0] = max( 0, size + frameA[0] )
               else: frameA[0] = min( frameA[0], size-1 )
               if frameA[1] < 0: frameA[1] = max( 0, size + frameA[1] )
               else: frameA[1] = min( frameA[1], size-1 )
               frameA = range( frameA[0],frameA[1]+1,frameA[2] )
      elif procr: frameA = ( float(procr.group('n')), )
      else:
         print '... could not parse the point <' + node[0] + '> from the string "' + s + '"'
         sys.exit(1)

      # ~~> Final packing
      frames.extend( frameA )

   return frames

# _____                        _____________________________________
# ____/ General Space Jumping /____________________________________/
#

def parseArrayPoint(s,size=-1):
   """
   @brief     Decoding structure all in order
      The list of frames is delimiting points either by ',' or ';',
         and the ranges by ':'
      The output is an arry [..]. Each term is complicated ...
   @examples of input / output
      '5'  =>  [(5, [(0, -1, 1)])]    # either a 2D node value or a vertical 1D profile covering all planes above the 2D node
      '(5)' =>  [(5, [(0, -1, 1)])]
      '9@2,58#3,18,4#1,4#1,76@0.e-3,8@0.5'
         =>  [(9, ([2.0, -1],)), (58, [3]), (18, [(0, -1, 1)]), (4, [1]), (4, [1]), (76, ([0.0, -1],)), (8, ([0.5, -1],))]
      '(4,5,6),[]#900'
         =>  [((4.0, 5.0, 6.0), [(0, -1, 1)]), ([], [900])]
      '(3;4,5)#[]'
         =>  [(3, [(0, -1, 1)]), (4, [(0, -1, 1)]), (5, [(0, -1, 1)])
      '(4;5,6)#[5:4;6;0:-1:2]'
         =>  [((4.0, 5.0, 6.0), [(5, 4, 1), 6, (0, -1, 2)])]
      '9@2,58#3,18,(4;7)#1,4#1,(76;4)@1.e-1,[8@(0.5;0.7)'
         =>  [(9, ([2.0, -1],)), (58, [3]), (18, [(0, -1, 1)]), ((4.0, 7.0), [1]), (4, [1]), ((76.0, 4.0), ([0.1, -1],)), (8, ([0.5, -1],[0.7, -1]))]
      '(4;5,6)#[5;6]'
         =>  [((4.0, 5.0, 6.0), [5, 6])]
      '(4;5,6)@(-5#3;6)'
         =>  [((4.0, 5.0, 6.0), ([-5.0, 3], [6.0, -1]))]
   """

   points = []

   # ~~ Special deal of all points ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if s == '':
      if size >= 0: return [ ( [],range(size) ) ]
      else: return [ ([],[0]) ]

   # ~~ Identify individual points ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for node in re.findall(complx,s+','):

      # ~~> Is it a point (x,y) or a node n
      xy = node[1]
      proci = re.match(nod2d,xy)
      procs = re.match(spl2d,xy)
      procr = re.match(pnt2d,xy)
      proce = re.match(empty,xy)
      if proci: pointA = int(proci.group('n'))
      elif procr:
         xy = procr.group('n').replace(',',';').split(';')
         if len(xy) == 2: pointA = ( float(xy[0]),float(xy[1]) )
         #if len(xy) == 3: pointA = ( float(xy[0]),float(xy[1]),float(xy[2]) )
         if len(xy) != 2:
            print '... we are not allowing anything anything but a pair (x,y). You have: <' + node[0] + '>from the string "' + s + '"'
            print '   +> if you need (x,y,z) you should use a depth above plan 0: (x,y)@z#0'
            sys.exit(1)
      elif proce:
         pointA = []
      elif procs:
         xy = procs.group('n').replace(',',';').split(';')
         if len(xy) == 2: pointA = ( int(xy[0]),int(xy[1]) )
         elif len(xy) == 3: pointA = ( int(xy[0]),int(xy[1]),int(xy[2]) )
         else:
            print '... could not parse the number of re-sampling steps. You have: <' + node[0] + '>from the string "' + s + '"'
            sys.exit(1)
         points.append( pointA )
         continue
      else:
         print '... could not parse the point <' + node[0] + '> from the string "' + s + '"'
         sys.exit(1)

      # ~~> Is it a depth d or a plane p or both
      pointB = []
      if node[2] != '':
         tp = node[2][0]
         zp = node[2][1:]
         if tp == '#':      # this is a plane or a series of planes
            proci = re.match(rng2d,zp)
            if proci: zp = '['+zp+']'
            pointB = parseArrayFrame(zp,size)
         if tp == '@':      # this is a depth or a series of depth, referenced by planes
            procr = re.match(numbr,zp)
            if procr: zp = '('+zp+')'
            procp = re.match(pnt2d,zp)
            if procp:
               pointB = []
               for p in procp.group('n').replace(',',';').split(';'):
                 if '#' in p:
                    a,b = p.split('#')
                    pointB.append( [float(a),int(b)] )
                 else:
                    pointB.append( [float(p),-1] )    # from the surface plane by default
               pointB = tuple(pointB)
      else:
         if size >= 0: pointB = range(size)
         else: pointB = [0,-1,1]

      # ~~> Final packing
      points.append( ( pointA,pointB) )

   return points

def parseArrayGrid(s,size):
   """
   @brief     Decoding structure all in order
      The grid is defined by two points and an array of re-sampling steps
      The input 'size' is either:
         - in 2D a pair of 2D points ( bottom-left, top-right )
         - in 3D a pair of 2D points and a range of planes
      The input 'size' is a pair of complex points (2D or 3D) and
         a set of re-sampling numbers
      The output is an arry [..]. Each term is complicated ...
   """

   grids = []
   minz = 0.; maxz = 0.
   minp = 0; maxp = 0
   
   if len(size) == 3: (minx,miny),(maxx,maxy),(minp,maxp) = size
   elif len(size) == 2:
      if len(size[0]) == 2: (minx,miny),(maxx,maxy) = size
      else: (minx,miny,minz),(maxx,maxy,maxz) = size
   nz = maxp - minp

   # ~~ Special deal of all points ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if s == '[]':
      dist = ( maxy-miny+maxx-minx )/20.0  # arbitrary value of 20 points
      dist = min( dist, maxx-minx )
      dist = min( dist, maxy-miny )
      xo = ( maxx+minx )/2.0
      yo = ( maxy+miny )/2.0
      nx = max( 2,int( ( maxx-minx )/dist ) )
      ny = max( 2,int( ( maxy-miny )/dist ) )
      dist = min( dist, (maxx-minx)/(1.0*nx) )
      dist = min( dist, (maxy-miny)/(1.0*ny) )
      if len(size) == 2 and len(size[0]) == 2:
         return [ [ ( xo-nx*dist/2.0,yo-ny*dist/2.0 ),( xo+nx*dist/2.0,yo+ny*dist/2.0 ),[nx,ny] ] ]
      elif len(size) == 2 and len(size[0]) == 3: #TODO: make sure you can suport this option
         zo = ( maxz+minz )/2.0
         nz = 10
         dizt = ( maxx-minx )/(1.0*nz)  # arbitrary value of 10 points
         return [ [ ( xo-nx*dist/2.0,yo-ny*dist/2.0,zo-nz*dizt/2.0 ),( xo+nx*dist/2.0,yo+ny*dist/2.0,zo+nz*dizt/2.0 ),[nx,ny,nz] ] ]
      else:
         return [ [ ( xo-nx*dist/2.0,yo-ny*dist/2.0 ),( xo+nx*dist/2.0,yo+ny*dist/2.0 ),range(minp,maxp),[nx,ny,nz] ] ]

   # ~~ Decoding of user entrance ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   s2g = parseArrayPoint(s)
   if gcd(len(s2g),3) != 3:
      print '... could not parse your grid . "' + s + '". It should be triplets made of 2 points (;)(;) and an array of resampling steps {;}.'
      sys.exit(1)
   for i in range(len(s2g)/3):
      pta,ptb,np = s2g[3*i:3*(i+1)]
      if len(np) == 2: grids.append([ pta[0],ptb[0],np ])
      elif len(np) == 3: #TODO: support a range of fixed depths as well as fixed planes
         zp = '['+str(pta[1][0])+':'+str(ptb[1][0])+']'
         grids.append([ pta[0],ptb[0],parseArrayFrame(zp,nz),np ])

   return grids

def parseArrayPaires(s):

   paires = []

   # ~~ Special deal of all paires ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if s == '': return []

   # ~~ Identify individual paires ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for node in re.findall(complx,s+','):

      # ~~> Is it a point (x,y) or a node n
      xy = node[1]
      proci = re.match(nod2d,xy)
      procr = re.match(pnt2d,xy)
      proce = re.match(empty,xy)
      if proci: pointA = int(proci.group('n'))
      elif procr:
         xy = procr.group('n').replace(',',';').split(';')
         if len(xy) == 2: pointA = ( float(xy[0]),float(xy[1]) )
         #if len(xy) == 3: pointA = ( float(xy[0]),float(xy[1]),float(xy[2]) )
         if len(xy) != 2:
            print '... we are not allowing anything anything but a pair (x,y). You have: <' + node[0] + '>from the string "' + s + '"'
            print '   +> if you need (x,y,z) you should use a depth above plan 0: (x,y)@z#0'
            sys.exit(1)
      elif proce:
         pointA = []
      else:
         print '... could not parse the point <' + node[0] + '> from the string "' + s + '"'
         sys.exit(1)

      # ~~> Final packing
      paires.append( pointA )

   return paires

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$15-Nov-2011 08:51:29$"

if __name__ == "__main__":

   # ~~ space ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if True:    # S.E.Bourban completed testing on August 25, 2013
      print '\n\n'
      strings = [ '5','9@2,58#3,18,4#1,4#1,76@0.e-3,8@0.5','(4,5,6),[]#900', '(3;4,5)#[]', '(4;5,6)#[5:4;6;0:-1:2]', \
         '(5)','9@2,58#3,18,(4;7)#1,4#1,(76;4)@1.e-1,[8@(0.5;0.7)','(4;5,6)#[5;6]','(4;5,6)@(-5#3;6)' ]
      for s in strings: print s,' => ',parseArrayPoint(s)

   # ~~ time ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if True:   # S.E.Bourban completed testing on August 25, 2013
      print '\n\n'
      strings = [ '5','[4]','[5,6,7,0]', \
         '(5.6)','(76);(4),[(3.3);4:14:2;0:6;8]' ]
      for s in strings: print s,' => ',parseArrayFrame(s)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)

"""
This will parse pairs of values from a string and
   convert it into a numpy array.
   - Paires are surounded by square bracketes.
   - Paires are joined up with ';'
   @examples: [10;1][0;1]

sqr_brack = re.compile(r'[,;]?\s*?\[(?P<brack>[\d;.\s+-dDeEpz]*?)\]',re.I)
# (\+|\-)? to capture the sign if there ... different from the parserFORTRAN version
var_doublep = re.compile(r'(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))',re.I)
var_integer = re.compile(r'(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))',re.I)
var_dist = re.compile(r'd(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))',re.I)
var_cote = re.compile(r'z(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))',re.I)
var_plan = re.compile(r'p(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))',re.I)

def parseArrayPaires(s):

   z = []  # /!\ only pairs of points allowed for now
   for brack in re.findall(sqr_brack,s):
      p = []
      for v in brack.split(';'): # /!\ this also work for one value
         proci = re.match(var_integer,v)
         procd = re.match(var_doublep,v)
         if procd:
            p.append(float(procd.group('number')))
         elif proci:
            p.append(int(proci.group('number')))
         else:
            if re.match(var_dist,v) or re.match(var_cote,v) or re.match(var_plan,v): p.append(v)
            else:
               print '... could not parse the array: ' + s
               sys.exit(1)
      z.append(p)

   return z
"""
