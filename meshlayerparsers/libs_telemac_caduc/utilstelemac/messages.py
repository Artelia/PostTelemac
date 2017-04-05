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
import threading
import subprocess as sp
from multiprocessing import Process,cpu_count,active_children
from multiprocessing.sharedctypes import Value,Array

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
               '\n'+'~'*18+'\n'+
               ''.join(traceback.format_exception(*sys.exc_info()))+
               '~'*18}
            if 'name' in d: cd['name'] = d['name']+':\n      '+cd['name']
            if 'msg' in d: cd['msg'] = d['msg']+':\n      '+cd['msg']
         if bypass: return cd
         print reprMessage([cd])
         sys.exit(1)
      elif type(e.args) == type([]):
         message = []
         for i in e.args: message.append(i)
         cd.update({'tree':message})
         print cd     #\
         sys.exit(1)   # > This should never happend
         return cd    #/
      else:
         cd.update({'tree':[repr(e.args)]})
         print cd     #\
         sys.exit(1)   # > This should never happend
         return cd    #/
   # ~~> case without
   else:
      if type(d) == type({}):
         if bypass: return d.copy()
         print reprMessage([d])
         sys.exit(1)
      else:
         cd = {'name':'uncontroled error from python:','msg':repr(d)}
         print cd    #\
         sys.exit(1)  # > This should never happend or maybe ?
         return cd   #/

def reprMessage(items):
   message = []
   for item in items:
      if type(item) == type({}):
         mi = item['name'] + ':'
         if 'msg' in item: mi = mi + ' ' + item['msg']
         if 'tree' in item:
            me = reprMessage(item['tree'])
            mi = mi + '\n   |' + '\n   |'.join(me.split('\n'))
         message.append(mi)
      else:
         print items      #\
         sys.exit(1)       # > This should not happend
   return '\n'.join(message)

# _____                  ___________________________________________
# ____/ Primary Classes /__________________________________________/
#

class MESSAGES:

   def __init__(self,size=0,ncsize=0):
      self.messages = []
      self.tail = ''
      self.size = size
      self.ncsize = ncsize
      if ncsize == 0: self.ncsize = cpu_count()

   def addMessages(self,ms):
      for item in ms: self.messages.append(item)  # because of tuple to array

   def exceptMessages(self):
      return reprMessage(self.messages)

   def notEmpty(self):
      return ( self.messages != [] )

   def startCmd(self,tasks,args,memo):
      # ~~> prevents from overloading your system
      while len(active_children()) >= self.ncsize: continue
      # ~~> subcontract the task out
      task = paraProcess(self.runCmd,args)
      # ~~> update the log pile
      tasks.append([task,args,memo])
      # ~~> order the work
      task.start()
      # ~~> return to high grounds
      return task

   def flushCmd(self,tasks):
      messages = []
      while tasks != []:
         task,(exe,bp,tail,code),memo = tasks.pop(-1)
         task.join()
         if tail.value.strip() != '':
            self.clearCmd(tasks)
         messages.append([exe,'',tail.value.strip(),code.value,memo])
      return messages

   def cleanCmd(self,tasks):
      i = len(tasks)
      messages = []
      while 0 < i:
         task,(exe,bp,tail,code),memo = tasks[i-1]
         if not task.is_alive():
            tasks.pop(i-1)
            task.join()
            if tail.value.strip() != '':
               messages.append([exe,'',tail.value.strip(),code.value,memo])
               self.clearCmd(tasks)
               break
            else:
               messages.append([exe,'','',code.value,memo])
         i -= 1
      return messages

   def clearCmd(self,tasks):
      while tasks != []:
         task,(exe,bp,tail,code),memo = tasks.pop()
         task.terminate()

   def runCmd(self,exe,bypass,tail=Array('c',' '*10000),code=Value('i',0)):
      if bypass:
         proc = sp.Popen(exe,bufsize=1024,stdout=sp.PIPE,stderr=sp.PIPE,shell=True)
         t1 = threading.Thread(target=self.bufferScreen,args=(proc.stdout,))
         t1.start()
         t1.join()
         proc.wait()
         code.value = proc.returncode
         if code.value != 0 and tail.value.strip() == '':
            tail.value = 'I was only able to capture the following execution error while executing the following:\n'+exe+'\n... you may wish to re-run without bypass option.'+ \
               '\n'+'~'*18+'\n'+str(proc.stderr.read().strip())+'\n'+'~'*18
            self.tail = self.tail + '\n' + tail.value
      else:
         code.value = sp.call(exe,shell=True)
         if code.value != 0:
            tail.value = '... The following command failed for the reason above (or below)\n'+exe+'\n'
            self.tail = self.tail + '\n' + tail.value
      return self.tail,code.value

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

