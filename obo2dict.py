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

from optparse import OptionParser
from obo import *


class ValueMap(object):
    def __init__(self):
        self.item = None
        self.stanza = None

    def set(self, value):
        (self.item, self.stanza) = value

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError()
        method = 'key_' + key.replace('-', '_')
        if not hasattr(self, method):
            raise KeyError(key)
        return getattr(self, method)()

    def key_name(self):
        return self.stanza.name.value

    def key_id(self):
        return self.stanza.id.value

    def key_synonym(self):
        if isinstance(self.item, Synonym):
            return self.item.text
        if isinstance(self.item, Stanza):
            return self.item.name.value
        raise Exception()

    def key_xref(self):
        if isinstance(self.item, XRef):
            return self.item.reference
        return '\t'.join(x.reference for x in self.stanza.xref)

    def key_subset(self):
        for ancestor in self.stanza.ancestors(include_self=True):
            if isinstance(ancestor, TermOrType):
                for subset in ancestor.subsets:
                    return subset
        return ''

    def key_id_path(self):
        if isinstance(self.item, list):
            return '/' + '/'.join(term.id.value for term in self.item)
        if isinstance(self.item, Term):
            paths = list(self.item.paths(include_self=True))
            return '/' + '/'.join(term.id.value for term in paths[0])
        if isinstance(self.item, Synonym):
            paths = list(self.item.stanza.paths(include_self=True))
            return '/' + '/'.join(term.id.value for term in paths[0])
        if isinstance(self.item, XRef):
            paths = list(self.item.term.paths(include_self=True))
            return '/' + '/'.join(term.id.value for term in paths[0])
        raise Exception('expected list, got ' + str(self.item))

    def key_name_path(self):
        if isinstance(self.item, list):
            return '/' + '/'.join(term.name.value for term in self.item)
        if isinstance(self.item, Term):
            paths = list(term.paths(include_self=True))
            return '/' + '/'.join(term.name.value for term in paths[0])
        raise Exception('expected list, got ' + str(self.item))


def iter_terms(onto):
    return ((term, term) for term in onto.stanzas.itervalues() if isinstance(term, Term))

def iter_term_synonyms(onto):
    for term in onto.stanzas.itervalues():
        if isinstance(term, Term):
            yield term, term
            for syn in term.synonyms:
                yield syn, term

def iter_term_paths(onto):
    for term in onto.stanzas.itervalues():
        if isinstance(term, Term):
            for path in term.paths(include_self=True):
                yield path, term

def iter_term_xrefs(onto):
    for term in onto.stanzas.itervalues():
        if isinstance(term, Term):
            for xref in term.xref:
                yield xref, term


class OBO2Dict(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.set_defaults(iter=iter_term_synonyms, pattern='%(synonym)s\\t%(id)s\\t%(name)s')
        self.add_option('--term-paths', action='store_const', dest='iter', const=iter_term_paths, help='iterates over term paths')
        self.add_option('--term-synonyms', action='store_const', dest='iter', const=iter_term_synonyms, help='iterates over term synonyms')
        self.add_option('--term-xrefs', action='store_const', dest='iter', const=iter_term_xrefs, help='iterates over term cross references')
        self.add_option('--terms', action='store_const', dest='iter', const=iter_terms, help='iterates over terms')
        self.add_option('--pattern', action='store', type='string', dest='pattern', metavar='PATTERN', help='item output pattern (default: %default)')
        
    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagWarn(), *args)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())
        map = ValueMap()
        pattern = options.pattern.decode('string_escape')
        for value in options.iter(onto):
            map.set(value)
            print pattern % map

if __name__ == '__main__':
    OBO2Dict().run()
