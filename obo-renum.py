#!/usr/bin/env python2


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
import obo
import sys


def _depth(term):
    return len(list(term.ancestors()))


def _cmp(t1, t2):
    r = _depth(t1) - _depth(t2)
    if r != 0:
        return r
    return obo.cmp(t1.name.value, t2.name.value)


class OBORenum(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options] [obofiles]')
        self.add_option('--prefix', action='store', default='RENUM', dest='prefix', help='identifier prefix (default: %default)')
        self.add_option('--digits', action='store', type='int', default=6, dest='digits', help='number of digits in generated identifiers (default: %default)')
        self.add_option('--start', action='store', type='int', default=0, dest='start', help='first number of generated identifier (default: %default)')
        self.add_option('--preserve', action='store_true', dest='preserve', default=False, help='preserve identifiers with the prefix')
        self.add_option('--mapping-file', action='store', dest='mapping_file', help='write identifier mapping in this file')

    def run(self):
        options, args = self.parse_args()
        onto = obo.Ontology()
        onto.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), obo.InvalidXRefWarn(), *args)
        onto.check_required()
        onto.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())

        terms = [term for term in onto.iterterms() if not(isinstance(term, obo.BuiltinStanza) or term.source == '<<builtin>>')]
        if options.preserve:
            prefix = options.prefix + ':'
            terms = [term for term in terms if not(term.id.value.startswith(prefix))]
        terms.sort(cmp=_cmp)
        format = '%s:%%0%dd' % (options.prefix, options.digits)
        mapping = dict((term.id.value, format % n) for n, term in enumerate(terms, options.start))

        onto.write_obo(sys.stdout)
        for stanza in onto.stanzas.values():
            if isinstance(stanza, obo.BuiltinStanza) or stanza.source == '<<builtin>>':
                continue
            if stanza.id.value in mapping:
                stanza.id.value = mapping[stanza.id.value]
            for links in stanza.references.values():
                for link in links:
                    if link.reference in mapping:
                        link.reference = mapping[link.reference]
            stanza.write_obo(sys.stdout)

        if options.mapping_file is not None:
            f = open(options.mapping_file, 'w')
            for p in mapping.items():
                f.write('%s\t%s\n' % p)
            f.close()


if __name__ == '__main__':
    OBORenum().run()
