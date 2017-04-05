#!/usr/bin/python
"""@author Nilton Volpato (Nilton.Volpato@gmail.com)
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
"""@history 23/08/2012 -- Fabien Decung:
         Only show bar in terminals by default
         (better for Jenkins console outputs)
"""
"""@history 13/12/2011 -- Sebastien E. Bourban:
         Modifying the good work of Nilton Volpato to apply it to the
         TELEMAC system
"""
"""@history 25/12/2011 -- Sebastien E. Bourban:
         Addin a write method to the ProgressBar class so you can still
         print to screen while moving the progress bar along
"""
"""@brief
         Text progressbar library for python.
"""
"""@details
   This library provides a text mode progressbar. This is tipically used
   to display the progress of a long running operation, providing a
   visual clue that processing is underway.

   The ProgressBar class manages the progress, and the format of the line
   is given by a number of widgets. A widget is an object that may
   display diferently depending on the state of the progress. There are
   three types of widget:
      - a string, which always shows itself (such as "Time(s): ") ;
      - a ProgressBarWidget, which may return a diferent value every time
              it's update method is called (such as "  3%"); and
      - a ProgressBarWidgetHFill, which is like ProgressBarWidget,
              except it expands to fill the remaining width of the line
              (such as "[#####   ]").

   The progressbar module is very easy to use, yet very powerful. And
   automatically supports features like auto-resizing when available.

   Since the progress bar is incredibly customizable you can specify
   different widgets of any type in any order. You can even write your own
   widgets! However, since there are already a good number of widgets you
   should probably play around with them before moving on to create your own
   widgets.
"""
import sys
#import datetime
import time
# The following two are for automatic resize but only work on linux / unix
from array import array
# from fcntl import ioctl
#import termios
import signal
#import math
#import os

#try:
#    from abc import ABCMeta, abstractmethod
#except ImportError:
#    AbstractWidget = object
#    abstractmethod = lambda fn: fn
#else:
#    AbstractWidget = ABCMeta('AbstractWidget', (object,), {})

# FD@EDF : idea taken from Dendright from Clint module
# Only show bar in terminals by default
# (better for Jenkins console outputs, piping, logging etc.)
# However it is said that sys.stderr may not always support .isatty(),
# e.g. when it has been replaced by something that partially implements the File interface
try:
    hide_default = not sys.stderr.isatty()
except AttributeError: # output does not support isatty()
    hide_default = True

class UnknownLength: pass

"""
   This is an element of ProgressBar formatting.
   The ProgressBar object will call it's update value when an update
      is needed. It's size may change between call, but the results will
      not be good if the size changes drastically and repeatedly.
"""
class ProgressBarWidget(object):
   #class Widget(AbstractWidget):
   #TIME_SENSITIVE = False
   #__slots__ = ()
   """
   Returns the string representing the widget.
   The parameter pbar is a reference to the calling ProgressBar,
      where one can access attributes of the class for knowing how
      the update must be made.
   At least this function must be overriden.
   """
   def update(self, pbar): pass
   #@abstractmethod
   #def update(self, pbar): pass

"""
   This is a variable width element of ProgressBar formatting.
   The ProgressBar object will call it's update value, informing the
      width this object must the made. This is like TeX \\hfill, it will
      expand to fill the line. You can use more than one in the same
      line, and they will all have the same width, and together will
      fill the line.
"""
class ProgressBarWidgetHFill(object):
   #class WidgetHFill(Widget):
   """
   Returns the string representing the widget.
   The parameter pbar is a reference to the calling ProgressBar,
      where one can access attributes of the class for knowing how
      the update must be made. The parameter width is the total
      horizontal width the widget must have.

   At least this function must be overriden.
   """
   def update(self, pbar, width): pass
   #@abstractmethod
   #def update(self, pbar, width): pass

"""
   Widget for the Estimated Time of Arrival
"""
class ETA(ProgressBarWidget):
#class ETA(Timer):
#   TIME_SENSITIVE = True

   def format_time(self, seconds):
      return str(int(seconds+1))+'s'
      #return time.strftime('%H:%M:%S', time.localtime(seconds))

   # ~~> Updates the widget to show the ETA or total time when finished.
   def update(self, pbar):
      if pbar.currval == 0: return ' | ---s' #'ETA:  --:--:--'
      elif pbar.finished: return ' | %s' % self.format_time(pbar.seconds_elapsed) #'Time: %s' % self.format_time(pbar.seconds_elapsed)
      else:
         elapsed = pbar.seconds_elapsed
         eta = elapsed * pbar.maxval / pbar.currval - elapsed
         return ' | %s' % self.format_time(eta)
         #return 'ETA:  %s' % self.format_time(eta)

"""
   Widget for showing the transfer speed (useful for file transfers).
