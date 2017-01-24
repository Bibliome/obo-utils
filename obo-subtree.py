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
from sys import stdout








class OBOSubtree(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--exclude-root', action='append', dest='excluded_roots', help='')

    def _is_excluded(self, excluded_roots, excluded_terms, term):
        if term in excluded_terms:
            return True
        if term.id.value in excluded_roots:
            excluded_terms.add(term)
            return True
        if 'is_a' not in term.references:
            return False
        for link in term.references['is_a']:
            if not self._is_excluded(excluded_roots, excluded_terms, link.reference_object):
                return False
        excluded_terms.add(term)
        return True

    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagWarn(), *args)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())

        if options.excluded_roots is None:
            excluded_roots = set()
        else:
            excluded_roots = set(options.excluded_roots)
        excluded_terms = set()
        for term in onto.iterterms():
            self._is_excluded(excluded_roots, excluded_terms, term)
        for term in onto.iterterms():
            for link_type in term.references:
                term.references[link_type][:] = [link for link in term.references[link_type] if link.reference_object not in excluded_terms]
        for term in excluded_terms:
            del onto.stanzas[term.id.value]

        onto.write_obo(stdout)
        for stanza in onto.stanzas.itervalues():
            if isinstance(stanza, BuiltinStanza) or stanza.source == '<<builtin>>':
                continue
            stanza.write_obo(stdout)

if __name__ == '__main__':
    OBOSubtree().run()
