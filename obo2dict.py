#!/usr/bin/env python

# MIT License
#
# Copyright (c) 2017-2023 Institut national de recherche pour l'agriculture, l'alimentation et l'environnement (Inrae)
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
import obo
import codecs


class HeaderMap(object):
    def __init__(self):
        pass

    def __getitem__(self, item):
        return item


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

    def key_parent_id(self):
        if isinstance(self.item, obo.Stanza):
            return self.item.id.value
        for parent in self.stanza.parents():
            return parent.id.value

    def key_synonym(self):
        if isinstance(self.item, obo.Synonym):
            return self.item.text
        if isinstance(self.item, obo.Stanza):
            return self.item.name.value
        raise Exception()

    def key_xref(self):
        if isinstance(self.item, obo.XRef):
            return self.item.reference
        return '\t'.join(x.reference for x in self.stanza.xref)

    def key_subset(self):
        for ancestor in self.stanza.ancestors(include_self=True):
            if isinstance(ancestor, obo.TermOrType):
                for subset in ancestor.subsets:
                    return subset
        return ''

    def key_id_path(self):
        if isinstance(self.item, list):
            return '/' + '/'.join(term.id.value for term in self.item)
        if isinstance(self.item, obo.Term):
            paths = list(self.item.paths(include_self=True))
            return '/' + '/'.join(term.id.value for term in paths[0])
        if isinstance(self.item, obo.Synonym):
            paths = list(self.item.stanza.paths(include_self=True))
            return '/' + '/'.join(term.id.value for term in paths[0])
        if isinstance(self.item, obo.XRef):
            paths = list(self.item.term.paths(include_self=True))
            return '/' + '/'.join(term.id.value for term in paths[0])
        raise Exception('expected list, got ' + str(self.item))

    def key_name_path(self):
        if isinstance(self.item, list):
            return '/' + '/'.join(term.name.value for term in self.item)
        if isinstance(self.item, obo.Term):
            paths = list(self.item.paths(include_self=True))
            return '/' + '/'.join(term.name.value for term in paths[0])
        raise Exception('expected list, got ' + str(self.item))


def iter_terms(onto):
    return ((term, term) for term in onto.stanzas.values() if isinstance(term, obo.Term))


def iter_term_synonyms(onto):
    for term in onto.stanzas.values():
        if isinstance(term, obo.Term):
            yield term, term
            for syn in term.synonyms:
                yield syn, term


def iter_term_parents(onto):
    for term in onto.stanzas.values():
        if isinstance(term, obo.Term):
            for parent in term.parents():
                yield parent, term


def iter_term_paths(onto):
    for term in onto.stanzas.values():
        if isinstance(term, obo.Term):
            for path in term.paths(include_self=True):
                yield path, term


def iter_term_xrefs(onto):
    for term in onto.stanzas.values():
        if isinstance(term, obo.Term):
            for xref in term.xref:
                yield xref, term


class OBO2Dict(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.set_defaults(iter=iter_term_synonyms, pattern='%(synonym)s\\t%(id)s\\t%(name)s', header=False)
        self.add_option('--term-paths', action='store_const', dest='iter', const=iter_term_paths,
                        help='iterates over term paths')
        self.add_option('--term-synonyms', action='store_const', dest='iter', const=iter_term_synonyms,
                        help='iterates over term synonyms')
        self.add_option('--term-xrefs', action='store_const', dest='iter', const=iter_term_xrefs,
                        help='iterates over term cross references')
        self.add_option('--term-parents', action='store_const', dest='iter', const=iter_term_parents,
                        help='iterates over term parents')
        self.add_option('--terms', action='store_const', dest='iter', const=iter_terms,
                        help='iterates over terms')
        self.add_option('--pattern', action='store', type='string', dest='pattern',
                        metavar='PATTERN', help='item output pattern (default: %default)')
        self.add_option('--header', action='store_true', dest='header',
                        help='print header line')

    def run(self):
        options, args = self.parse_args()
        onto = obo.Ontology()
        onto.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), obo.InvalidXRefWarn(), *args)
        onto.check_required()
        onto.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())
        pattern = options.pattern.replace('\\t', '\t')
        if options.header:
            print(pattern % HeaderMap())
        vmap = ValueMap()
        for value in options.iter(onto):
            vmap.set(value)
            print(pattern % vmap)


if __name__ == '__main__':
    OBO2Dict().run()