"""
class FileTransferSpeed(ProgressBarWidget):
#class FileTransferSpeed(Widget):
#   format = '%6.2f %s%s/s'
#   prefixes = ' kMGTPEZY'
#   __slots__ = ('unit', 'format')

   def __init__(self):
      self.fmt = '%6.2f %s'
      self.units = ['B','K','M','G','T','P']

   # ~~> Updates the widget with the current SI prefixed speed.
   def update(self, pbar):
      if pbar.seconds_elapsed < 2e-6: #or pbar.currval < 2e-6:
         #scaled = power = 0
         bps = 0.0
      else:
         bps = float(pbar.currval) / pbar.seconds_elapsed
         #speed = pbar.currval / pbar.seconds_elapsed
         #power = int(math.log(speed, 1000))
         #scaled = speed / 1000.**power
      spd = bps
      for u in self.units:
         if spd < 1000:
            break
         spd /= 1000

      return self.fmt % (spd, u+'/s')
      #return self.format % (scaled, self.prefixes[power], self.unit)

"""
   A rotating marker for filling the bar of progress.
"""
class RotatingMarker(ProgressBarWidget):
#class RotatingMarker(Widget):
#   __slots__ = ('markers', 'curmark')
    
   def __init__(self, markers='|/-\\'):
      self.markers = markers
      self.curmark = -1

    # ~~> An animated marker for the progress bar which defaults to appear
    #     as if it were rotating.
   def update(self, pbar):
      if pbar.finished:
         return self.markers[0]
      self.curmark = (self.curmark + 1)%len(self.markers)
      return self.markers[self.curmark]

"""
   Just the percentage done.
"""
class Percentage(ProgressBarWidget):
   def update(self, pbar):
      return '%3d%%' % pbar.percentage()

"""
   The bar of progress. It will strech to fill the line.
      marker - string or updatable object to use as a marker
      left - string or updatable object to use as a left border
      right - string or updatable object to use as a right border
      fill - character to use for the empty part of the progress bar
      fill_left - whether to fill from the left or the right
"""
class Bar(ProgressBarWidgetHFill):
#class Bar(WidgetHFill):
#   __slots__ = ('marker', 'left', 'right', 'fill', 'fill_left')

   def __init__(self, marker='#', left='|', right='|'): #, fill=' ',fill_left=True):
      self.marker = marker
      self.left = left
      self.right = right
      #self.fill = fill
      #self.fill_left = fill_left
   def _format_marker(self, pbar):
      if isinstance(self.marker, (str, unicode)):
         return self.marker
      else:
         return self.marker.update(pbar)
   # ~~> Updates the progress bar and its subcomponents
   def update(self, pbar, width):
      #left, marker, right = (format_updatable(i, pbar) for i in
      #                         (self.left, self.marker, self.right))
      #width -= len(left) + len(right)
      # ~~> Marker must *always* have length of 1
      #marker *= int(pbar.currval / pbar.maxval * width)
      percent = pbar.percentage()
      cwidth = width - len(self.left) - len(self.right)
      marked_width = int(percent * cwidth / 100)
      m = self._format_marker(pbar)
      bar = (self.left + (m*marked_width).ljust(cwidth) + self.right)
      #if self.fill_left: return '%s%s%s' % (left, marker.ljust(width, self.fill), right)
      #else: return '%s%s%s' % (left, marker.rjust(width, self.fill), right)
      return bar

"""
   The reverse bar of progress, or bar of regress. :)
"""
class ReverseBar(Bar):

   #def __init__(self, marker='#', left='|', right='|', fill=' ', fill_left=False):
   #     self.marker = marker
   #     self.left = left
   #     self.right = right
   #     self.fill = fill
   #     self.fill_left = fill_left
   def update(self, pbar, width):
      percent = pbar.percentage()
      cwidth = width - len(self.left) - len(self.right)
      marked_width = int(percent * cwidth / 100)
      m = self._format_marker(pbar)
      bar = (self.left + (m*marked_width).rjust(cwidth) + self.right)
      return bar

default_widgets = [Bar(marker='\\',left='[',right=']'),' ',Percentage(),' ',ETA()]
default_subwidgets = [Bar(marker='.',left='[',right=']')]

"""
def format_updatable(updatable, pbar):
   if hasattr(updatable, 'update'): return updatable.update(pbar)
   else: return updatable

