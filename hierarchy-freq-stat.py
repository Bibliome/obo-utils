#!/usr/bin/env python


# MIT License
# 
# Copyright (c) 2017 Institut National de la Recherche Agronomique
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from scipy.stats.distributions import chi2
from obo import *
from sys import argv, stdout, stderr
from collections import defaultdict
from math import log
from optparse import OptionParser

EXPECTED = 0
OBSERVED = 1
FREQSETS = (EXPECTED, OBSERVED)

def xlog(msg, *args):
    stderr.write(msg % args)
    stderr.write('\n')

class Count:
    def __init__(self):
        self.proper = 0

class Hierarchy:
    def __init__(self):
        self.node_map = {}
        self.root = None

    def create_node(self, id, name, parent):
        if id in self.node_map:
            node = self.node_map[id]
        else:
            node = Node(id, name)
            self.node_map[id] = node
        if parent is None:
            if self.root is not None:
                raise Exception('already has root')
            self.root = node
        else:
            parent.children.append(node)
        return node

    def _obo_node(self, childrenmap, term, parent):
        node = self.create_node(term.id.value, term.name.value, parent)
        for child in childrenmap[term.id.value]:
            self._obo_node(childrenmap, child, node)

    def read_obo(self, filename, rootid):
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagWarn(), filename)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())
        childrenmap = defaultdict(list)
        for term in onto.iterterms():
            for par in term.parents():
                childrenmap[par.id.value].append(term)
        root = onto.stanzas[rootid]
        self._obo_node(childrenmap, root, None)

    def read_frequencies(self, filename, c):
        f = open(filename)
        for line in f:
            count, id = line.strip().split(None, 1)
            if id in self.node_map:
                self.node_map[id].counts[c].proper += int(count)
        f.close()

class Node:
    def __init__(self, id, name=''):
        self.id = id
        self.name = name
        self.counts = (Count(), Count())
        self.children = []

    def _write(self, f, indent=''):
        f.write('%s%s (%d/%d)\n' % (indent, self.id, self.counts[EXPECTED].proper, self.counts[OBSERVED].proper))
        indent = '  ' + indent
        for child in self.children:
            child._write(f, indent)

    def cumulate(self, c=None):
        if c is None:
            for i in FREQSETS:
                self.cumulate(i)
            return
        if hasattr(self.counts[c], 'cumul'):
            return
        r = self.counts[c].proper
        for child in self.children:
            child.cumulate(c)
            r += child.counts[c].cumul
        self.counts[c].cumul = r

    def observed(self):
        return self.counts[OBSERVED].cumul

    def expected(self):
        return self.counts[EXPECTED].cumul

def delta_chi2(exp, obs):
    return ((obs - exp) ** 2) / exp
        
def delta_g(exp, obs):
    return 2 * obs * log(obs / exp)

def delta_nil(exp, obs):
    return 0

class Chi2Cell:
    def __init__(self, ratio, deltafun, child):
        self.child = child
        self.expected = ratio * child.expected()
        self.observed = child.observed() + 1
        self.delta = deltafun(self.expected, self.observed)
        self.direction = 0
        self.pvalue = 1.0

    def set_direction(self):
        self.direction = cmp(self.observed, self.expected)

class RealChi2Cell:
    def __init__(self, child, expected, observed, delta, direction, pvalue):
        self.child = child
        self.expected = expected
        self.observed = observed
        self.delta = delta
        self.direction = direction
        self.pvalue = pvalue
        
        
def test_children_chi2(node, threshold, deltafun, depth=0):
    children = tuple(child for child in node.children if child.expected() > 0)
    result = []
    while len(children) >= 1:
        esum = sum(child.expected() for child in children)
        osum = sum(child.observed() for child in children) + len(children)
        ratio = float(osum) / float(esum)
        cells = tuple(Chi2Cell(ratio, deltafun, child) for child in children)
        dsum = sum(cell.delta for cell in cells)
        pvalue = chi2.sf(dsum, len(cells) - 1)
        if pvalue > threshold:
            for cell in cells:
                cell.pvalue = pvalue
                result.append(cell)
            break
        maxdelta = max(cell.delta for cell in cells)
        for cell in cells:
            if cell.delta == maxdelta:
                cell.pvalue = pvalue
                cell.set_direction()
                result.append(cell)
        children = tuple(cell.child for cell in cells if cell.delta < maxdelta)
    result.extend(Chi2Cell(1, delta_nil, child) for child in node.children if child.expected() == 0)
    yield result
    if depth > 0:
        for child in node.children:
            for r in test_children_chi2(child, threshold, deltafun, depth - 1):
                yield r

class HStat(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog --obo FILE --root ID --expected FILE --observed FILE [options]')
        self.set_defaults(depth=0, deltafun=delta_chi2, risk=0.001)
        self.add_option('--obo', action='store', type='string', dest='obo', help='hierarchy file in OBO format')
        self.add_option('--root', action='store', type='string', dest='root', help='identifier of the root node')
        self.add_option('--expected', action='store', type='string', dest='expected', help='expected frequencies (as given by uniq -c)')
        self.add_option('--observed', action='store', type='string', dest='observed', help='observed frequencies (as given by uniq -c)')
        self.add_option('--depth', action='store', type='int', dest='depth', help='maximum depth of tested nodes (default: %default)')
        self.add_option('--g-test', action='store_const', const=delta_g, dest='deltafun', help='use G-test instead of regular chi-squared difference formula')
        self.add_option('--risk', action='store', type='float', dest='risk', help='null hypothesis rejection risk (default: %default)')
        
    def run(self):
        options, args = self.parse_args()
        if len(args):
            raise Exception('stray argument: %s' % args[0])
        if options.obo is None:
            raise Exception('--obo is mandatory')
        if options.root is None:
            raise Exception('--root is mandatory')
        if options.expected is None:
            raise Exception('--expected is mandatory')
        if options.observed is None:
            raise Exception('--observed is mandatory')
        hierarchy = Hierarchy()
        hierarchy.read_obo(options.obo, options.root)
        hierarchy.read_frequencies(options.expected, EXPECTED)
        hierarchy.read_frequencies(options.observed, OBSERVED)
        hierarchy.root.cumulate()
        print 'ID\tDIRECTION\tDELTA\tOBSERVED\tEXPECTED\tCHILD-EXPECTED\tP-VALUE\tNAME'
        for cells in test_children_chi2(hierarchy.root, options.risk, options.deltafun, options.depth):
            for cell in cells:
                print '%s\t% 2d\t%15.6f\t%8d\t%15.6f\t%8d\t%f\t%s' % (cell.child.id, cell.direction, cell.delta, cell.observed, cell.expected, cell.child.expected(), cell.pvalue, cell.child.name)
            print
        

        
if __name__ == '__main__':
    HStat().run()
