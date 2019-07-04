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


import re
from sys import stdin, stdout, stderr
from io import StringIO
from time import strftime
from os import getenv
from collections import OrderedDict

class OBOException(Exception):
    '''Generic exception for all things OBO'''
    def __init__(self, sourced, msg):
        Exception.__init__(self, sourced.message(msg))

class OBONotImplemented(OBOException):
    '''Exception raised when an OBO feature is not implemented here'''
    def __init__(self, sourced, tag):
        OBOException.__init__(self, sourced, tag + ' not implemented yet')

class OBOInvalidFormat(OBOException):
    '''Exception raised when an OBO file is not well-formed'''
    def __init__(self, sourced, tag):
        OBOException.__init__(self, sourced, 'invalid ' + tag + ' format')


class UnhandledTagOption:
    '''Abstract class that handles unhandled OBO predicate tag'''
    def __init__(self):
        pass

    def handle(self, tagset, tag, value):
        '''Handles an unhadled tag

        :Parameters:
        tagset: tagset (e.g. Term)
        tag: tag name
        value: string value of the tag'''
        raise NotImplemented()

class UnhandledTagFail(UnhandledTagOption):
    '''Unhandled tag: raise exception'''
    def __init__(self):
        UnhandledTagOption.__init__(self)

    def handle(self, tagset, tag, value):
        raise OBOException(value.message('unhandled tag ' + tag))

class UnhandledTagWarn(UnhandledTagOption):
    '''Unhandled tag: print warning and ignore'''
    def __init__(self):
        UnhandledTagOption.__init__(self)

    def handle(self, tagset, tag, value):
        value.warning('unhandled tag ' + tag)

class UnhandledTagRecord(UnhandledTagOption):
    '''Unhandled tag: record in 'unhandled_tags' '''
    def __init__(self):
        UnhandledTagOption.__init__(self)

    def handle(self, tagset, tag, value):
        tagset.unhandled_tags.append((tag, value))

class UnhadledTagWarnAndRecord(UnhandledTagWarn, UnhandledTagRecord):
    '''Unhandled tag: print warning and record in 'unhandled_tags' '''
    def __init__(self):
        UnhandledTagWarn.__init__(self)
        UnhandledTagRecord.__init__(self)

    def handle(self, tagset, tag, value):
        UnhandledTagWarn.handle(self, tagset, tag, value)
        UnhandledTagRecord.handle(self, tagset, tag, value)

class UnhandledTagIgnore(UnhandledTagOption):
    '''Unhandled tag: silently ignore'''
    def __init__(self):
        UnhandledTagOption.__init__(self)

    def handle(self, tagset, tag, value):
        pass


class DeprecatedTagOption:
    '''Abstract class that handles deprecated tags'''
    def __init__(self):
        pass

    def handle(self, tagset, tag, value):
        '''Handles a deprecated tag

        :Parameters:
        tagset: tagset (e.g. Term)
        tag: tag name
        value: string value'''
        raise NotImplemented()

class DeprecatedTagWarn(DeprecatedTagOption):
    '''Deprecated tag: print warning'''
    def __init__(self):
        DeprecatedTagOption.__init__(self)

    def handle(self, tagset, tag, value):
        value.warning('deprecated tag: ' + tag)

class DeprecatedTagSilent(DeprecatedTagOption):
    '''Deprecated tag: silently ignore'''
    def __init__(self):
        DeprecatedTagOption.__init__(self)

    def handle(self, tagset, tag, value):
        pass
    

class TagReader:
    def __init__(self, tagset, ontology, unhandled_tag_option, deprecated_tag_option):
        self.tagset = tagset
        self.ontology = ontology
        self.tags = []
        self.unhandled_tag_option = unhandled_tag_option
        self.deprecated_tag_option = deprecated_tag_option

    def read(self, tag, value):
        method_name = 'read_' + tag.replace('-', '_')
        if hasattr(self, method_name):
            getattr(self, method_name)(value)
        else:
            self.default_read(tag, value)
    
    def default_read(self, tag, value):
        value.warning('unhandled tag ' + tag + ' in ' + self.tagset.__class__.__name__)



def unquoted_string(name, phrase=False):
    S = r'(?:\\.|[^ \[\]])+'
    if phrase:
        return r'(?P<' + name + r'>' + S + r'(?:\s+' + S + ')*)'
    return r'(?P<' + name + r'>' + S + ')'

def quoted_string(name):
    return r'"(?P<' + name + '>.*?)(?<!\\\)"'

TERMINAL_COMMENT = r'\s*(?:!.*)?$'
SCOPE = r'(?:\s+(?P<scope>EXACT|BROAD|NARROW|RELATED))?'
DBXREF_LIST = r'(?:\s+\[(?P<dbxrefs>(?:[^\[\]]|\\.)*)\])?'

