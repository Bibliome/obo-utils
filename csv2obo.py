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
from datetime import datetime
from os import getenv


class CSV2OBO(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage='usage: %prog [options]')
        self.add_option('--id', action='store', type='int', dest='id_column', help='term identifier column')
        self.add_option('--id-prefix', action='store', type='str', dest='id_prefix', default=None, help='prepend identifier prefix')
        self.add_option('--name', action='store', type='int', dest='name_column', help='term name column')
        self.add_option('--isa', action='append', type='int', dest='isa_columns', help='parent column (multiple allowed)')
        self.add_option('--synonym', action='append', type='int', dest='synonym_columns', help='synonym column (multiple allowed)')
        self.add_option('--definition', action='store', type='int', dest='definition_column', help='definition column')
        self.add_option('--delimiter', action='store', type='string', dest='delimiter', default='\t', help='field delimiter')
        self.add_option('--skip-first', action='store_true', dest='skip_first', default=False, help='skip first record')
        self.add_option('--output', action='store', type='str', dest='output', default=None, help='output file')

    def run(self):
        options, args = self.parse_args()
        self.init_ontology(options)
        self.load(options, args)
        self.ontology.check_required()
        self.ontology.resolve_references(DanglingReferenceWarn(), DanglingReferenceWarn())
        if options.output is None:
            self.write(stdout)
        else:
            with open(options.output, 'w') as f:
                self.write(f)
            
    def init_ontology(self, options):
        self.ontology = Ontology()
        header_reader = HeaderReader(self.ontology, UnhandledTagFail(), DeprecatedTagWarn())
        header_reader.read_date(SourcedValue('<commandline>', 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        header_reader.read_auto_generated_by(SourcedValue('<commandline>', 0, 'csv2obo.py'))
        header_reader.read_saved_by(SourcedValue('<commandline>', 0, getenv('USER')))

    def load(self, options, args):
        if len(args) == 0:
            self.load_records(options, '<stdin>', stdin)
        else:
            for filename in args:
                with open(filename) as f:
                    self.load_records(options, filename, f)
        
    def load_records(self, options, filename, f):
        r = csv.reader(f, delimiter=options.delimiter)
        lineno = 0
        for row in r:
            lineno += 1
            self.load_record(options, filename, lineno, row)
        
    def load_record(self, options, filename, lineno, row):
        if lineno == 1 and options.skip_first:
            return
        term_reader = TermReader(filename, lineno, self.ontology, UnhandledTagFail(), DeprecatedTagWarn())
        if not self.read_id(options, row, term_reader):
            stderr.write('skipping line %d because id is empty\n' % lineno)
            return
        self.read_name(options, row, term_reader)
        self.read_def(options, row, term_reader)
        self.read_isas(options, row, term_reader)
        self.read_synonyms(options, row, term_reader)
        
    def read_id(self, options, row, term_reader):
        id = row[options.id_column]
        if id == '':
            return False
        #stderr.write('id = %s\n' % id)
        id = self.get_ref(options, id)
        term_reader.read_id(SourcedValue(term_reader.source, term_reader.lineno, id))
        return True

    def get_ref(self, options, ref):
        if options.id_prefix is None:
            return ref
        if ref.find(':') >= 0:
            return ref
        return ':'.join((options.id_prefix, ref))
        
    def read_name(self, options, row, term_reader):
        name = row[options.name_column]
        if name != '':
            #stderr.write('name = %s\n' % name)
            name = name.replace('[', '(').replace(']', ')')
            term_reader.read_name(SourcedValue(term_reader.source, term_reader.lineno, name))

    def read_def(self, options, row, term_reader):
        definition = row[options.definition_column]
        if definition != '':
            #stderr.write('def = %s\n' % definition)
            definition = definition.replace('"', '\'')
            term_reader.read_def(SourcedValue(term_reader.source, term_reader.lineno, '"%s"' % definition))

    def read_isas(self, options, row, term_reader):
        for col in options.isa_columns:
            ref = row[col]
            if ref != '':
                ref = self.get_ref(options, ref)
                term_reader.read_is_a(SourcedValue(term_reader.source, term_reader.lineno, ref))

    def read_synonyms(self, options, row, term_reader):
        for col in options.synonym_columns:
            syn = row[col]
            if syn != '':
                term_reader.read_synonym(SourcedValue(term_reader.source, term_reader.lineno, '"%s"' % syn.replace('"', '\'')))

    def write(self, f):
        self.ontology.write_obo(f)
        for term in self.ontology.iterterms():
            #stderr.write('id = %s\n' % term.id.value)
            term.write_obo(f)
        f.write('\n')

if __name__ == '__main__':
    CSV2OBO().run()