# _____                     ________________________________________
# ____/ Parallel Utilities /_______________________________________/
#

class paraProcess(Process):

   def __init__(self,fct,args):
      Process.__init__(self)
      self.fct = fct
      self.args = args

   def run(self): self.fct(*self.args)

# _____                  ___________________________________________
# ____/ Other Utilities /__________________________________________/
#

def banner(text,size=1):

   l = LETTERS(size)
   return l.render(text)


class LETTERS:

   def __init__(self,size=1):

      self.size = size         # only one size supported for now
      self.ascii = {}
      for i in range(126-31):  # 95 characters of the ASCII set are supported from char 32
         self.ascii.update({i+32:[chr(i+32),'']})

      # ~~> character set inspired from Glenn Chappell
      self.ascii[32][1]   = ['  ','  ','  ','  ','  ','  ','  ','  ']                                                                           #>  single space
      self.ascii[33][1]   = ['  _ ',' | |',' | |',' | |',' |_|',' (_)','    ','    ']                                                           #>  !
      self.ascii[34][1]   = ['  _ _ ',' ( | )','  V V ','      ','      ','      ','      ','      ']                                           #>  "
      self.ascii[35][1]   = ['    _  _   ','  _| || |_ ',' |_  __  _|','  _| || |_ ',' |_  __  _|','   |_||_|  ','           ','           ']   #>  #
      self.ascii[36][1]   = ['   _  ','  | | ',' / __)',' \\__ \\',' (   /','  |_| ','      ','      ']                                         #>  $
      self.ascii[37][1]   = ['  _   __',' (_) / /','    / / ','   / /  ','  / / _ ',' /_/ (_)','        ','        ']                           #>  %
      self.ascii[38][1]   = ['         ','   ___   ','  ( _ )  ','  / _ \\/\\',' | (_>  <','  \\___/\\/','         ','         ']               #>  &
      self.ascii[39][1]   = ['  _ ',' ( )',' |/ ','    ','    ','    ','    ','    ']                                                           #>  '
      self.ascii[40][1]   = ['   __','  / /',' | | ',' | | ',' | | ',' | | ','  \\_\\','       ']                                               #>  (
      self.ascii[41][1]   = [' __  ',' \\ \\ ','  | |','  | |','  | |','  | |',' /_/ ','     ']                                                 #>  )
      self.ascii[42][1]   = ['     _    ','  /\\| |/\\ ','  \\ ` \' / ',' |_     _|','  / , . \\ ','  \\/|_|\\/ ','          ','          ']    #>  *
      self.ascii[43][1]   = ['        ','    _   ','  _| |_ ',' |_   _|','   |_|  ','        ','        ','        ']                           #>  +
      self.ascii[44][1]   = ['    ','    ','    ','    ','  _ ',' ( )',' |/ ','    ']                                                           #>  ,
      self.ascii[45][1]   = ['         ','         ','  ______ ',' |______|','         ','         ','         ','         ']                   #>  -
      self.ascii[46][1]   = ['    ','    ','    ','    ','  _ ',' (_)','    ','    ']                                                           #>  .
      self.ascii[47][1]   = ['      __','     / /','    / / ','   / /  ','  / /   ',' /_/    ','        ','        ']                           #>  /
      self.ascii[48][1]   = ['   ___  ','  / _ \ ',' | | | |',' | | | |',' | |_| |','  \___/ ','        ','        ']                           #>  0
      self.ascii[49][1]   = ['  __ ',' /_ |','  | |','  | |','  | |','  |_|','     ','     ']                                                   #>  1
      self.ascii[50][1]   = ['  ___  ',' |__ \ ','    ) |','   / / ','  / /_ ',' |____|','       ','       ']                                   #>  2
      self.ascii[51][1]   = ['  ____  ',' |___ \ ','   __) |','  |__ < ','  ___) |',' |____/ ','        ','        ']                           #>  3
      self.ascii[52][1]   = ['  _  _   ',' | || |  ',' | || |_ ',' |__   _|','    | |  ','    |_|  ','         ','         ']                   #>  4
      self.ascii[53][1]   = ['  _____ ',' | ____|',' | |__  ',' |___ \ ','  ___) |',' |____/ ','        ','        ']                           #>  5
      self.ascii[54][1]   = ['    __  ','   / /  ','  / /_  ',' | \'_ \\ ',' | (_) |','  \\___/ ','        ','        ']                        #>  6
      self.ascii[55][1]   = ['  _____ ',' |___  |','   _/ / ','  |_ _| ','   / /  ','  /_/   ','        ','        ']                           #>  7
      self.ascii[56][1]   = ['   ___  ','  / _ \ ',' | (_) |','  > _ < ',' | (_) |','  \___/ ','        ','        ']                           #>  8
      self.ascii[57][1]   = ['   ___  ','  / _ \ ',' | (_) |','  \__, |','    / / ','   /_/  ','        ','        ']                           #>  9
      self.ascii[58][1]   = ['    ','  _ ',' (_)','    ','  _ ',' (_)','    ','    ']                                                           #>  :
      self.ascii[59][1]   = ['    ','  _ ',' (_)','    ','  _ ',' ( )',' |/ ','    ']                                                           #>  ;
      self.ascii[60][1]   = ['    __','   / /','  / / ',' < <  ','  \\ \\ ','   \\_\\','      ','      ']                                       #>  <
      self.ascii[61][1]   = ['         ','  ______ ',' |______|','  ______ ',' |______|','         ','         ','         ']                   #>  =
      self.ascii[62][1]   = [' __   ',' \\ \\  ','  \\ \\ ','   > >','  / / ',' /_/  ','      ','      ']                                       #>  >
      self.ascii[63][1]   = ['  ___  ',' |__ \ ','    ) |','   / / ','  |_|  ','  (_)  ','       ','       ']                                   #>  ?
      self.ascii[64][1]   = ['          ','    ____  ','   / __ \\ ','  / / _` |',' | | (_| |','  \\ \\__,_|','   \\____/ ','          ']       #>  @
      self.ascii[65][1]   = ['           ','     /\\    ','    /  \\   ','   / /\\ \\  ','  / ____ \\ ',' /_/    \\_\\','           ','           ']  #>  A
      self.ascii[66][1]   = ['  ____  ',' |  _ \\ ',' | |_) |',' |  _ < ',' | |_) |',' |____/ ','        ','        ']                          #>  B
      self.ascii[67][1]   = ['   _____ ','  / ____|',' | |     ',' | |     ',' | |____ ','  \\_____|','         ','         ']                  #>  C
      self.ascii[68][1]   = ['  _____  ',' |  __ \\ ',' | |  | |',' | |  | |',' | |__| |',' |_____/ ','         ','         ']                  #>  D
      self.ascii[69][1]   = ['  ______ ',' |  ____|',' | |__   ',' |  __|  ',' | |____ ',' |______|','         ','         ']                   #>  E
      self.ascii[70][1]   = ['  ______ ',' |  ____|',' | |__   ',' |  __|  ',' | |     ',' |_|     ','         ','         ']                   #>  F
      self.ascii[71][1]   = ['   _____ ','  / ____|',' | |  __ ',' | | |_ |',' | |__| |','  \\_____|','         ','         ']                  #>  G
      self.ascii[72][1]   = ['  _    _ ',' | |  | |',' | |__| |',' |  __  |',' | |  | |',' |_|  |_|','         ','         ']                   #>  H
      self.ascii[73][1]   = ['  _____ ',' |_   _|','   | |  ','   | |  ','  _| |_ ',' |_____|','        ','        ']                           #>  I
      self.ascii[74][1]   = ['       _ ','      | |','      | |','  _   | |',' | |__| |','  \\____/ ','         ','         ']                  #>  J
      self.ascii[75][1]   = ['  _  __',' | |/ /',' | \' / ',' |  <  ',' | . \\ ',' |_|\\_\\','       ','       ']                               #>  K
      self.ascii[76][1]   = ['  _      ',' | |     ',' | |     ',' | |     ',' | |____ ',' |______|','         ','         ']                   #>  L
      self.ascii[77][1]   = ['  __  __ ',' |  \\/  |',' | \\  / |',' | |\\/| |',' | |  | |',' |_|  |_|','         ','         ']                #>  M
      self.ascii[78][1]   = ['  _   _ ',' | \\ | |',' |  \\| |',' | . ` |',' | |\\  |',' |_| \\_|','        ','        ']                       #>  N
      self.ascii[79][1]   = ['   ____  ','  / __ \\ ',' | |  | |',' | |  | |',' | |__| |','  \\____/ ','         ','         ']                 #>  O
      self.ascii[80][1]   = ['  _____  ',' |  __ \\ ',' | |__) |',' |  ___/ ',' | |     ',' |_|     ','         ','         ']                  #>  P
      self.ascii[81][1]   = ['   ____  ','  / __ \\ ',' | |  | |',' | |  | |',' | |__| |','  \\___\\_\\','         ','         ']               #>  Q
      self.ascii[82][1]   = ['  _____  ',' |  __ \\ ',' | |__) |',' |  _  / ',' | | \\ \\ ',' |_|  \\_\\','         ','         ']              #>  R
      self.ascii[83][1]   = ['   _____ ','  / ____|',' | (___  ','  \\___ \\ ','  ____) |',' |_____/ ','         ','         ']                 #>  S
      self.ascii[84][1]   = ['  _______ ',' |__   __|','    | |   ','    | |   ','    | |   ','    |_|   ','          ','          ']           #>  T
      self.ascii[85][1]   = ['  _    _ ',' | |  | |',' | |  | |',' | |  | |',' | |__| |','  \\____/ ','         ','         ']                  #>  U
      self.ascii[86][1]   = [' __     __',' \\ \\   / /','  \\ \\ / / ','   \\ V /  ','    \\ /   ','     V    ','          ','          ']     #>  V
      self.ascii[87][1]   = [' __         __',' \\ \\   _   / /','  \\ \\ / \\ / / ','   \\ V _ V /  ','    \ / \ /   ','     V   V    ','              ','            ']  #>  W
      self.ascii[88][1]   = [' __   __',' \\ \\ / /','  \\ V / ','   > <  ','  / . \\ ',' /_/ \\_\\','        ','        ']                    #>  X
      self.ascii[89][1]   = [' __     __',' \\ \\   / /','  \\ \\_/ / ','   \\   /  ','    | |   ','    |_|   ','          ','          ']      #>  Y
      self.ascii[90][1]   = ['  ______',' |___  /','    / / ','   / /  ','  / /__ ',' /_____|','        ','        ']                           #>  Z
      self.ascii[91][1]   = ['  ___ ',' |  _|',' | |  ',' | |  ',' | |  ',' | |_ ',' |___|','      ']                                           #>  [
      self.ascii[92][1]   = [' __     ',' \\ \\    ','  \\ \\   ','   \\ \\  ','    \\ \\ ','     \\_\\','        ','        ']                 #>  \
      self.ascii[93][1]   = ['  ___ ',' |_  |','   | |','   | |','   | |','  _| |',' |___|','      ']                                           #>  ]
      self.ascii[94][1]   = ['  /\\ ',' |/\\|','     ','     ','     ','     ','     ','     ']                                                 #>  ^
      self.ascii[95][1]   = ['         ','         ','         ','         ','         ','         ','  ______ ',' |______|']                   #>  _
      self.ascii[96][1]   = ['  _ ',' ( )','  \\|','    ','    ','    ','    ','    ']                                                          #>  `
      self.ascii[97][1]   = ['        ','        ','   __ _ ','  / _` |',' | (_| |','  \\__,_|','        ','        ']                          #>  a
      self.ascii[98][1]   = ['  _     ',' | |    ',' | |__  ',' | \'_ \\ ',' | |_) |',' |_.__/ ','        ','        ']                         #>  b
      self.ascii[99][1]   = ['       ','       ','   ___ ','  / __|',' | (__ ','  \\___|','       ','       ']                                  #>  c
      self.ascii[100][1]  = ['      _ ','     | |','   __| |','  / _` |',' | (_| |','  \\__,_|','        ','        ']                          #>  d
      self.ascii[101][1]  = ['       ','       ','   ___ ','  / _ \\',' |  __/','  \\___|','       ','       ']                                 #>  e
      self.ascii[102][1]  = ['   __ ','  / _|',' | |_ ',' |  _|',' | |  ',' |_|  ','      ','      ']                                           #>  f
      self.ascii[103][1]  = ['        ','        ','   __ _ ','  / _` |',' | (_| |','  \\__, |','   __/ |','  |___/ ']                          #>  g
      self.ascii[104][1]  = ['  _     ',' | |    ',' | |__  ',' | \'_ \\ ',' | | | |',' |_| |_|','        ','        ']                         #>  h
      self.ascii[105][1]  = ['  _ ',' (_)','  _ ',' | |',' | |',' |_|','    ','    ']                                                           #>  i
      self.ascii[106][1]  = ['    _ ','   (_)','    _ ','   | |','   | |','   | |','  _/ |',' |__/ ']                                           #>  j
      self.ascii[107][1]  = ['  _    ',' | |   ',' | | __',' | |/ /',' |   < ',' |_|\\_\\','       ','       ']                                 #>  k
      self.ascii[108][1]  = ['  _ ',' | |',' | |',' | |',' | |',' |_|','    ','    ']                                                           #>  l
      self.ascii[109][1]  = ['            ','            ','  _ __ ___  ',' | \'_ ` _ \\ ',' | | | | | |',' |_| |_| |_|','            ','            ']    #>  m
      self.ascii[110][1]  = ['        ','        ','  _ __  ',' | \'_ \\ ',' | | | |',' |_| |_|','        ','        ']                         #>  n
      self.ascii[111][1]  = ['        ','        ','   ___  ','  / _ \\ ',' | (_) |','  \\___/ ','        ','        ']                         #>  o
      self.ascii[112][1]  = ['        ','        ','  _ __  ',' | \'_ \\ ',' | |_) |',' | .__/ ',' | |    ',' |_|    ']                         #>  p
      self.ascii[113][1]  = ['        ','        ','   __ _ ','  / _` |',' | (_| |','  \\__, |','     | |','     |_|']                          #>  q
      self.ascii[114][1]  = ['       ','       ','  _ __ ',' | \'__|',' | |   ',' |_|   ','       ','       ']                                  #>  r
      self.ascii[115][1]  = ['      ','      ','  ___ ',' / __|',' \\__ \\',' |___/','      ','      ']                                         #>  s
      self.ascii[116][1]  = ['  _   ',' | |  ',' | |_ ',' | __|',' | |_ ','  \\__|','      ','      ']                                          #>  t
      self.ascii[117][1]  = ['        ','        ','  _   _ ',' | | | |',' | |_| |','  \\__,_|','        ','        ']                          #>  u
      self.ascii[118][1]  = ['        ','        ',' __   __',' \\ \\ / /','  \\ V / ','   \\_/  ','        ','        ']                       #>  v
      self.ascii[119][1]  = ['           ','           ',' __      __',' \\ \\ /\\ / /','  \\ V  V / ','   \\_/\\_/  ','           ','           ']       #>  w
      self.ascii[120][1]  = ['       ','       ',' __  __',' \\ \\/ /','  >  < ',' /_/\\_\\','       ','       ']                               #>  x
      self.ascii[121][1]  = ['        ','        ','  _   _ ',' | | | |',' | |_| |','  \\__, |','   __/ |','  |___/ ']                          #>  y
      self.ascii[122][1]  = ['      ','      ','  ____',' |_  /','  / / ',' /___|','      ','      ']                                           #>  z
      self.ascii[123][1]  = ['   __','  / /','  | |',' / / ',' \\ \\ ','  | |','  \\_\\','     ']                                               #>  {
      self.ascii[124][1]  = ['  _ ',' | |',' | |',' | |',' | |',' | |',' | |',' |_|']                                                           #>  |
      self.ascii[125][1]  = [' __  ',' \\ \\ ',' | | ','  \\ \\','  / /',' | | ',' /_/ ','     ']                                               #>  }
      self.ascii[126][1]  = ['      ','      ','      ','  /\\/|',' |/\\/ ','      ','      ','      ']                                         #>  ~

      # ~~> print the ASCII character set one character at a time
      #for i in self.ascii: print '\n'+str(i)+' -> '+self.ascii[i][0]+'\n'+'\n'.join(self.ascii[i][size])
      # ~~> print the ASCII character on one line
      #lines = self.ascii[32][size]
      #for i in self.ascii:
      #   for j in range(len(self.ascii[i][size])): lines[j] += self.ascii[i][size][j]
      #print '\n'.join(lines)

   def render(self,text):
      lines = [ ' ' for i in self.ascii[32][self.size] ]
      for c in range(len(text)):
         i = ord(text[c])
         for j in range(len(self.ascii[i][self.size])): lines[j] += self.ascii[i][self.size][j][1:]
      return lines