DATE_VALUE_PATTERN = re.compile(r'(?P<date>\d\d:\d\d:\d\d\d\d \d\d:\d\d)' + TERMINAL_COMMENT)
SUBSETDEF_PATTERN = re.compile(unquoted_string('subset') + '\s+' + quoted_string('descr') + TERMINAL_COMMENT)
SYNONYMTYPEDEF_PATTERN = re.compile(unquoted_string('name') + '\s+' + quoted_string('descr') + SCOPE + TERMINAL_COMMENT)
FREE_VALUE_PATTERN = re.compile(r'(?P<value>(?:\\.|[^!\[\]])+)' + DBXREF_LIST + TERMINAL_COMMENT)
BOOLEAN_VALUE_PATTERN = re.compile(r'(?P<value>true|false)' + TERMINAL_COMMENT)
QUOTED_VALUE_PATTERN = re.compile(quoted_string('value') + TERMINAL_COMMENT)
SYNONYM_PATTERN = re.compile(quoted_string('text') + SCOPE + r'(?: ' + unquoted_string('type') + ')?' + DBXREF_LIST + TERMINAL_COMMENT)
DEPRECATED_SYNONYM_PATTERN = re.compile(quoted_string('text') + r'(?: ' + unquoted_string('type') + ')?' + DBXREF_LIST + TERMINAL_COMMENT)
XREF_PATTERN = re.compile(unquoted_string('id') + r'(?: ' + quoted_string('descr') + r')?' + r'(?:\s+' + r'(?P<match>NO MATCH|MATCH NAME|MATCH SYNONYM)(?:\s+' + unquoted_string('matched', True) + r')?)?' + TERMINAL_COMMENT)
INTERSECTION_PATTERN = re.compile('(?:' + unquoted_string('rel') + ' )?' + unquoted_string('id') + TERMINAL_COMMENT)
RELATIONSHIP_PATTERN = re.compile(unquoted_string('rel') + '\s+' + unquoted_string('id') + TERMINAL_COMMENT)
INSTANCE_PROPERTY_VALUE_PATTERN = re.compile(unquoted_string('rel') + '(?: ' + quoted_string('value') + ')?' + '\s+' + unquoted_string('ref') + TERMINAL_COMMENT)
DEFINITION_PATTERN = re.compile(quoted_string('definition') + DBXREF_LIST + TERMINAL_COMMENT)

def match_pattern(pattern, tag, value):
    result = pattern.match(value.value)
    if result is None:
        raise OBOInvalidFormat(value, tag)
    return result

def unescape(s):
    l = []
    esc = False
    for c in s:
        if esc:
            if c == 'n':
                l.append('\n')
            elif c == 't':
                l.append('\t')
            elif c == 'r':
                l.append('\r')
            else:
                l.append(c)
            esc = False
        elif c == '\\':
            esc = True
        else:
            l.append(c)
    return ''.join(l)

def get_quoted_value(tag, value):
    return match_pattern(QUOTED_VALUE_PATTERN, tag, value).group('value')

def get_boolean_value(tag, value):
    return match_pattern(BOOLEAN_VALUE_PATTERN, tag, value).group('value') == 'true'

def get_free_value(tag, value):
    return match_pattern(FREE_VALUE_PATTERN, tag, value).group('value').strip()

def get_date_value(tag, value):
    return get_free_value(tag, value)
#    return match_pattern(DATE_VALUE_PATTERN, source, lineno, tag, value).group('date')


class Sourced:
    def __init__(self, source, lineno):
        self.source = source
        self.lineno = lineno

    def message(self, msg=None):
        if msg:
            return '%s:%d: %s' % (self.source, self.lineno, msg)
        return '%s:%d' % (self.source, self.lineno)

    def warning(self, msg):
        stderr.write(self.message(msg + '\n'))

    def duplicate(self, tag, msg=None):
        r = 'duplicate tag ' + tag + ', see: ' + self.message()
        if msg is None:
            return r
        return '%s (%s)' % (r, msg)


class SourcedValue(Sourced):
    def __init__(self, source, lineno, value):
        Sourced.__init__(self, source, lineno)
        self.value = value

        
class SubsetDef(Sourced):
    def __init__(self, source, lineno, name, description):
        Sourced.__init__(self, source, lineno)
        self.name = name
        self.description = description


class SynonymTypeDef(Sourced):
    def __init__(self, source, lineno, name, description, scope):
        Sourced.__init__(self, source, lineno)
        self.name = name
        self.description = description
        self.scope = scope

