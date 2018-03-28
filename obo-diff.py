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


class TermDiff:
    def __init__(self, term1, term2):
        self.term1 = term1
        self.term2 = term2
        self.deletion = (term2 is None)
        self.addition = (term1 is None)
        if self.deletion or self.addition:
            self.name_change = False
            self.added_synonyms = ()
            self.removed_synonyms = ()
            self.added_parents = ()
            self.removed_parents = ()
            self.added_children = ()
            self.removed_children = ()
        else:
            self.name_change = (term1.name.value != term2.name.value)
            syns1 = set(s.text for s in term1.synonyms)
            syns2 = set(s.text for s in term2.synonyms)
            self.added_synonyms = syns2 - syns1
            self.removed_synonyms = syns1 - syns2
            parentids1 = set(p.id.value for p in term1.parents())
            parentids2 = set(p.id.value for p in term2.parents())
            self.added_parents = tuple(p for p in term2.parents() if (p.id.value not in parentids1))
            self.removed_parents = tuple(p for p in term1.parents() if (p.id.value not in parentids2))
            childrenids1 = set(p.id.value for p in term1.children())
            childrenids2 = set(p.id.value for p in term2.children())
            self.added_children = tuple(p for p in term2.children() if (p.id.value not in childrenids1))
            self.removed_children = tuple(p for p in term1.children() if (p.id.value not in childrenids2))

    def changed(self):
        return self.deletion or self.addition or self.name_change or self.added_synonyms or self.removed_synonyms or self.added_parents or self.removed_parents or self.added_children or self.removed_children

    def id(self):
        if self.addition:
            return self.term2.id.value
        return self.term1.id.value

    def name(self):
        if self.addition:
            return self.term2.name.value
        return self.term1.name.value

    def presence(self):
        if self.addition:
            return 'ADDITION'
        if self.deletion:
            return 'DELETION'
        return ''

    def new_name(self):
        if self.name_change:
            return self.term2.name.value
        return ''

    def new_synonyms(self):
        return ', '.join(self.added_synonyms)

    def former_synonyms(self):
        return ', '.join(self.removed_synonyms)

    def new_parents(self):
        return ', '.join(('%s (%s)' % (p.id.value, p.name.value)) for p in self.added_parents)

    def former_parents(self):
        return ', '.join(('%s (%s)' % (p.id.value, p.name.value)) for p in self.removed_parents)

    def new_children(self):
        return ', '.join(('%s (%s)' % (p.id.value, p.name.value)) for p in self.added_children)

    def former_children(self):
        return ', '.join(('%s (%s)' % (p.id.value, p.name.value)) for p in self.removed_children)
    
class OBODiff(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')

    def _load_onto(self, filename):
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagWarn(), filename)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())
        return onto

    def _differences(self, onto1, onto2):
        for term1 in onto1.stanzas.itervalues():
            if not isinstance(term1, Term):
                continue
            termid = term1.id.value
            if termid in onto2.stanzas:
                term2 = onto2.stanzas[termid]
            else:
                term2 = None
            d = TermDiff(term1, term2)
            if d.changed():
                yield d
        for term2 in onto2.stanzas.itervalues():
            if not isinstance(term2, Term):
                continue
            termid = term2.id.value
            if termid not in onto1.stanzas:
                yield TermDiff(None, term2)

    def run(self):
        options, args = self.parse_args()
        if len(args) != 2:
            raise Exception('two ontologies are required')
        onto1, onto2 = (self._load_onto(filename) for filename in args)
        all_diff = tuple(self._differences(onto1, onto2))
        if not all_diff:
            stderr.write('ontologies are equivalent\n')
        else:
            print 'ID\tNAME\tPRESENCE\tNEW NAME\tNEW SYNONYMS\tFORMER SYNONYMS\tNEW PARENTS\tFORMER PARENTS\tNEW CHILDREN\tFORMER CHILDREN'
            for diff in all_diff:
                print '\t'.join((diff.id(), diff.name(), diff.presence(), diff.new_name(), diff.new_synonyms(), diff.former_synonyms(), diff.new_parents(), diff.former_parents(), diff.new_children(), diff.former_children()))


if __name__ == '__main__':
    OBODiff().run()
