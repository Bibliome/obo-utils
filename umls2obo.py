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
from argparse import ArgumentParser
from sys import stdout, stderr



MRCOLS = 'MRCOLS.RRF'
MRFILES = 'MRFILES.RRF'
MRCONSO = 'MRCONSO.RRF'
MRREL = 'MRREL.RRF'

class UMLS2OBO(ArgumentParser):
    def __init__(self):
        ArgumentParser.__init__(self, description='convert UMLS MR files into OBO', epilog='something')
        self.add_argument('umls_dir', metavar='UMLS_DIR', type=str, default=None, help='UMLS directory containing MR files')
        self.add_argument('-f', '--filter', metavar='COL VALUES', type=str, action='append', nargs=2, default=[], dest='filters', help='MRCONSO.RRF filter')
        self.add_argument('-r', '--relation', metavar='REL_COL VALUE REL', type=str, action='append', nargs=3, default=[], dest='relations', help='MRREL.RRF relations')
        self.add_argument('-F', '--relation-filter', metavar='COL VALUES', type=str, action='append', nargs=2, default=[], dest='relation_filters', help='MRREL.RRF filter')
        self.columns = {
            MRCONSO: {},
            MRREL: {},
        }
        self.filters = {
            MRCONSO: (),
            MRREL: (),
        }
        self.relations = ()
        self.onto = Ontology()

    def mr_read(self, args, filename):
        path = '/'.join((args.umls_dir, filename))
        stderr.write('reading %s\n' % path)
        if filename in self.filters:
            filters = self.filters[filename]
        else:
            filters = []
        with open(path) as f:
            for n, line in enumerate(f):
                line = line.strip()
                cols = line.split('|')
                if UMLS2OBO._valid_cols(filters, cols):
                    yield n, cols

    @staticmethod
    def _valid_cols(filters, cols):
        for col, values in filters:
            if cols[col] not in values:
                return False
        return True
    
    def _load_columns(self, args):
        for n, cols in self.mr_read(args, MRFILES):
            filename = cols[0]
            if filename in self.columns:
                colmap = self.columns[filename]
                for idx, name in enumerate(cols[2].split(',')):
                    colmap[name] = idx
                
    def _load_terms(self, args):
        nt = 0
        for n, cols in self.mr_read(args, MRCONSO):
            if n % 137:
                stderr.write('  line % 9d, % 7d terms\r' % (n, nt))
            tid = cols[0]
            if tid in self.onto.stanzas:
                term = self.onto.stanzas[tid]
            else:
                nt += 1
                term = Term(MRCONSO, n, self.onto, SourcedValue(MRCONSO, n, tid))
            if cols[2] == 'P':
                term.name = SourcedValue(MRCONSO, n, cols[14])
            else:
                Synonym(MRCONSO, n, term, cols[14], 'EXACT', None, '')
        stderr.write('  line % 9d, % 7d terms\n' % (n, nt))

    def _get_relation(self, cols):
        for col, value, rel in self.relations:
            if cols[col] == value:
                return rel
        return None
        
    def _load_relations(self, args):
        nr = 0
        for n, cols in self.mr_read(args, MRREL):
            if n % 137:
                stderr.write('  line % 9d, % 7d relations\r' % (n, nr))
            lid = cols[0]
            if lid not in self.onto.stanzas:
                continue
            rid = cols[4]
            if rid not in self.onto.stanzas:
                continue
            rel = self._get_relation(cols)
            if rel is None:
                continue
            StanzaReference(MRREL, n, self.onto.stanzas[lid], rel, rid)
            nr += 1
        stderr.write('  line % 9d, % 7d relations\n' % (n, nr))
        
    def _create_filter(self, filename, col, values):
        try:
            col = int(col)
        except ValueError:
            col = self.columns[filename][col]
        values = set(values.split(','))
        return col, values

    def _col(self, filename, col):
        try:
            return int(col)
        except ValueError:
            return self.columns[filename][col]

    def run(self):
        args = self.parse_args()
        self._load_columns(args)
        self.filters[MRCONSO] = tuple((self._col(MRCONSO, col), set(values.split(','))) for col, values in args.filters)
        self._load_terms(args)
        self.relations = tuple((self._col(MRREL, col), value, rel) for col, value, rel in args.relations)
        if self.relations:
            self.filters[MRREL] = tuple((self._col(MRCONSO, col), set(values.split(','))) for col, values in args.relation_filters)
            self._load_relations(args)
            stderr.write('resolving references')
            self.onto.resolve_references(DanglingReferenceFail(), DanglingReferenceFail())
        self.onto.write_obo(stdout)
        for term in self.onto.iterterms():
            term.write_obo(stdout)

if __name__ == '__main__':
    UMLS2OBO().run()
