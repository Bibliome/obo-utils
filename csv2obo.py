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


from obo import *
import csv
from optparse import OptionParser
from sys import stdin, stderr, stdout




class CSV2OBO(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--id', action='store', type='int', dest='id_column', help='term identifier column')
        self.add_option('--name', action='store', type='int', dest='name_column', help='term name column')
        self.add_option('--isa', action='append', type='int', dest='isa_columns', help='parent column (multiple allowed)')
        self.add_option('--synonym', action='append', type='int', dest='synonym_columns', help='synonym column (multiple allowed)')
        self.add_option('--definition', action='store', type='int', dest='definition_column', help='definition column')
        self.add_option('--delimiter', action='store', type='string', dest='delimiter', default='\t', help='field delimiter')
        self.add_option('--skip-first', action='store_true', dest='skip_first', default=False, help='skip first record')

    def run(self):
        options, args = self.parse_args()
        onto = Ontology()
        if len(args) == 0:
            self.load_records(options, onto, '<stdin>', stdin)
        else:
            for filename in args:
                with open(filename) as f:
                    self.load_records(options, onto, filename, f)
        onto.check_required()
        onto.resolve_references(DanglingReferenceWarn(), DanglingReferenceWarn())
        for term in onto.iterterms():
            #stderr.write('id = %s\n' % term.id.value)
            term.write_obo(stdout)
        stdout.write('\n')

    def load_records(self, options, ontology, filename, f):
        r = csv.reader(f, delimiter=options.delimiter)
        lineno = 0
        for row in r:
            lineno += 1
            if lineno == 1 and options.skip_first:
                continue
            term_reader = TermReader(filename, lineno, ontology, UnhandledTagFail(), DeprecatedTagWarn())
            id = row[options.id_column]
            if id == '':
                stderr.write('skipping line %d because id is empty\n' % lineno)
                continue
            #stderr.write('id = %s\n' % id)
            term_reader.read_id(SourcedValue(filename, lineno, id))
            name = row[options.name_column]
            if name != '':
                #stderr.write('name = %s\n' % name)
                term_reader.read_name(SourcedValue(filename, lineno, name.replace('[', '(').replace(']', ')')))
            definition = row[options.definition_column]
            if definition != '':
                #stderr.write('def = %s\n' % definition)
                term_reader.read_def(SourcedValue(filename, lineno, '"%s"' % definition.replace('"', '\'')))
            for col in options.isa_columns:
                ref = row[col]
                if ref != '':
                    term_reader.read_is_a(SourcedValue(filename, lineno, ref))
            for col in options.synonym_columns:
                syn = row[col]
                if syn != '':
                    term_reader.read_synonym(SourcedValue(filename, lineno, '"%s"' % syn.replace('"', '\'')))

            
if __name__ == '__main__':
    CSV2OBO().run()
