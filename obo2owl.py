#!/usr/bin/python

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

import obo
from optparse import OptionParser
from xml.sax.saxutils import escape


OWL_HEADER = '''<?xml version="1.0"?>
<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
  <owl:Ontology/>
'''

OWL_FOOTER = '''</rdf:RDF>
'''


class OBO2OWL(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--synonyms', action='store_true', dest='synonyms', help='Include synonyms (kinda broken)')

    def _id(self, id_):
        return 'http://purl.obolibrary.org/obo/' + id_.replace(':', '_', 1)

    def run(self):
        options, args = self.parse_args()
        onto = obo.Ontology()
        onto.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), obo.InvalidXRefWarn(), *args)
        onto.check_required()
        onto.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())
        print(OWL_HEADER)
        for stanza in onto.stanzas.values():
            if isinstance(stanza, obo.Term):
                print('  <owl:Class rdf:about="%s">' % self._id(stanza.id.value))
                print('    <rdfs:label rdf:datatype="http://www.w3.org/2001/XMLSchema#string">%s</rdfs:label>' % escape(stanza.name.value))
                if options.synonyms:
                    for syn in stanza.synonyms:
                        if syn.scope == 'EXACT':
                            tag = 'synonymExact'
                        elif syn.scope == 'RELATED':
                            tag = 'synonymRelated'
                        elif syn.scope == 'NARROW':
                            tag = 'synonymNarrower'
                        else:
                            raise RuntimeError(syn.scope)
                        print('    <%s rdf:datatype="http://www.w3.org/2001/XMLSchema#string">%s</%s>' % (tag, escape(syn.text), tag))
                if 'is_a' in stanza.references:
                    for ref in stanza.references['is_a']:
                        print('    <rdfs:subClassOf>')
                        print('      <owl:Class rdf:about="%s"/>' % self._id(ref.reference))
                        print('    </rdfs:subClassOf>')
                print('  </owl:Class>')
        print(OWL_FOOTER)


if __name__ == '__main__':
    OBO2OWL().run()
