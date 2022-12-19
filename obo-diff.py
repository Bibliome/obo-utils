#!/usr/bin/env python

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

from optparse import OptionParser
import obo
import sys


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
            self.added_siblings = ()
            self.removed_siblings = ()
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
            siblingids1 = set(s.id.value for p in term1.parents() for s in p.children())
            siblingids2 = set(s.id.value for p in term2.parents() for s in p.children())
            self.added_siblings = tuple(term2.ontology.stanzas[tid] for tid in siblingids2 if tid not in siblingids1)
            self.removed_siblings = tuple(term1.ontology.stanzas[tid] for tid in siblingids1 if tid not in siblingids2)

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

    def new_siblings(self):
        return ', '.join(('%s (%s)' % (p.id.value, p.name.value)) for p in self.added_siblings)

    def former_siblings(self):
        return ', '.join(('%s (%s)' % (p.id.value, p.name.value)) for p in self.removed_siblings)


def _term_id(term):
    return term.id.value


def _term_name(term):
    return term.name.value


def _build_name_dict(onto):
    result = {}
    for term in onto.iterterms():
        name = term.name.value
        if name in result:
            sys.stderr.write('terms with same name (%s): %s, %s\n' % (name, term.id.value, result[name].id.value))
        else:
            result[name] = term
    return result


class TermMatch:
    def __init__(self, onto):
        self.onto = onto
        self.map = self._build_map(onto)

    def _build_map(self, onto):
        raise NotImplementedError()

    def _key(self, term):
        raise NotImplementedError()

    def match(self, term):
        key = self._key(term)
        if key in self.map:
            return self.map[key]
        return None


class TermIdMatch(TermMatch):
    def __init__(self, onto):
        TermMatch.__init__(self, onto)

    def _build_map(self, onto):
        return onto.stanzas

    def _key(self, term):
        return term.id.value


class TermNameMatch(TermMatch):
    def __init__(self, onto):
        TermMatch.__init__(self, onto)

    def _message(self, term):
        return term.message('%s (%s)' % (term.id.value, term.name.value))

    def _build_map(self, onto):
        result = {}
        for term in onto.iterterms():
            name = self._key(term)
            if name in result:
                sys.stderr.write('terms with same name %s, %s\n' % (self._message(term), self._message(result[name])))
            else:
                result[name] = term
        return result

    def _key(self, term):
        return term.name.value


class TermNameCaseMatch(TermNameMatch):
    def __init__(self, onto):
        TermNameMatch.__init__(self, onto)

    def _key(self, term):
        return term.name.value.lower()


class OBODiff(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.set_defaults(term_match=TermIdMatch)
        self.add_option('--match-name', action='store_const', dest='term_match', const=TermNameMatch, help='match term names instead of ids')
        self.add_option('--match-name-case', action='store_const', dest='term_match', const=TermNameCaseMatch, help='match term names (case insensitive) instead of ids')

    def _load_term_match(self, filename, klass):
        onto = obo.Ontology()
        onto.load_files(obo.UnhandledTagFail(), obo.DeprecatedTagWarn(), filename)
        onto.check_required()
        onto.resolve_references(obo.DanglingReferenceFail(), obo.DanglingReferenceWarn())
        return klass(onto)

    def _differences(self, term_match1, term_match2):
        for term1 in term_match1.onto.iterterms():
            term2 = term_match2.match(term1)
            d = TermDiff(term1, term2)
            if d.changed():
                yield d
        for term2 in term_match2.onto.iterterms():
            term1 = term_match1.match(term2)
            if term1 is None:
                yield TermDiff(None, term2)

    def run(self):
        options, args = self.parse_args()
        if len(args) != 2:
            raise Exception('two ontologies are required')
        term_match1, term_match2 = (self._load_term_match(filename, options.term_match) for filename in args)
        all_diff = tuple(self._differences(term_match1, term_match2))
        if not all_diff:
            sys.stderr.write('ontologies are equivalent\n')
        else:
            print('ID\tNAME\tPRESENCE\tNEW NAME\tNEW SYNONYMS\tFORMER SYNONYMS\tNEW PARENTS\tFORMER PARENTS\tNEW CHILDREN\tFORMER CHILDREN\tNEW SIBLINGS\tFORMER SIBLINGS')
            for diff in all_diff:
                print('\t'.join((diff.id(), diff.name(), diff.presence(), diff.new_name(), diff.new_synonyms(), diff.former_synonyms(), diff.new_parents(), diff.former_parents(), diff.new_children(), diff.former_children(), diff.new_siblings(), diff.former_siblings())))


if __name__ == '__main__':
    OBODiff().run()
