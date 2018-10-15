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

from optparse import OptionParser
from obo import *

class OBO2Indent(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.set_defaults(root=None)
        self.add_option('--root', action='store', type='string', dest='root', help='export subtree')

    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagSilent(), *args)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())
        if options.root is None:
            for t in onto.iterterms():
                if 'is_a' not in t.references:
                    self.display(onto, t, '')
        else:
            self.display(onto, onto.stanzas[options.root], '')

    def display(self, onto, term, indent):
        print indent + '----------'
        print indent + term.id.value
        print indent + term.name.value
        for syn in term.synonyms:
            print indent + syn.text
        print indent + '----------'
        indent = indent + '\t'
        for t in onto.iterterms():
            if 'is_a' in t.references:
                for link in t.references['is_a']:
                    if link.reference_object == term:
                        self.display(onto, t, indent)



if __name__ == '__main__':
    OBO2Indent().run()