# ~~> Widget which displays the elapsed seconds.
class Timer(Widget):
   __slots__ = ('format',)
   TIME_SENSITIVE = True
   def __init__(self, format='Elapsed Time: %s'): self.format = format

   @staticmethod
   # ~~> Formats time as the string "HH:MM:SS".
   def format_time(seconds): return str(datetime.timedelta(seconds=int(seconds)))

   # ~~> Updates the widget to show the elapsed time.
   def update(self, pbar): return self.format % self.format_time(pbar.seconds_elapsed)

# ~~> Displays the current count
class Counter(Widget):
   __slots__ = ('format',)
   def __init__(self, format='%d'): self.format = format
   def update(self, pbar): return self.format % pbar.currval

# ~~> Displays a formatted label
class FormatLabel(Timer):
   mapping = {
        'elapsed': ('seconds_elapsed', Timer.format_time),
        'finished': ('finished', None),
        'last_update': ('last_update_time', None),
        'max': ('maxval', None),
        'seconds': ('seconds_elapsed', None),
        'start': ('start_time', None),
        'value': ('currval', None)
   }

   __slots__ = ('format',)
   def __init__(self, format):
      self.format = format

   def update(self, pbar):
      context = {}
      for name, (key, transform) in self.mapping.items():
         try:
            value = getattr(pbar, key)
            if transform is None:
               context[name] = value
            else:
               context[name] = transform(value)
         except: pass
      return self.format % context

# ~~> Returns progress as a count of the total (e.g.: "5 of 47")
class SimpleProgress(Widget):
   __slots__ = ('sep',)
   def __init__(self, sep=' of '): self.sep = sep
   def update(self, pbar): return '%d%s%d' % (pbar.currval, self.sep, pbar.maxval)

class BouncingBar(Bar):

   # ~~> Updates the progress bar and its subcomponents
   def update(self, pbar, width):
      left, marker, right = (format_updatable(i, pbar) for i in
                               (self.left, self.marker, self.right))
      width -= len(left) + len(right)
      if pbar.finished: return '%s%s%s' % (left, width * marker, right)
      position = int(pbar.currval % (width * 2 - 1))
      if position > width: position = width * 2 - position
      lpad = self.fill * (position - 1)
      rpad = self.fill * (width - len(marker) - len(lpad))
      # Swap if we want to bounce the other way
      if not self.fill_left: rpad, lpad = lpad, rpad
      return '%s%s%s%s%s' % (left, lpad, marker, rpad, right)

   def start(self):
      if self.maxval is None: self.maxval = self._DEFAULT_MAXVAL
      self.num_intervals = max(100, self.term_width)
      self.next_update = 0
      if self.maxval is not UnknownLength:
         if self.maxval < 0: raise ValueError('Value out of range')
         self.update_interval = self.maxval / self.num_intervals
      self.start_time = self.last_update_time = time.time()
      self.update(0)
      return self

"""
"""
   The ProgressBar class which updates and prints the bar.

    A common way of using it is like:
        pbar = ProgressBar().start()
        for i in range(100):
    ...    # do something
    ...    pbar.update(i+1)
        pbar.finish()

    You can also use a ProgressBar as an iterator:
        progress = ProgressBar()
        for i in progress(some_iterable):
    ...    # do something

    The term_width parameter represents the current terminal width. If the
    parameter is set to an integer then the progress bar will use that,
    otherwise it will attempt to determine the terminal width falling back to
    80 columns if the width cannot be determined.

    When implementing a widget's update method you are passed a reference to
    the current progress bar. As a result, you have access to the
    ProgressBar's methods and attributes. Although there is nothing preventing
    you from changing the ProgressBar you should treat it as read only.

    Useful methods and attributes include:
       - currval: current progress (0 <= currval <= maxval)
       - maxval: maximum (and final) value
       - finished: True if the bar has finished (reached 100%)
       - start_time: the time when start() method of ProgressBar was called
       - seconds_elapsed: seconds elapsed since start_time and last call to
                        update
       - percentage(): progress in percent [0..100]
