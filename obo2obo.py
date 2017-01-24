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

def stanza_type_weight(stanza):
    t = stanza.__class__
    if t == Term:
        return 1
    if t == Typedef:
        return 2
    if t == Instance:
        return 3
    return 0

def _get_value(v):
    if hasattr(v, 'value'):
        return v.value
    return v

def stanza_comparator(attr):
    def result(a, b):
        twa = stanza_type_weight(a)
        twb = stanza_type_weight(b)
        if attr is None or twa != twb:
            return twa - twb
        aa = _get_value(getattr(a, attr))
        ab = _get_value(getattr(b, attr))
        return cmp(aa, ab)
    return result

class OBO2OBO(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--include-obsolete', action='store_true', dest='include_obsolete', default=False, help='include obsolete objects')
        self.add_option('--sort-by-id', action='store_const', dest='sort_by', const='id', default=None, help='sort stanzas by id')
        self.add_option('--sort-by-name', action='store_const', dest='sort_by', const='name', default=None, help='sort stanzas by name')
        self.add_option('--keep-synonyms-from', action='append', type='int', dest='synonyms_from', default=[], help='')
        self.add_option('--keep-isa-from', action='append', type='int', dest='isa_from', default=[], help='')
        self.add_option('--keep-named-from', action='append', type='int', dest='name_from', default=[], help='')

    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagWarn(), *args)
        onto.check_required()
        if options.include_obsolete:
            obsolete_reference_option = DanglingReferenceWarn()
        else:
            obsolete_reference_option = DanglingReferenceFail()
        onto.resolve_references(DanglingReferenceFail(), obsolete_reference_option)
        onto.write_obo(stdout)
        stanzas = list(onto.stanzas.itervalues())
        stanzas.sort(cmp=stanza_comparator(options.sort_by))
        synonym_sources = set(args[i] for i in options.synonyms_from)
        isa_sources = set(args[i] for i in options.isa_from)
        name_sources = set(args[i] for i in options.name_from)
        for stanza in stanzas:
            if stanza.is_obsolete and not options.include_obsolete:
                continue
            if isinstance(stanza, BuiltinStanza):
                continue
            if stanza.source == '<<builtin>>':
                continue
            if isinstance(stanza, Term) and name_sources and stanza.name.source not in name_sources:
                stanza.is_obsolete = True
            if synonym_sources:
                stanza.synonyms[:] = [s for s in stanza.synonyms if (s.source in synonym_sources)]
            if isa_sources and 'is_a' in stanza.references:
                stanza.references['is_a'][:] = [r for r in stanza.references['is_a'] if (r.source in isa_sources)]
            stanza.write_obo(stdout)
        stdout.write('\n')

if __name__ == '__main__':
    OBO2OBO().run()
