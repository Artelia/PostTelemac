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
"""@history 05/06/2012 -- Sebastien E. Bourban
      First draft
"""
"""@history 18/06/2012 -- Sebastien E. Bourban
      Final solution for the first implementation of the utility.
      Calls to sys.exit() and os.system() have been progressively captured
         into a try/except statement to better manage errors.
      This, however, assumes that all errors are anticipated.
"""
"""@history 05/12/2012 -- Sebastien E. Bourban
   Addition of a better capture of errors, particularly when the error is
      not thrown through runCmd.
"""
"""@brief
      Catching and reporting on sys.exit / os.system errors
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
import traceback
import os
import threading
from subprocess import *

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def filterMessage(d,e=None,bypass=True):
   # ~~> case with an exception
   if e != None:
      cd = d.copy()   # assumes d is a dict and e is an Exception
      if type(e.args) == type(()):
         message = []
         if type(e.args[0]) == type([]):
            for i in e.args: message.extend(i)
            cd.update({'tree':message})
         elif type(e.args[0]) == type({}):
            for i in e.args: message.append(i)
            cd.update({'tree':message})
         else:
            cd = {'name':'uncontroled error from python:','msg':repr(e)+ 
               '\n~~~~~~~~~~~~~~~~~~\n'+
               ''.join(traceback.format_exception(*sys.exc_info()))+
               '~~~~~~~~~~~~~~~~~~'}
            if d.has_key('name'): cd['name'] = d['name']+':\n      '+cd['name']
            if d.has_key('msg'): cd['msg'] = d['msg']+':\n      '+cd['msg']
         if bypass: return cd
         print reprMessage([cd])
         sys.exit()
      elif type(e.args) == type([]):
         message = []
         for i in e.args: message.append(i)
         cd.update({'tree':message})
         print cd     #\
         sys.exit()   # > This should never happend
         return cd    #/
      else:
         cd.update({'tree':[repr(e.args)]})
         print cd     #\
         sys.exit()   # > This should never happend
         return cd    #/
   # ~~> case without
   else:
      if type(d) == type({}):
         if bypass: return d.copy()
         print reprMessage([d])
         sys.exit()
      else:
         cd = {'name':'uncontroled error from python:','msg':repr(d)}
         print cd    #\
         sys.exit()  # > This should never happend or maybe ?
         return cd   #/

def reprMessage(items):
   message = []
   for item in items:
      if type(item) == type({}):
         mi = item['name'] + ':'
         if item.has_key('msg'): mi = mi + ' ' + item['msg']
         if item.has_key('tree'):
            me = reprMessage(item['tree'])
            mi = mi + '\n   |' + '\n   |'.join(me.split('\n'))
         message.append(mi)
      else:
         print items      #\
         sys.exit()       # > This should not happend
   return '\n'.join(message)


# _____                  ___________________________________________
# ____/ Primary Classes /__________________________________________/
#

class MESSAGES:

   def __init__(self,size=0):
      self.messages = []
      self.tail = ''
      self.size = size

   def addMessages(self,ms):
      for item in ms: self.messages.append(item)  # because of tuple to array

   def exceptMessages(self):
      return reprMessage(self.messages)

   def notEmpty(self):
      return ( self.messages != [] )

   def runCmd(self,exe,bypass):
      if bypass:
         proc = Popen(exe,bufsize=1024,stdout=PIPE,stderr=PIPE,shell=True)
         t1 = threading.Thread(target=self.bufferScreen,args=(proc.stdout,))
         t1.start()
         t1.join()
         proc.wait()
         if proc.returncode != 0 and self.tail == '':
            self.tail = 'I was only able to capture the following execution error. You may wish to re-run without bypass option.'+ \
               '\n~~~~~~~~~~~~~~~~~~\n'+str(proc.stderr.read().strip())+'\n~~~~~~~~~~~~~~~~~~'
         return self.tail,proc.returncode
      if os.system(exe):
         print '... The following command failed for the reason above\n'+exe
         sys.exit(1)
      return '',0

   def bufferScreen(self,pipe):
      lastlineempty = False
      for line in iter(pipe.readline,''):
         dat = line.rstrip()
         if (dat == ''):
            if not lastlineempty:
               self.tail = self.tail +'\n'+ dat
               lastlineempty = True
         else:
            lastlineempty = False
            self.tail = self.tail +'\n'+ dat
      if len(self.tail.split('\n')) > self.size: self.tail = '\n'.join((self.tail.split('\n'))[-self.size:]) 
   
