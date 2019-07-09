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
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from sys import stdout, stderr, argv
import re 
import datetime
from os import getenv
from datetime import datetime

MRCOLS = 'MRCOLS.RRF'
MRFILES = 'MRFILES.RRF'
MRCONSO = 'MRCONSO.RRF'
MRREL = 'MRREL.RRF'
MRHIER = 'MRHIER.RRF'


EPILOG = '''* Filter labels by language (english):
  --filter LAT ENG

* Filter labels by source:
  --filter SAB SNOMEDCT_US,RXNORM

* Filter terms by source (import all labels if a CUI contains at least one label from the specified sources):
  --sources SNOMEDCT_US,RXNORM

* Lowercase labels (and case insensitive de-duplication):
  --case-folding

* Exclude labels with regexp:
  --exclude-pattern '\d-'

* Import is-a relations (strict):
  --relation RELA isa is_a

* Import is-a relation (relaxed):
  --relation REL CHD is_a

* Relation filter by identifiers used to assert the relation:
  --relation-filter STYPE1 SCUI --relation-filter STYPE2 SCUI

* Relation filter by source:
  --relation-filter SAB SNOMED_CT,RXNORM
'''

class UMLS2OBO(ArgumentParser):
    def __init__(self):
        ArgumentParser.__init__(self, description='convert UMLS MR files into OBO', epilog=EPILOG, formatter_class=RawDescriptionHelpFormatter)
        self.add_argument('umls_dir', metavar='UMLS_DIR', type=str, default=None, help='UMLS directory containing MR files')
        self.add_argument('-f', '--filter', metavar=('COL', 'VALUES'), type=str, action='append', nargs=2, default=[], dest='filters', help='MRCONSO.RRF filter, only read lines if COL value is in VALUES (comma separated)')
        self.add_argument('-r', '--relation', metavar=('REL_COL', 'VALUE', 'REL'), type=str, action='append', nargs=3, default=[], dest='relations', help='MRREL.RRF relations, create a relation REL if COL calue equals VALUE')
        self.add_argument('-F', '--relation-filter', metavar=('COL', 'VALUES'), type=str, action='append', nargs=2, default=[], dest='relation_filters', help='MRREL.RRF filter, only read lines if COL value is in VALUES (comma separated)')
        self.add_argument('-s', '--sources', metavar='SOURCES', type=str, action='store', default=None, dest='sources', help='keep terms from the specified sources')
        self.add_argument('--keep-duplicate-synonyms', action='store_true', default=False, dest='keep_duplicate_synonyms', help='do not remove duplicate synonyms')
        self.add_argument('-c', '--case-folding', action='store_true', default=False, dest='case_folding', help='lowercase names and synonyms')
        self.add_argument('-p', '--exclude-pattern', metavar='REGEXP', action='append', type=re.compile, default=[], dest='exclude_patterns', help='exclude labels that match the specified regular expression')
        self.add_argument('-R', '--root', metavar=('REL', 'ID', 'NAME'), type=str, action='append', nargs=3, default=[], dest='roots', help='add root')
        self.add_argument('-H', '--hierarchy', metavar='REL', type=str, default=None, dest='hierarchy', help='')
        self.add_argument('-I', '--hierarchy-filter', metavar=('COL', 'VALUES'), type=str, action='append', nargs=2, default=[], dest='hierarchy_filters', help='MRHIER.RRF filter, only read lines if COL value is in VALUES (comma separated)')
        self.columns = {
            MRCONSO: {},
            MRREL: {},
            MRHIER: {},
        }
        self.filters = {
            MRCONSO: (),
            MRREL: (),
            MRHIER: (),
        }
        self.aui2cui = {}
        self.relations = ()
        self.onto = Ontology()
        header_reader = HeaderReader(self.onto, UnhandledTagFail(), DeprecatedTagWarn())
        header_reader.read_date(SourcedValue('<cmdline>', 0, datetime.now().strftime('%d:%m:%Y %H:%M')))
        header_reader.read_auto_generated_by(SourcedValue('<cmdline>', 0, ' '.join(argv)))
        header_reader.read_saved_by(SourcedValue('<cmdline>', 0, getenv('USER')))

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
                if not line:
                    continue
                cols = line.split('|')
                if UMLS2OBO._valid_cols(n, filters, cols):
                    yield n, cols

    @staticmethod
    def _valid_cols(n, filters, cols):
        for col, values in filters:
            try:
                if cols[col] not in values:
                    return False
            except IndexError:
                stderr.write('\n  malformed line %d\n' % n)
                return False
        return True
    
    def _load_columns(self, args):
        for n, cols in self.mr_read(args, MRFILES):
            filename = cols[0]
            if filename in self.columns:
                colmap = self.columns[filename]
                for idx, name in enumerate(cols[2].split(',')):
                    colmap[name] = idx

    def _exclude(self, args, form):
        for p in args.exclude_patterns:
            m = p.search(form)
            if m is not None:
                return True
        return False
    
    def _load_terms(self, args):
        nt = 0
        current = None
        sources = set()
        forms = set()
        for n, cols in self.mr_read(args, MRCONSO):
            if n % 137:
                stderr.write('  line % 9d, % 7d terms\r' % (n, nt))
            cui = cols[0]
            aui = cols[7]
            self.aui2cui[aui] = cui
            if current is None or current.id.value != cui:
                if current is not None:
                    if (not forms) or (args.sources and sources.isdisjoint(args.sources)):
                        del self.onto.stanzas[current.id.value]
                        nt -= 1
                    elif current.name is None:
                        if current.synonyms:
                            syn = current.synonyms.pop(0)
                            current.name = SourcedValue(MRCONSO, syn.lineno, syn.text)
                        else:
                            del self.onto.stanzas[current.id.value]
                            nt -= 1
                current = Term(MRCONSO, n, self.onto, SourcedValue(MRCONSO, n, cui))
                nt += 1
                sources = set()
                forms = set()
            sources.add(cols[11])
            form = cols[14]
            if args.case_folding:
                form = form.lower()
            if self._exclude(args, form):
                continue
            if cols[2] == 'P':
                current.name = SourcedValue(MRCONSO, n, form)
            elif args.keep_duplicate_synonyms or form not in forms:
                Synonym(MRCONSO, n, current, form, 'EXACT', None, '')
            forms.add(form)
        stderr.write('  line % 9d, % 7d terms\n' % (n, nt))

    def _get_relation(self, cols):
        for col, value, rel in self.relations:
            if cols[col] == value:
                return rel
        return None

    @staticmethod
    def _has_ref(term, rel, ref):
        if rel not in term.references:
            return False
        for r in term.references[rel]:
            if r.reference == ref:
                return True
        return False
        
    def _load_relations(self, args):
        nr = 0
        for n, cols in self.mr_read(args, MRREL):
            if n % 137:
                stderr.write('  line % 9d, % 7d relations\r' % (n, nr))
            lid = cols[4]
            if lid not in self.onto.stanzas:
                continue
            rid = cols[0]
            if rid not in self.onto.stanzas:
                continue
            rel = self._get_relation(cols)
            if rel is None:
                continue
            if lid == rid:
                #stderr.write('\n  relation with self (%s) line %d\n' % (lid, n))
                continue
            term = self.onto.stanzas[lid]
            if not UMLS2OBO._has_ref(term, rel, rid):
                StanzaReference(MRREL, n, term, rel, rid)
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

    def _get_mutual(self, rel):
        result = set()
        for stanza in self.onto.iter_user_stanzas():
            if rel not in stanza.references:
                continue
            sid = stanza.id.value
            for link in stanza.references[rel]:
                ref = link.reference
                if ref not in self.onto.stanzas:
                    continue
                other = self.onto.stanzas[ref]
                if rel not in other.references:
                    continue
                for olink in other.references[rel]:
                    if olink.reference == sid and (ref, sid) not in result:
                        result.add((sid, ref))
        return result

    def _merge_mutual(self, stanza1, stanza2):
        for rel, links in stanza2.references.items():
            if rel in stanza1.references:
                already = set(l.reference for l in stanza1.references[rel])
            else:
                already = ()
            for link in links:
                if link.reference not in already:
                    StanzaReference(link.source, link.lineno, stanza1, rel, link.reference)
        already = set(syn.text for syn in stanza1.synonyms)
        for syn in stanza2.synonyms:
            if syn.text not in already:
                Synonym(syn.source, syn.lineno, stanza1, syn.text, 'EXACT', None, '')
        id1 = stanza1.id.value
        id2 = stanza2.id.value
        for stanza in self.onto.iter_user_stanzas():
            for links in stanza.references.values():
                for link in links:
                    if link.reference == id2:
                        link.reference = id1
        for rel in stanza1.references:
            stanza1.references[rel] = list(link for link in stanza1.references[rel] if link.reference != id1)
        stanza1.alt_ids.append(id2)
        del self.onto.stanzas[id2]

    def _merge_all(self):
        nmerge = 0
        for rel in set(rel for (col, val, rel) in self.relations):
            for id1, id2 in self._get_mutual(rel):
                if id1 in self.onto.stanzas and id2 in self.onto.stanzas:
                    self._merge_mutual(self.onto.stanzas[id1], self.onto.stanzas[id2])
                    nmerge += 1
        return nmerge

    def _load_hierarchy(self, args):
        nr = 0
        for n, cols in self.mr_read(args, MRHIER):
            if n % 137:
                stderr.write('  line % 9d, % 7d relations\r' % (n, nr))
            cui1 = cols[0]
            if cui1 not in self.onto.stanzas:
                continue
            term = self.onto.stanzas[cui1]
            cui_path = tuple(self.aui2cui[aui] for aui in cols[6].split('.') if aui in self.aui2cui)
            path = tuple((cui, self.onto.stanzas[cui]) for cui in cui_path if cui in self.onto.stanzas)
            for cui, parent in reversed(path):
                if term.id.value != cui and not UMLS2OBO._has_ref(term, args.hierarchy, cui):
                    StanzaReference(MRHIER, n, term, args.hierarchy, cui)
                    nr += 1
                    break
                term = parent
        stderr.write('  line % 9d, % 7d relations\n' % (n, nr))

    def run(self):
        args = self.parse_args()
        self._load_columns(args)
        self.filters[MRCONSO] = tuple((self._col(MRCONSO, col), set(values.split(','))) for col, values in args.filters)
        if args.sources is not None:
            args.sources = set(args.sources.split(','))
        self._load_terms(args)
        self.onto.check_required()
        if len(args.relations) > 0:
            self.relations = tuple((self._col(MRREL, col), value, rel) for col, value, rel in args.relations)
            self.filters[MRREL] = tuple((self._col(MRREL, col), set(values.split(','))) for col, values in args.relation_filters)
            self._load_relations(args)
            while True:
                nmerge = self._merge_all()
                if nmerge == 0:
                    break
                else:
                    stderr.write('merged %d terms\n' % nmerge)
        if args.hierarchy is not None:
            self.filters[MRHIER] = tuple((self._col(MRHIER, col), set(values.split(','))) for col, values in args.hierarchy_filters)
            self._load_hierarchy(args)
        for rel, id, name in args.roots:
            sourced_id = SourcedValue('<cmdline>', 0, id)
            root = Term('<cmdline>', 0, self.onto, sourced_id)
            root.name = SourcedValue('<cmdline>', 0, name)
            for term in self.onto.iterterms():
                if rel not in term.references and term.id.value != id:
                    StanzaReference('<cmdline>', 0, term, rel, id)
        stderr.write('resolving references\n')
        self.onto.resolve_references(DanglingReferenceFail(), DanglingReferenceFail())
        stderr.write('writing OBO\n')
        self.onto.write_obo(stdout)
        for term in self.onto.iterterms():
            term.write_obo(stdout)

if __name__ == '__main__':
    UMLS2OBO().run()
