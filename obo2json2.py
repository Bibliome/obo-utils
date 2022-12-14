#!/usr/bin/python

# MIT License
#
# Copyright (c) 2017-2023 Institut national de recherche pour l’agriculture, l’alimentation et l’environnement (Inrae)
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

import json
import obo
import argparse
import sys


class OBO2Json(argparse.ArgumentParser):
    def __init__(self):
        argparse.ArgumentParser.__init__(self, description='converts OBO ontology to Json for AlvisIR interface')
        self.add_argument('obo_files', metavar='OBO', nargs='+', default=[], help='OBO ontology file')
        self.add_argument('--root', metavar='ID', dest='root', required=True, help='identifier of the root term of the ontology')

    def run(self):
        args = self.parse_args()
        ontology = obo.Ontology()
        ontology.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), obo.InvalidXRefWarn(), *args.obo_files)
        ontology.check_required()
        ontology.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())
        terms = {}
        for term in ontology.iterterms():
            terms[term.id.value] = {
                'extid': term.id.value,
                'intid': term.id.value,
                'name': term.name.value,
                'syns': [syn.text for syn in term.synonyms],
                'children': []
            }
        for term in ontology.iterterms():
            d = terms[term.id.value]
            if 'is_a' in term.references:
                for link in term.references['is_a']:
                    parent_d = terms[link.reference]
                    parent_d['children'].append(d)
        root_d = terms[args.root]
        self._desc(root_d)
        self._sublvl(root_d)
        json.dump(root_d, sys.stdout)

    def _desc(self, d):
        r = sum((self._desc(c) + 1) for c in d['children'])
        d['descendantnb'] = r
        return r

    def _sublvl(self, d):
        if len(d['children']) == 0:
            r = 0
        else:
            r = 1 + max(self._sublvl(c) for c in d['children'])
        d['sublevelnb'] = r
        return r


if __name__ == '__main__':
    OBO2Json().run()