class HeaderReader(TagReader):
    def __init__(self, ontology, unhandled_tag_option, deprecated_tag_option):
        TagReader.__init__(self, ontology, ontology, unhandled_tag_option, deprecated_tag_option)

    def read_format_version(self, value):
        self.ontology.format_version = get_free_value('format-version', value)

    def read_data_version(self, value):
        self.ontology.version = get_free_value('data-version', value)

    def read_date(self, value):
        self.ontology.date = get_date_value('date', value)

    def read_saved_by(self, value):
        self.ontology.saved_by = get_free_value('saved-by', value)

    def read_auto_generated_by(self, value):
        self.ontology.auto_generated_by = get_free_value('auto-generated-by', value)

    def read_subsetdef(self, value):
        m = match_pattern(SUBSETDEF_PATTERN, 'subsetdef', value)
        name = m.group(1)
        descr = m.group(2)
        if name in self.ontology.subsetdef:
            value.warning(self.ontology.subsetdef[name].duplicate('subsetdef'))
        else:
            self.ontology.subsetdef[name] = SubsetDef(value.source, value.lineno, name, descr)

    def read_synonymtypedef(self, value):
        m = match_pattern(SYNONYMTYPEDEF_PATTERN, 'synonymtypedef', value)
        name = m.group('name')
        descr = m.group('descr')
        scope = m.group('scope')
        if scope is None:
            scope = 'RELATED'
        if name in self.ontology.synonymtypedef:
            value.warning(self.ontology.synonymtypedef[name].duplicate('synonymtypedef'))
        else:
            self.ontology.synonymtypedef[name] = SynonymTypeDef(value.source, value.lineno, name, descr, scope)

    def read_remark(self, value):
        self.ontology.remark.append(get_free_value('remark', value))

    def read_default_namespace(self, value):
        self.ontology.default_namespace = get_free_value('default-namespace', value)


class StanzaReader(Sourced, TagReader):
    def __init__(self, source, lineno, stanza_type, ontology, unhandled_tag_option, deprecated_tag_option):
        Sourced.__init__(self, source, lineno)
        TagReader.__init__(self, None, ontology, unhandled_tag_option, deprecated_tag_option)
        self.stanza_type = stanza_type
        self.stanza = None

    def read(self, tag, value):
        if tag != 'id' and self.stanza is None:
            raise OBOException(value, 'expected tag id')
        TagReader.read(self, tag, value)

    def read_id(self, value):
        if self.stanza is not None:
            raise OBOException(value, self.stanza.duplicate('id'))
        id = get_free_value('id', value)
        if id in self.ontology.builtin:
            raise OBOException(value, 'this id is reserved')
        srcid = SourcedValue(value.source, value.lineno, id)
        if id in self.ontology.stanzas:
            stanza = self.ontology.stanzas[id]
            if not isinstance(stanza, self.stanza_type):
                raise OBOException(value, 'the same id is used for different types of stanzas, see: ' + stanza.message())
            stanza.id = srcid
            self.stanza = stanza
        else:
            self.stanza = self.stanza_type(self.source, self.lineno, self.ontology, srcid)
        self.tagset = self.stanza
        
    def read_name(self, value):
        name = unescape(get_free_value('name', value))
        if self.stanza.name is not None:
            msg = self.stanza.name.duplicate('name', '%s / %s' % (self.stanza.name.value, name))
            if self.stanza.name.value != name:
                value.warning(msg)
        self.stanza.name = SourcedValue(value.source, value.lineno, name)

    def read_def(self, value):
        if self.stanza.definition is not None:
            raise OBOException(self.stanza.definition.duplicate('def'))
        m = match_pattern(DEFINITION_PATTERN, 'def', value)
        self.stanza.definition = SourcedValue(value.source, value.lineno, m.group('definition'))
        self.stanza.definition_dbxrefs = m.group('dbxrefs')

    def read_is_anonymous(self, value):
        self.stanza.is_anonymous = get_boolean_value('is_anonymous', value)

    def read_alt_id(self, value):
        alt_id = get_free_value('alt_id', value)
        self.stanza.alt_ids.append(alt_id)

    def read_comment(self, value):
        if self.stanza.comment is not None:
            raise OBOException(self.stanza.comment.duplicate('comment'))
        self.stanza.comment = SourcedValue(value.source, value.lineno, get_free_value('comment', value))

    def _read_xref(self, tag, value):
        if tag != 'xref':
            self.deprecated_tag_option.handle(self.ontology, tag, value)
        m = match_pattern(XREF_PATTERN, tag, value)
        XRef(value.source, value.lineno, self.stanza, m.group('id'), m.group('descr'), m.group('match'), m.group('matched'))

    def read_xref(self, value):
        self._read_xref('xref', value)

    def read_is_obsolete(self, value):
        self.stanza.is_obsolete = get_boolean_value('is_obsolete', value)

    def read_replaced_by(self, value):
        id = get_free_value('replaced_by', value)
        self.stanza.replaced_by.append(id)

    def _read_simple_ref(self, tag, value, rel):
        id = get_free_value(tag, value)
        #self.stanza.lookup_reference(rel, id, remove=True)
        StanzaReference(value.source, value.lineno, self.stanza, rel, id)

    def read_namespace(self, value):
        self.stanza.namespace = get_free_value('namespace', value)

    def read_consider(self, value):
        id = get_free_value('consider', value)
        self.stanza.consider.append(id)

    def read_synonym(self, value):
        m = match_pattern(SYNONYM_PATTERN, 'synonym', value)
        type = m.group('type')
        if type is None:
            default_scope = 'RELATED'
        else:
            if type not in self.ontology.synonymtypedef:
                raise OBOException(value, 'undefined synonym type: ' + type)
            default_scope = self.ontology.synonymtypedef[type].scope
        text = unescape(m.group('text'))
        scope = m.group('scope')
        if scope is None:
            scope = default_scope
        dbxrefs = m.group('dbxrefs')
        Synonym(value.source, value.lineno, self.stanza, text, scope, type, dbxrefs)


