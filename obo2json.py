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
from optparse import OptionParser
import obo


class OBO2Indent(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.set_defaults(root=None)
        self.add_option('--root', action='store', type='string', dest='root', help='export subtree')

    def run(self):
        options, args = self.parse_args()
        onto = obo.Ontology()
        onto.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), obo.InvalidXRefWarn(), *args)
        onto.check_required()
        onto.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())
        if options.root is None:
            for t in onto.iterterms():
                if 'is_a' not in t.references:
                    nbSubLevel, nbDescendant, displayStr = self.display(onto, t, '')
                    print(displayStr)
        else:
            nbSubLevel, nbDescendant, displayStr = self.display(onto, onto.stanzas[options.root], '')
            print(displayStr)

    def display(self, onto, term, indent):
        resultStr = indent + '{'
        resultStr += '"extid" : ' + json.dumps(term.id.value) + ', ' + "\n"
        resultStr += indent + '"intid" : ' + json.dumps(term.id.value) + ', ' + "\n"
        resultStr += indent + '"name" : ' + json.dumps(term.name.value)

        synonymes = []
        for syn in term.synonyms:
            if len(syn.text) > 0:
                synonymes.append(syn.text)
        if len(synonymes):
            resultStr += ', ' + "\n"
            resultStr += indent + '"syns" : ' + json.dumps(synonymes)

        childrenStr = ''
        sepChild = ''
        innerIndent = indent + '\t'
        nbDescendant = 0
        nbSubLevel = 0
        for t in onto.iterterms():
            if 'is_a' in t.references:
                for link in t.references['is_a']:
                    if link.reference_object == term:
                        nbDescendant += 1
                        childrenStr += innerIndent + sepChild + "\n"
                        nbChildSubLevel, nbChildChildren, childStr = self.display(onto, t, innerIndent)
                        childrenStr += childStr
                        nbDescendant += nbChildChildren
                        nbSubLevel = max(nbSubLevel, nbChildSubLevel)
                        sepChild = ', '

        if len(childrenStr) > 0:
            resultStr += ', ' + "\n"
            resultStr += indent + '"children" :[' + "\n" + childrenStr
            resultStr += indent + '] '

            resultStr += ', ' + "\n"
            resultStr += indent + '"descendantnb" : ' + str(nbDescendant)
            resultStr += ', ' + "\n"
            resultStr += indent + '"sublevelnb" : ' + str(nbSubLevel)

            resultStr += "\n"
            resultStr += indent + '}' + "\n"

        return nbSubLevel + 1, nbDescendant, resultStr


if __name__ == '__main__':
    OBO2Indent().run()