"""
class ProgressBar(object):

   def __init__(self, maxval=100, widgets=default_widgets, term_width=None,
                fd=sys.stderr):
      assert maxval > 0
      self.maxval = maxval
      self.widgets = widgets
      self.fd = fd
      self.signal_set = False
      self.term_width = 79
      if term_width is None:
            try:
                self.handle_resize(None,None)
                signal.signal(signal.SIGWINCH, self.handle_resize)
                self.signal_set = True
            except:
                self.term_width = 79
      else:
            self.term_width = term_width

      self.currval = 0
      self.finished = False
      self.prev_percentage = -1
      self.start_time = None
      self.seconds_elapsed = 0

   def handle_resize(self, signum, frame):
      #h,w=array('h', ioctl(self.fd,termios.TIOCGWINSZ,'\0'*8))[:2]
      #self.term_width = w
      pass

   def percentage(self):
      "Returns the percentage of the progress."
      return self.currval*100.0 / self.maxval

   def _format_widgets(self):
      r = []
      hfill_inds = []
      num_hfill = 0
      currwidth = 0
      for i, w in enumerate(self.widgets):
          if isinstance(w, ProgressBarWidgetHFill):
              r.append(w)
              hfill_inds.append(i)
              num_hfill += 1
          elif isinstance(w, (str, unicode)):
              r.append(w)
              currwidth += len(w)
          else:
              weval = w.update(self)
              currwidth += len(weval)
              r.append(weval)
      for iw in hfill_inds:
          r[iw] = r[iw].update(self, (self.term_width-currwidth)/num_hfill)
      return r

   def _format_line(self):
      return ''.join(self._format_widgets()).ljust(self.term_width)

   def _need_update(self):
      return int(self.percentage()) != int(self.prev_percentage)

   def update(self, value, carriage='\r'):
      "Updates the progress bar to a new value."
      assert 0 <= value <= self.maxval
      self.currval = value
      if not self._need_update() or self.finished: return
      if not self.start_time: self.start_time = time.time()
      self.seconds_elapsed = time.time() - self.start_time
      self.prev_percentage = self.percentage()
      if not hide_default:
          if value != self.maxval:
              self.fd.write(self._format_line() + carriage)
          else:
              self.finished = True
              self.fd.write(' '*79+'\r') # /!\ remove the progress bar from display
              #self.fd.write(self._format_line() + '\n') or with carriage

   def write(self, str, value):
      "Move the progress bar along."
      self.fd.write(' '*79+'\r')
      self.fd.write(str+'\n')
      if not self.start_time: self.start_time = time.time()
      self.seconds_elapsed = time.time() - self.start_time
      self.prev_percentage = self.percentage()
      if value != self.maxval:
          self.fd.write(self._format_line() + '\r')
      else:
          self.finished = True
          self.fd.write(' '*79+'\r') # /!\ remove the progress bar from display
          #self.fd.write(self._format_line() + '\n')

   def trace(self):
      "Leave a trace on screen of the progress bar and carry on to the next line."
      if self.currval > 0: self.fd.write(self._format_line() + '\n')

   def start(self):
      # ~~> Start measuring time, and prints the bar at 0%.
      self.update(0)
      return self

   def finish(self):
      # ~~> Used to tell the progress is finished.
      self.update(self.maxval)
      if self.signal_set: signal.signal(signal.SIGWINCH, signal.SIG_DFL)

class SubProgressBar(ProgressBar):

   def __init__(self, maxval=100):
      ProgressBar.__init__( self, maxval=maxval, widgets=default_subwidgets )

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Nilton Volpato"
__date__ ="$07-May-2006 08:51:29$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ widgets ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   if True:
      widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
      pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
      for i in range(1000000):
         # do something
         pbar.update(10*i+1)
      pbar.finish()
   if True:
      widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),' ', ETA(), ' ', FileTransferSpeed()]
      pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
      for i in range(1000000):
         # do something
         pbar.update(10*i+1)
      pbar.finish()
   if True:
      widgets=[Percentage(), Bar(marker='o',left='[',right=']')]
      pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
      for i in range(1000000):
         # do something
         pbar.update(10*i+1)
      pbar.finish()
   sys.exit(0)