class InstanceReader(StanzaReader):
    def __init__(self, source, lineno, ontology, unhandled_tag_option, deprecated_tag_option):
        StanzaReader.__init__(self, source, lineno, Instance, ontology, unhandled_tag_option, deprecated_tag_option)

    def read_instance_of(self, value):
        ref = get_free_value('instance_of', value)
        StanzaReference(value.source, value.lineno, self.stanza, 'instance_of', ref)

    def read_property_value(self, value):
        m = match_pattern(INSTANCE_PROPERTY_VALUE_PATTERN, 'property_value', value)
        ref = StanzaReference(value.source, value.lineno, self.stanza, m.group('rel'), m.group('ref'))
        if m.group('value'):
            ref.value = m.group('value')


class TermOrTypeReader(StanzaReader):
    def __init__(self, source, lineno, stanza_type, ontology, unhandled_tag_option, deprecated_tag_option):
        StanzaReader.__init__(self, source, lineno, stanza_type, ontology, unhandled_tag_option, deprecated_tag_option)

    def read_subset(self, value):
        subset = get_free_value('subset', value)
        if subset not in self.ontology.subsetdef:
            raise OBOException(value, 'undefined subset ' + subset + ' (' + str(self.ontology.subsetdef) + ')')
        if subset in self.stanza.subsets:
            value.warning(self.ontology.subsetdef[subset].duplicate('subsetdef'))
        self.stanza.subsets.add(subset)

    def _read_deprecated_synonym(self, tag, value, scope):
        self.deprecated_tag_option.handle(self.ontology, tag, value)
        m = match_pattern(DEPRECATED_SYNONYM_PATTERN, tag, value)
        type = m.group('type')
        if type is not None:
            if type not in self.ontology.synonymtypedef:
                raise OBOException(value, 'undefined synonym type: ' + type)
            default_scope = self.ontology.synonymtypedef[type].scope
        text = m.group('text')
        dbxrefs = m.group('dbxrefs')
        Synonym(value.source, value.lineno, self.stanza, text, scope, type, dbxrefs)

    def read_exact_synonym(self, value):
        self._read_deprecated_synonym('exact_synonym', value, 'EXACT')

    def read_narrow_synonym(self, value):
        self._read_deprecated_synonym('narrow_synonym', value, 'NARROW')

    def read_related_synonym(self, value):
        self._read_deprecated_synonym('related_synonym', value, 'RELATED')

    def read_broad_synonym(self, value):
        self._read_deprecated_synonym('broad_synonym', value, 'BROAD')

    def read_xref_analog(self, value):
        self._read_xref('xref_analog', value)

    def read_xref_unk(self, value):
        self._read_xref('xref_unk', value)

    def read_is_a(self, value):
        self._read_simple_ref('is_a', value, 'is_a')

    def read_relationship(self, value):
        m = match_pattern(RELATIONSHIP_PATTERN, 'relationship', value)
        StanzaReference(value.source, value.lineno, self.stanza, m.group('rel'), m.group('id'))

    def read_use_term(self, value):
        self._read_consider('use_term', value)

    def read_created_by(self, value):
        self.stanza.created_by = get_free_value('created_by', value)

    def read_creation_date(self, value):
        self.stanza.creation_date = get_date_value('creation_date', value)



class TermReader(TermOrTypeReader):
    def __init__(self, source, lineno, ontology, unhandled_tag_option, deprecated_tag_option):
        TermOrTypeReader.__init__(self, source, lineno, Term, ontology, unhandled_tag_option, deprecated_tag_option)

    def read_union_of(self, value):
        self._read_simple_ref('union_of', value, 'union_of')

    def read_disjoint_from(self, value):
        self._read_simple_ref('disjoint_from', value, 'disjoint_from')

    def read_intersection_of(self, value):
        m = match_pattern(INTERSECTION_PATTERN, 'intersection_of', value)
        rel = m.group('rel')
        if rel is None:
            rel = 'is_a'
        StanzaReference(value.source, value.lineno, self.stanza, rel, m.group('id'), collection_attribute='intersection_of')
        


