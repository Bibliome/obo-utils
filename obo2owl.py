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


OWL_HEADER = '''<?xml version="1.0"?>
<rdf:RDF
    xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#"
    xmlns:protege="http://protege.stanford.edu/plugins/owl/protege#"
    xmlns:j.0="http://atol#"
    xmlns:xsp="http://www.owl-ontologies.com/2005/08/07/xsp.owl#"
    xmlns:owl2xml="http://www.w3.org/2006/12/owl2-xml#"
    xmlns:swrlb="http://www.w3.org/2003/11/swrlb#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
    xmlns:swrl="http://www.w3.org/2003/11/swrl#"
    xmlns:obo="http://purl.org/obo/"
    xmlns="file:/C:/Lea/ontologies/versions%20ATOL/atol_v3.0.obo#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xml:base="file:/C:/Lea/ontologies/versions%20ATOL/atol_v3.0.obo">
  <owl:Ontology rdf:about="file:/C:/Lea/ontologies/versions%20ATOL/atol_v3.0.obo"/>
'''

OWL_FOOTER = '''</rdf:RDF>
'''


class OBO2OWL(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')

    def run(self):
        options, args = self.parse_args()
        onto = obo.Ontology()
        onto.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), *args)
        onto.check_required()
        onto.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())
        print(OWL_HEADER)
        for stanza in onto.stanzas.values():
            if isinstance(stanza, obo.Term):
                print('  <owl:Class rdf:about="%s">' % stanza.id.value)
                print('    <rdfs:label rdf:datatype="http://www.w3.org/2001/XMLSchema#string">%s</rdfs:label>' % stanza.name.value)
                for syn in stanza.synonyms:
                    if syn.scope == 'EXACT':
                        tag = 'synonymExact'
                    elif syn.scope == 'RELATED':
                        tag = 'synonymRelated'
                    print('    <%s rdf:datatype="http://www.w3.org/2001/XMLSchema#string">%s</%s>' % (tag, syn.text, tag))
                if 'is_a' in stanza.references:
                    for ref in stanza.references['is_a']:
                        print('    <rdfs:subClassOf>')
                        print('      <owl:Class rdf:about="%s"/>' % ref.reference)
                        print('    </rdfs:subClassOf>')
                print('  </owl:Class>')
        print(OWL_FOOTER)


if __name__ == '__main__':
    OBO2OWL().run()
