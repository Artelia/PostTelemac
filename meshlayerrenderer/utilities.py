# -*- coding: UTF-8 -*-

import time
import os
from math import log, exp as exp_

def complete_filename(name):
    return os.path.join(os.path.dirname(__file__), name)

def format_(min_, max_):
    format_ = "%.2e"
    if max_ < 10000 and min_ >= 0.1:
        format_ = "%.1f"
    return format_

def multiplier(value):
    """return a couple of multiplier and text representing it that are appropiate for
    the specified range"""

    multiplyers = {1e-9:u" x 10⁻⁹", 1e-6:u" x 10⁻⁶", 1e-3:u" x 10⁻³", 1.0:u"", 1e3:u" x 10³", 1e6:u" x 10⁶", 1e9:u" x 10⁹"}
    mult = 1e-9
    for x in sorted(multiplyers.keys()):
        if x <= abs(value):
            mult = x 
    return mult, multiplyers[mult]

def linemerge(lines):
    """Returns a (set of) LineString(s) formed by sewing together a multilinestring."""
    graph = {}
    # first build a bidirectional graph
    for line in lines:
        b = tuple(line[0])
        e = tuple(line[-1])
        if b in graph:
            graph[b].add(e) 
        else: 
            graph[b] = set([e])
        if e in graph:
            graph[e].add(b) 
        else: 
            graph[e] = set([b])
     
    # now consume the graph
    if not len(graph):
        return []
    nxt = graph.iterkeys().next()
    out = [[nxt]]
    while len(graph):
        #assert len(graph[nxt]) == 1 or len(graph[nxt]) == 2
        prev = nxt
        nxt = None
        while len(graph[prev]) and nxt not in graph:
            nxt = graph[prev].pop()
        graph.pop(prev, None)
        if nxt not in graph:
            if nxt:
                out[-1].append(nxt)
            if not len(graph):
                break
            nxt = graph.iterkeys().next()
            out.append([nxt])
        else:
            out[-1].append(nxt)
    return out
         
# run as script for testing
if __name__ == "__main__":
    #@todo: unit test multiplier
    #@todo: unit test linemerge
    pass

class Timer(object):
    def __init__(self):
        self.start = time.time()
    def reset(self, text=""):
        s = self.start
        self.start = time.time()
        return "%30s % 8.4f sec"%(text, (self.start - s))