class TypedefReader(TermOrTypeReader):
    def __init__(self, source, lineno, ontology, unhandled_tag_option, deprecated_tag_option):
        TermOrTypeReader.__init__(self, source, lineno, Typedef, ontology, unhandled_tag_option, deprecated_tag_option)

    def read_domain(self, value):
        StanzaReference(value.source, value.lineno, self.stanza, 'domain', get_free_value('domain', value))

    def read_range(self, value):
        StanzaReference(value.source, value.lineno, self.stanza, 'range', get_free_value('range', value))

    def read_inverse_of(self, value):
        StanzaReference(value.source, value.lineno, self.stanza, 'inverse_of', get_free_value('inverse_of', value))

    def read_transitive_over(self, value):
        StanzaReference(value.source, value.lineno, self.stanza, 'transitive_over', get_free_value('transitive_over', value))

    def read_is_cyclic(self, value):
        self.stanza.is_cyclic = get_boolean_value('is_cyclic', value)

    def read_is_reflexive(self, value):
        self.stanza.is_reflexive = get_boolean_value('is_reflexive', value)

    def read_is_symmetric(self, value):
        self.stanza.is_symmetric = get_boolean_value('is_symmetric', value)

    def read_is_anti_symmetric(self, value):
        self.stanza.is_anti_symmetric = get_boolean_value('is_anti_symmetric', value)

    def read_is_transitive(self, value):
        self.stanza.is_transitive = get_boolean_value('is_transitive', value)

    def read_is_metadata_tag(self, value):
        self.stanza.is_metadata_tag = get_boolean_value('is_metadata_tag', value)

    


class StanzaReference(Sourced):
    def __init__(self, source, lineno, stanza, rel, reference, collection_attribute='references'):
        Sourced.__init__(self, source, lineno)
        self.stanza = stanza
        self.rel = rel
        self.reference = reference
        c = getattr(stanza, collection_attribute)
        if rel in c:
            l = c[rel]
        else:
            l = []
            c[rel] = l
#        for ref in l:
#            if ref.reference == reference:
#                return
        l.append(self)

    def resolve_reference(self, rel_object, dangling_reference_option, obsolete_reference_option):
        if rel_object is not None:
            self.rel_object = rel_object
        if self.reference in self.stanza.ontology.stanzas:
            self.reference_object = self.stanza.ontology.stanzas[self.reference]
            if obsolete_reference_option is not None and self.reference_object.is_obsolete:
               obsolete_reference_option.handle(self, self.reference, 'reference to obsolete ') 
               # XXX check range
        else:
            dangling_reference_option.handle(self, self.reference, 'reference to unknown ')

class XRef(Sourced):
    def __init__(self, source, lineno, term, reference, description, match, matched):
        Sourced.__init__(self, source, lineno)
        self.term = term
        self.reference = reference
        self.description = description
        self.match = match
        self.matched = matched
        term.xref.append(self)

class Synonym(Sourced):
    def __init__(self, source, lineno, stanza, text, scope, type, dbxrefs):
        Sourced.__init__(self, source, lineno)
        self.stanza = stanza
        self.text = text
        self.scope = scope
        self.type = type
        self.dbxrefs = dbxrefs
        stanza.synonyms.append(self)

    def resolve_references(self, dangling_reference_option):
        if self.type is None:
            return
        if self.type not in self.stanza.ontology.synonymtypedef:
            dangling_reference_option.handle(self, self.type)
            return
        self.type_object = self.stanza.ontology.synonymtypedef[self.type]


class TagSet:
    def __init__(self):
        self.unhandled_tags = []

    def write_obo(self, out):
        raise NotImplemented()

    def _write_obo_triplet_attr(self, out, pred, attr, comment=None, quote=False, scope=None, dbxrefs=None):
        if hasattr(self, attr):
            self._write_obo_triplet(out, pred, getattr(self, attr), comment=comment, quote=quote, scope=scope, dbxrefs=dbxrefs)

    def _write_obo_triplet(self, out, pred, value, comment=None, quote=False, scope=None, dbxrefs=None):
        if hasattr(value, '__iter__'):
            for v in value:
                self._write_obo_triplet(out, pred, v, comment=comment, quote=quote, scope=scope, dbxrefs=dbxrefs)
            return
        if hasattr(value, 'id'):
            value = value.id
        if hasattr(value, 'value'):
            value = value.value
        if value is None:
            return
        if value is True:
            value = 'true'
        if value is False:
            return
        value = value.replace('\n', '\\n').replace('\r', '\\n').replace('\t', '\\t').replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]').replace('{', '\\{').replace('}', '\\}')
        if quote:
            value = '"%s"' % value.replace('"', '\\"')
        if scope:
            value = '%s %s' % (value, scope)
        if dbxrefs is not None:
            value = '%s [%s]' % (value, dbxrefs)
        out.write('%s: %s' % (pred, value))
        if comment is not None:
            out.write(' ! %s' % comment)
        out.write('\n')

class BuiltinStanza:
    def __init__(self, ontology, id):
        self.ontology = ontology
        self.id = id
        self.ontology.stanzas[id] = self
        self.ontology.builtin[id] = self

    def resolve_references(self, dangling_reference_option, obsolete_reference_option):
        pass

    def check_required(self):
        pass
    
    def write_obo(self, out):
        pass

class BuiltinTermOrType(BuiltinStanza):
    def __init__(self, ontology):
        BuiltinStanza.__init__(self, ontology, 'OBO:TERM_OR_TYPE')
        self.is_obsolete = False

class BuiltinTerm(BuiltinStanza):
    def __init__(self, ontology):
        BuiltinStanza.__init__(self, ontology, 'OBO:TERM')
        self.is_obsolete = False

