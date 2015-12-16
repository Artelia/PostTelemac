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
"""@brief
         Various method to parse strings into values, arrays, etc.
         Arrays are converted to numpy arrays
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import re
import sys
import numpy as np

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#
"""@brief This will parse pairs of values from a string and
   convert it into a numpy array.
   - Paires are surounded by square bracketes.
   - Paires are joined up with ';'
   @examples: [10;1][0;1]
"""
sqr_brack = re.compile(r'[,;]?\s*?\[(?P<brack>[\d;.\s+-dDeE]*?)\]',re.I)
# (\+|\-)? to capture the sign if there ... different from the parserFORTRAN version
var_doublep = re.compile(r'(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))',re.I)
var_integer = re.compile(r'(?P<number>(\+|\-)?(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))',re.I)

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
            print '... could not parse the array: ' + s
            sys.exit()
      z.append(p)

   return np.array(z)

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$15-Nov-2011 08:51:29$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit()
