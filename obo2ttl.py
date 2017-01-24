#!/usr/bin/python

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

LEX_STATEMENTS='''lex:synonym
      a      rdfs:DataProperty ;
      rdfs:domain rdfs:Class ;
      rdfs:range xsd:string .

lex:relatedSynonym rdfs:subPropertyOf lex:synonym .

lex:exactSynonym rdf:subPropertyOf lex:synonym .
'''

PREFIXES = {
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'lex': 'http://inra.fr/lexicalization.owl#'
}

def _prefix_callback(option, opt_str, value, parser):
    name, prefix = value
    if name and prefix:
        PREFIXES[name] = prefix


def _get_id(options, id):
    if options.terms_namespace:
        return '%s:%s' % (options.terms_namespace, id)
    for name, prefix in PREFIXES.iteritems():
        if id.startswith(prefix):
            return '%s:%s' % (name, id[len(prefix):])
    return id

class OBO2OWL(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--lex-statements', action='store_true', dest='lex_statements', default=False, help='')
        self.add_option('--terms-namespace', action='store', dest='terms_namespace', type='string', default=None, help='', metavar='NAME')
        self.add_option('--prefix', '-p', action='callback', nargs=2, type='string', callback=_prefix_callback, help='', metavar='NAME PEFIX')

    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagWarn(), *args)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail())
        for p in PREFIXES.iteritems():
            print '@prefix %s: <%s> .' % p
        if options.lex_statements:
            print LEX_STATEMENTS
        print
        for t in onto.iterterms():
            print _get_id(options, t.id.value)
            print '      rdfs:label "%s"^^xsd:string' % t.name.value
            for syn in t.synonyms:
                print '      lex:%sSynonym "%s"^^xsd:string' % (syn.scope.lower(), syn.text)
            if 'is_a' in t.references:
                for link in t.references['is_a']:
                    p = link.reference_object
                    print '      rdfs:subClassOf %s # %s' % (_get_id(options, p.id.value), p.name.value)
            print


if __name__ == '__main__':
    OBO2OWL().run()
