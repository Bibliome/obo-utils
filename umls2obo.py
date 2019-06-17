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

from obo import *
from optparse import OptionParser


class MR20B0(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--lang', action='store', default=None, dest='lang', help='term language filter')
        self.add_option('--source', action='append', default=[], dest='sources', help='term source filter')
        self.onto = Ontology()
                        
    def _load_terms(self, filename):
        with open(filename) as f:
            for n, line in enumerate(f):
                line = line.strip()
                cols = line.split('|')
                if self.options.lang is not None and self.options.lang != line[1]:
                    continue
                if self.options.sources and line[11] not in self.options.source:
                    continue
                tid = cols[0]
                if tid in onto.stanzas:
                    term = onto.stanzas[tid]
                else:
                    term = Term(filename, n, self.onto, tid)
                if cols[2] == 'P':
                    term.name = SourcedValue(filename, n, cols[14])
                else:
                    Synonym(filename, n, term, cols[14], 'EXACT', None, '')
                    
    def run(self):
        self.options, args = self.parse_args()
        if len(args) != 1:
            raise Exception()
        self._load_terms(args[0])