class BuiltinType(BuiltinStanza):
    def __init__(self, ontology):
        BuiltinStanza.__init__(self, ontology, 'OBO:TYPE')
        self.is_obsolete = False

class BuiltinInstance(BuiltinStanza):
    def __init__(self, ontology):
        BuiltinStanza.__init__(self, ontology, 'OBO:INSTANCE')
        self.is_obsolete = False

def _reference_relation_comparator(a, b):
    if a == b:
        return 0
    if a == 'is_a':
        return -1
    if b == 'is_a':
        return 1
    return cmp(a, b)

class Stanza(Sourced, TagSet):
    def __init__(self, source, lineno, ontology, id):
        Sourced.__init__(self, source, lineno)
        TagSet.__init__(self)
        self.ontology = ontology
        self.id = id
        ontology.stanzas[id.value] = self
        self.name = None
        self.is_anonymous = False
        self.alt_ids = []
        self.comment = None
        self.synonyms = []
        self.references = {}
        self.is_obsolete = False
        self.created_by = None
        self.creation_date = None
        self.definition = None
        self.definition_dbxrefs = None
        self.xref = []
        self.replaced_by = []
        self.consider = []
        self.namespace = ontology.default_namespace

    def lookup_synonym(self, text, remove=False):
        for s in self.synonyms:
            if s.text == text:
                if remove:
                    self.synonyms[:] = [x for x in self.synonyms if x.text != text]
                return s
        return None

    def _write_obo_synonyms(self, out):
        for syn in self.synonyms:
            self._write_obo_triplet(out, 'synonym', syn.text, comment=None, quote=True, scope=syn.scope, dbxrefs=syn.dbxrefs)

    def _write_obo_xrefs(self, out):
        for x in self.xref:
            value = x.reference
            if x.match:
                value = value + ' ' + x.match
            if x.matched:
                value = value + ' ' + x.matched
            self._write_obo_triplet(out, 'xref', value)

    def _write_obo_relations(self, out):
        for refrel in sorted(self.references, cmp=_reference_relation_comparator):
            for ref in self.references[refrel]:
                if hasattr(ref, 'reference_object') and hasattr(ref.reference_object, 'name'):
                    comment = ref.reference_object.name.value
                else:
                    comment = None
                if ref.rel in self.ontology.builtin_relations:
                    pred = ref.rel
                    value = ref.reference
                else:
                    pred = 'relationship'
                    value = '%s %s' % (ref.rel, ref.reference)
                self._write_obo_triplet(out, pred, value, comment)

    def write_obo(self, out):
        out.write('\n[%s]\n' % self.obo_header())
        self._write_obo_triplet(out, 'id', self.id)
        self._write_obo_triplet(out, 'name', self.name)
        self._write_obo_triplet(out, 'alt_id', self.alt_ids)
        self._write_obo_triplet(out, 'def', self.definition, quote=True, dbxrefs=self.definition_dbxrefs)
        self._write_obo_triplet_attr(out, 'subset', 'subsets')
        self._write_obo_triplet_attr(out, 'is_transitive', 'is_transitive')
        self._write_obo_triplet(out, 'comment', self.comment)
        self._write_obo_synonyms(out)
        self._write_obo_xrefs(out)
        self._write_obo_relations(out)
        self._write_obo_triplet(out, 'is_anonymous', self.is_anonymous)
        self._write_obo_triplet(out, 'is_obsolete', self.is_obsolete)
        self._write_obo_triplet(out, 'replaced_by', self.replaced_by)
        self._write_obo_triplet(out, 'consider', self.consider)
        self._write_obo_triplet(out, 'created_by', self.created_by)
        self._write_obo_triplet(out, 'creation_date', self.creation_date)

    def check_required(self):
        if self.name is None:
            raise OBOException(self, 'missing required tag name')

    def _resolve_relation_references(self, c, dangling_reference_option, obsolete_reference_option):
        if self.is_obsolete:
            obsolete_reference_option = None
        for rt, refs in c.iteritems():
            if rt not in self.ontology.stanzas:
                dangling_reference_option.handle(self, rt)
                rt_object = None
            else:
                rt_object = self.ontology.stanzas[rt]
                if not isinstance(rt_object, Typedef):
                    raise OBOException('this is not a relation type: ' + rt + '\n    ' + '\n    '.join(ref.message() for ref in refs))
                # XXX check domain
                for ref in refs:
                    ref.resolve_reference(rt_object, dangling_reference_option, obsolete_reference_option)

    def resolve_references(self, dangling_reference_option, obsolete_reference_option):
        for syn in self.synonyms:
            syn.resolve_references(dangling_reference_option)
        self._resolve_relation_references(self.references, dangling_reference_option, obsolete_reference_option)

    def lookup_reference(self, rel, reference, collection_attribute='references', remove=False):
        c = getattr(self, collection_attribute)
        if rel in c:
            for r in c[rel]:
                if r.reference == reference:
                    if remove:
                        c[rel][:] = [x for x in c[rel] if r.reference != reference]
                    return r
        return None

    def parents(self, rel='is_a'):
        if rel in  self.references:
            for link in self.references[rel]:
                yield link.reference_object

    def children(self, rel='is_a'):
        for stanza in self.ontology.stanzas.itervalues():
            if isinstance(stanza, BuiltinStanza):
                continue
            for p in stanza.parents():
                if p.id.value == self.id.value:
                    yield stanza
                    break

    def ancestors(self, rel='is_a', include_self=False):
        if include_self:
            yield self
        if rel in self.references:
            for link in self.references[rel]:
                for a in link.reference_object.ancestors(rel, include_self=True):
                    yield a

    def paths(self, rel='is_a', include_self=False):
        if rel in self.references:
            for link in self.references[rel]:
                for parent_path in link.reference_object.paths(rel, include_self=True):
                    if self in parent_path:
                        raise Exception('loop: %s -> %s' % (' -> '.join(str(p.id.value) for p in parent_path), str(self.id.value)))
                    if include_self:
                        parent_path.append(self)
                    yield parent_path
        elif include_self:
            yield [self]
        else:
            yield []


