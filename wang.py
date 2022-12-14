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

from optparse import OptionParser
from obo import Ontology, UnhandledTagFail, DanglingReferenceFail, DanglingReferenceWarn, DeprecatedTagSilent


class Wang_Normalization(dict):
    def __init__(self, ontology, weight):
        dict.__init__(self, ((term, self._get_s_values(term)) for term in ontology.iterterms()))
        self.ontology = ontology
        self.weight = weight

    def _ancestors(self, term, depth):
        yield term, depth
        if 'is_a' in term.references:
            for r in term.references['is_a']:
                for p in self._ancestors(r.reference_object, depth + 1):
                    yield p

    def _get_s_values(self, term):
        result = {}
        for ancestor, depth in self._ancestors(term, 0):
            if ancestor in result:
                result[ancestor] = min(result[ancestor], depth)
            else:
                result[ancestor] = depth
        return result

    def value(self, term):
        if term not in self:
            return 0
        return sum((self.weight ** depth) for depth in self[term].values())

    def s_values(self, term):
        if term not in self:
            return {}
        return dict((t, (self.weight ** d)) for t, d in self[term].items())

    def term_similarity(self, term1, term2):
        if term1 not in self:
            return 0
        if term2 not in self:
            return 0
        if term1 == term2:
            return 1.0
        v1 = self.value(term1)
        v2 = self.value(term2)
        sv1 = self.s_values(term1)
        sv2 = self.s_values(term2)
        inter = set(sv1) & set(sv2)
        return sum((sv1[t] + sv2[t]) for t in inter) / (v1 + v2)

    def score(self, a1, a2):
        term1 = self.ontology.stanzas[a1.referent]
        term2 = self.ontology.stanzas[a2.referent]
        return self.term_similarity(term1, term2)


class Wang(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.set_defaults(weight=0.8, symmetric=False, print_names=False)
        self.add_option('--print-names', action='store_true', dest='print_names', help='print term names')
        self.add_option('--weight', action='store', type='float', dest='weight', help='ancestor weight (default: %default)')
        self.add_option('--symmetric', action='store_true', dest='symmetric', help='print symmetric matrix')

    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        onto.load_files(UnhandledTagFail(), DeprecatedTagSilent(), *args)
        onto.check_required()
        onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())
        wang = Wang_Normalization(onto, options.weight)
        terms = tuple(t for t in onto.iterterms())
        for i, termA in enumerate(terms):
            for j in range(i, len(terms)):
                termB = terms[j]
                d = wang.term_similarity(termA, termB)
                if options.print_names:
                    print('%s\t%s\t%s\t%s\t%f' % (termA.id.value, termA.name.value, termB.id.value, termB.name.value, d))
                    if options.symmetric and i != j:
                        print('%s\t%s\t%s\t%s\t%f' % (termB.id.value, termB.name.value, termA.id.value, termA.name.value, d))
                else:
                    print('%s\t%s\t%f' % (termA.id.value, termB.id.value, d))
                    if options.symmetric and i != j:
                        print('%s\t%s\t%f' % (termB.id.value, termA.id.value, d))


if __name__ == '__main__':
    Wang().run()