class TermOrType(Stanza):
    def __init__(self, source, lineno, ontology, id):
        Stanza.__init__(self, source, lineno, ontology, id)
        self.subsets = set()

    def resolve_references(self, dangling_reference_option, obsolete_reference_option):
        Stanza.resolve_references(self, dangling_reference_option, obsolete_reference_option)
        self.subset_objects = []
        for s in self.subsets:
            if s not in self.ontology.subsetdef:
                dangling_reference_option.handle(self, s)
            else:
                self.subset_objects.append(self.ontology.subsetdef[s])

class Term(TermOrType):
    def __init__(self, source, lineno, ontology, id):
        TermOrType.__init__(self, source, lineno, ontology, id)
        self.intersection_of = {}

    def resolve_references(self, dangling_reference_option, obsolete_reference_option):
        TermOrType.resolve_references(self, dangling_reference_option, obsolete_reference_option)
        self._resolve_relation_references(self.intersection_of, dangling_reference_option, obsolete_reference_option)

    def obo_header(self):
        return 'Term'

class Typedef(TermOrType):
    def __init__(self, source, lineno, ontology, id):
        TermOrType.__init__(self, source, lineno, ontology, id)

    def obo_header(self):
        return 'Typedef'


class Instance(Stanza):
    def __init__(self, source, lineno, ontology, id):
        Stanza.__init__(self, source, lineno, ontology, id)

    def check_required(self):
        if 'instance_of' not in self.references:
            raise OBOException(self, 'missing required tag instance_of')


class DanglingReferenceOption:
    def __init__(self):
        pass

    def handle(self, sourced, ref, msg):
        raise NotImplemented()

class DanglingReferenceFail(DanglingReferenceOption):
    def __init__(self):
        DanglingReferenceOption.__init__(self)

    def handle(self, sourced, ref, msg):
        raise OBOException(sourced, msg + str(ref))

class DanglingReferenceIgnore(DanglingReferenceOption):
    def __init__(self):
        DanglingReferenceOption.__init__(self)

    def handle(self, sourced, ref, msg):
        pass

class DanglingReferenceWarn(DanglingReferenceOption):
    def __init__(self):
        DanglingReferenceOption.__init__(self)

    def handle(self, sourced, ref, msg):
        sourced.warning(msg + ref)

class DanglingReferenceWarnAndIgnore(DanglingReferenceWarn, DanglingReferenceIgnore):
    def __init__(self):
        DanglingReferenceWarn.__init__(self)
        DanglingReferenceIgnore.__init__(self)

    def handle(self, sourced, ref, msg):
        DanglingReferenceWarn.handle(self, sourced, ref, msg)
        DanglingReferenceIgnore.handle(self, sourced, ref, msg)

STANZA_TYPE_PATTERN = re.compile('\[(?P<stanza_type>\S+)\]' + TERMINAL_COMMENT)
TAG_VALUE_PATTERN = re.compile('(?P<tag>(?:[^:]|\\.)+):(?P<value>.*)')

class OntologyReader:
    def __init__(self, ontology):
        self.ontology = ontology
        self.header_reader = HeaderReader(ontology, None, None)
        self.stanza_readers = {
            'Term': TermReader(None, 0, ontology, None, None),
            'Typedef': TypedefReader(None, 0, ontology, None, None),
            'Instance': InstanceReader(None, 0, ontology, None, None)
            }

    def read(self, source, file, unhandled_tag_option, deprecated_tag_option):
        current_reader = self.header_reader
        current_reader.unhandled_tag_option = unhandled_tag_option
        current_reader.deprecated_tag_option = deprecated_tag_option
        for r in self.stanza_readers.itervalues():
            r.unhandled_tag_option = unhandled_tag_option
            r.deprecated_tag_option = deprecated_tag_option
        lineno = 0
        for line in file:
            lineno += 1
            line = line.strip()
            if line == '':
                continue
            if line[0] == '!':
                continue
            m = STANZA_TYPE_PATTERN.match(line)
            if m is not None:
                stanza_type_name = m.group('stanza_type')
                if stanza_type_name not in self.stanza_readers:
                    raise OBOException(Sourced(source, lineno), 'unhandled stanza type ' + stanza_type_name)
                current_reader = self.stanza_readers[stanza_type_name]
                current_reader.source = source
                current_reader.lineno = lineno
                current_reader.stanza = None
                continue
            m = TAG_VALUE_PATTERN.match(line)
            if m is None:
                raise OBOException(Sourced(source, lineno), 'syntax error')
            tag = m.group('tag').strip()
            value = m.group('value').strip()
            current_reader.read(tag, SourcedValue(source, lineno, value))



        

BUILTIN = u'''[Typedef]
id: is_a
name: is_a
range: OBO:TERM_OR_TYPE
domain: OBO:TERM_OR_TYPE
def: "The basic subclassing relationship" [OBO:defs]

[Typedef]
id: disjoint_from
name: disjoint_from
range: OBO:TERM
domain: OBO:TERM
def: "Indicates that two classes are disjoint" [OBO:defs]

[Typedef]
id: instance_of
name: instance_of
range: OBO:TERM
domain: OBO:INSTANCE
def: "Indicates the type of an instance" [OBO:defs]

[Typedef]
id: inverse_of
name: inverse_of
range: OBO:TYPE
domain: OBO:TYPE
def: "Indicates that one relationship type is the inverse of another" [OBO:defs]

[Typedef]
id: union_of
name: union_of
range: OBO:TERM
domain: OBO:TERM
def: "Indicates that a term is the union of several others" [OBO:defs]

[Typedef]
id: intersection_of
name: intersection_of
range: OBO:TERM
domain: OBO:TERM
def: "Indicates that a term is the intersection of several others" [OBO:defs]

[Typedef]
id: range
name: range
range: OBO:TERM_OR_TYPE
domain: OBO:TYPE
def: "Indicates the range (type of target) of a relation"

[Typedef]
id: domain
name: domain
range: OBO:TERM_OR_TYPE
domain: OBO:TYPE
def: "Indicates the domain (type of source) of a relation"
'''





class Ontology(TagSet):
    def __init__(self):
        TagSet.__init__(self)
        self.synonymtypedef = OrderedDict()
        self.remark = []
        self.stanzas = OrderedDict()
        self.builtin = {}
        self.subsetdef = OrderedDict()
        self.format_version = '1.2'
        self.version = None
        self.date = None
        self.saved_by = None
        self.auto_generated_by = None
        self.default_namespace = None
        OntologyReader(self).read('<<builtin>>', StringIO(BUILTIN), UnhandledTagFail(), DeprecatedTagWarn())
        self.builtin_relations = set(r.id.value for r in self.stanzas.itervalues() if (r.source == '<<builtin>>'))
        BuiltinType(self)
        BuiltinInstance(self)
        BuiltinTerm(self)
        BuiltinTermOrType(self)

    def write_obo(self, out):
        self._write_obo_triplet(out, 'format-version', self.format_version)
        self._write_obo_triplet(out, 'version', self.version)
        self._write_obo_triplet(out, 'date', self.date)
        self._write_obo_triplet(out, 'saved-by', self.saved_by)
        self._write_obo_triplet(out, 'auto-generated-by', self.auto_generated_by)
        for subset in self.subsetdef.itervalues():
            self._write_obo_triplet(out, 'subsetdef', '%s "%s"' % (subset.name, subset.description))
        for syntype in self.synonymtypedef.itervalues():
            self._write_obo_triplet(out, 'synonymtypedef', '%s "%s" %s' % (syntype.name, syntype.description, syntype.scope))
        self._write_obo_triplet(out, 'default-namespace', self.default_namespace)
        self._write_obo_triplet(out, 'remark', self.remark)

    def load_files(self, unhandled_tag_option, deprecated_tag_option, *filenames):
        reader = OntologyReader(self)
        for fn in filenames:
            f = open(fn)
            reader.read(fn, f, unhandled_tag_option, deprecated_tag_option)
            f.close()

    def load_stdin(self, unhandled_tag_option, deprecated_tag_option):
        reader = OntologyReader(self)
        reader.read('<<stdin>>', stdin, unhandled_tag_option, deprecated_tag_option)

    def resolve_references(self, dangling_reference_option, obsolete_reference_option):
        for s in self.stanzas.itervalues():
            s.resolve_references(dangling_reference_option, obsolete_reference_option)

    def check_required(self):
        for s in self.stanzas.itervalues():
            s.check_required()

    def iterterms(self):
        for term in self.stanzas.itervalues():
            if isinstance(term, Term):
                yield term

    def iter_user_stanzas(self):
        for stanza in self.stanzas.itervalues():
            if isinstance(stanza, BuiltinStanza) or stanza.source == '<<builtin>>':
                continue
            yield stanza

if __name__ == '__main__':
    onto = Ontology()
    onto.load_stdin(UnhandledTagFail(), DeprecatedTagSilent())
    onto.check_required()
    onto.resolve_references(DanglingReferenceFail(), DanglingReferenceWarn())
