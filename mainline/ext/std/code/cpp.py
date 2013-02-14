'''
Created on 26/06/2012

@author: konstaa
'''

import fnmatch
import re
import binascii
import logging

import core.api

class Plugin(core.api.Plugin, core.api.Parent, core.api.Child, core.api.IConfigurable, core.api.ICode):
    
    def declare_configuration(self, parser):
        parser.add_option("--std.code.cpp.files", default="*.c,*.cpp,*.h,*.hpp",
                         help="Enumerates filename extensions to match C/C++ files [default: %default]")
    
    def configure(self, options):
        self.files = options.__dict__['std.code.cpp.files'].split(',')
        
    def initialize(self):
        core.api.subscribe_by_parents_name('core.dir', self)
        
        namespace = self.get_plugin_loader().get_database_loader().create_namespace(self.get_name())
        namespace.add_field('files', int)
        namespace.add_field('mismatched_brackets', None)
    
    def callback(self, parent, data):
        for ext in self.files:
            if fnmatch.fnmatch(data.get_path(), ext):
                if data.get_data(self.get_name(), 'files') != None:
                    self.notify_children(data)
                    return

                count_mismatched_brackets = CppCodeParser().run(data)
                data.set_data(self.get_name(), 'files', 1)
                data.set_data(self.get_name(), 'mismatched_brackets', count_mismatched_brackets)
                self.notify_children(data)
                break
            
class CppCodeParser(object):
    
    regex_cpp = re.compile(r'''
                   /([\\](?:\n|\r|\r\n))*/(?=\n|\r|\r\n)              # Match C++ style comments (empty comment line)
                |  /([\\](?:\n|\r|\r\n))*/.*?[^\\](?=\n|\r|\r\n)      # Match C++ style comments
                                                                      # NOTE: end of line is NOT consumed
                                                                      # NOTE: ([\\](?:\n|\r|\r\n))* for new line separators,
                                                                      # Need to support new line separators in expense of efficiency?
                | /([\\](?:\n|\r|\r\n))*\*.*?\*([\\](?:\n|\r|\r\n))*/ # Match C style comments
                | \'(?:\\.|[^\\\'])*\'                                # Match quoted strings
                | "(?:\\.|[^\\"])*"                                   # Match double quoted strings
                | (((?<=\n|\r)|^)[ \t]*[#].*?[^\\](?=\n|\r|\r\n))     # Match preprocessor
                                                                      # NOTE: end of line is NOT consumed
                                                                      # NOTE: beginning of line is NOT consumed
                | (?P<fn_name>
                      (operator(                                      # Match C++ operator ...
                         (\s+[_a-zA-Z][_a-zA-Z0-9]*(\s*\[\s*\])?)     # - cast, new and delete operators
                       | (\s*\[\s*\])                                 # - operator []
                       | (\s*\(\s*\))                                 # - operator ()
                       | (\s*[+-\\*/=<>!%&^|~,?.]{1,3})               # - other operators (from 1 to 3 symbols)
                      ))                                               
                    | ([~]?[_a-zA-Z][_a-zA-Z0-9]*)                    # ... or function or constructor
                  )\s*[(]                                             # LIMITATION: if there are comments after function name
                                                                      # and before '(', it is not detected
                                                                      # LIMITATION: if there are comments within operator definition,
                                                                      # if may be not detected
                | ((?P<block_type>class|struct|namespace)             # Match C++ class or struct
                    (?P<block_name>((\s+[a-zA-Z_][a-zA-Z0-9_]*)|(?=\s*[{])))) # noname is supported, symbol '{' is not consumed
                                                                      # LIMITATION: if there are comments between keyword and name,
                                                                      # it is not detected
                | [<>{};:]                                            # Match block start/end, brackets and statement separator
                | ((?:\n|\r|\r\n)\s*(?:\n|\r|\r\n))                   # Match double empty line
            ''',
            re.DOTALL | re.MULTILINE | re.VERBOSE
        )

    regex_ln = re.compile(r'(\n)|(\r)|(\r\n)')

    def run(self, data):
        self.__init__() # Go to initial state if it is called twice
        return self.parse(data)
        
    def finalize_block(self, text, block, block_end):
        space_match = re.match('^\s*', text[block['start']:block_end], re.MULTILINE)
        block['start'] += space_match.end() # trim spaces at the beginning
        block['end'] = block_end

        start_pos = block['start']
        crc32 = 0
        for child in block['children']:
            # exclude children
            crc32 = binascii.crc32(text[start_pos:child['start']], crc32)
            start_pos = child['end']
        block['checksum'] = binascii.crc32(text[start_pos:block['end']], crc32) & 0xffffffff # to match python 3
        
    def add_lines_data(self, text, blocks):
        def add_lines_data_rec(self, text, blocks):
            for each in blocks:
                # add line begin
                self.total_current += len(self.regex_ln.findall(text, self.total_last_pos, each['start']))
                each['line_begin'] = self.total_current
                self.total_last_pos = each['start']
                # process enclosed
                add_lines_data_rec(self, text, each['children'])
                # add line end
                self.total_current += len(self.regex_ln.findall(text, self.total_last_pos, each['end']))
                each['line_end'] = self.total_current
                self.total_last_pos = each['end']
        self.total_last_pos = 0
        self.total_current = 1
        add_lines_data_rec(self, text, blocks)

    def add_regions(self, data, blocks):
        # Note: data.add_region() internals depend on special ordering of regions
        # in order to identify enclosed regions efficiently
        def add_regions_rec(self, data, blocks):
            def get_type_id(data, named_type):
                if named_type == "function":
                    return data.get_region_types().FUNCTION
                elif named_type == "class":
                    return data.get_region_types().CLASS
                elif named_type == "struct":
                    return data.get_region_types().STRUCT
                elif named_type == "namespace":
                    return data.get_region_types().NAMESPACE
                elif named_type == "__global__":
                    return data.get_region_types().GLOBAL
                else:
                    assert(False)
            for each in blocks:
                data.add_region(each['name'], each['start'], each['end'],
                                each['line_begin'], each['line_end'], each['cursor'],
                                get_type_id(data, each['type']), each['checksum'])
                add_regions_rec(self, data, each['children'])
        add_regions_rec(self, data, blocks)
        
    def parse(self, data):
        
        def reset_next_block(start):
            return {'name':'', 'start':start, 'cursor':0, 'type':'', 'confirmed':False}
        
        count_mismatched_brackets = 0
        
        text = data.get_content()
        indent_current = 0;
        
        blocks = [{'name':'__global__', 'start':0, 'cursor':0, 'type':'__global__', 'indent_start':indent_current, 'children':[]}]
        curblk = 0
        
        next_block = reset_next_block(0)
        
        cursor_last_pos = 0
        cursor_current = 1
        
        for m in re.finditer(self.regex_cpp, text):
            # Comment
            if text[m.start()] == '/':
                data.add_marker(m.start(), m.end(), data.get_marker_types().COMMENT)
                if text[m.start():m.end()].startswith("//\n"):
                    print text[m.start():m.end()]
            
            # String
            elif text[m.start()] == '"' or text[m.start()] == '\'':
                data.add_marker(m.start() + 1, m.end() - 1, data.get_marker_types().STRING)
            
            # Preprocessor (including internal comments)
            elif text[m.start()] == ' ' or text[m.start()] == '\t' or text[m.start()] == '#':
                data.add_marker(m.start(), m.end(), data.get_marker_types().PREPROCESSOR)

            # Statement end
            elif text[m.start()] == ';':
                # Reset next block name and start
                next_block['name'] = ""
                next_block['start'] = m.end() # potential region start

            # Template argument closing bracket
            elif text[m.start()] == '>':
                # Reset next block name and start (in order to skip class names in templates), if has not been confirmed before
                if next_block['confirmed'] == False and (next_block['type'] == 'class' or next_block['type'] == 'struct'):
                    next_block['name'] = ""
                    next_block['start'] = m.end() # potential region start
                    
            # Template argument opening bracket or after class inheritance specification
            elif text[m.start()] == ':' or text[m.start()] == '<':
                # .. if goes after calss definition
                if next_block['type'] == 'class' or next_block['type'] == 'struct':
                    next_block['confirmed'] = True

            # Double end line
            elif text[m.start()] == '\n' or text[m.start()] == '\r':
                # Reset next block start, if has not been named yet
                if next_block['name'] == "":
                    next_block['start'] = m.end() # potential region start

            # Block start...
            elif text[m.start()] == '{':
                # shift indent right
                indent_current += 1
                
                # ... if name detected previously
                if next_block['name'] != '': # - Start of enclosed block
                    blocks.append({'name':next_block['name'],
                                   'start':next_block['start'],
                                   'cursor':next_block['cursor'],
                                   'type':next_block['type'],
                                   'indent_start':indent_current,
                                   'children':[]})
                    next_block = reset_next_block(m.end())
                    curblk += 1
                # ... reset next block start, otherwise
                else: # - unknown type of block start
                    next_block['start'] = m.end() # potential region start
            
            # Block end...
            elif text[m.start()] == '}':
                # ... if indent level matches the start
                if blocks[curblk]['indent_start'] == indent_current:
                    next_block = reset_next_block(m.end())
                    if curblk == 0:
                        print data.get_path()
                        print cursor_current + len(self.regex_ln.findall(text, cursor_last_pos, m.start()))
                        logging.warning("Non-matching closing bracket '}' detected")
                        count_mismatched_brackets += 1
                        continue
                    
                    self.finalize_block(text, blocks[curblk], m.end())
                    assert(blocks[curblk]['type'] != '__global__')
                    
                    curblk -= 1
                    assert(curblk >= 0)
                    blocks[curblk]['children'].append(blocks.pop())

                # shift indent left
                indent_current -= 1
                if indent_current < 0:
                    logging.warning("Non-matching closing bracket '}' detected")
                    count_mismatched_brackets += 1
                    indent_current = 0

            # Potential namespace, struct, class
            elif text[m.start():m.end()].startswith(('class','struct','namespace')) == True \
                and m.group('fn_name') == None: # function name can start with keyword, for example class_id_type()
                if next_block['name'] == "":
                    # - 'name'
                    next_block['name'] = m.group('block_name').strip()
                    if next_block['name'] == "":
                        next_block['name'] = '__noname__'
                    # - 'cursor'
                    cursor_current += len(self.regex_ln.findall(text, cursor_last_pos, m.start('block_name')))
                    cursor_last_pos = m.start('block_name')
                    next_block['cursor'] = cursor_current
                    # - 'type'
                    next_block['type'] = m.group('block_type').strip()
                    # - 'start' detected earlier

            # Potential function name detected...
            else:
                # ... if outside of a function (do not detect enclosed functions, unless classes are matched)
                if blocks[curblk]['type'] != 'function' and (next_block['name'] == "" or next_block['type'] != 'function'):
                    # - 'name'
                    next_block['name'] = m.group('fn_name').strip()
                    # - 'cursor'
                    cursor_current += len(self.regex_ln.findall(text, cursor_last_pos, m.start('fn_name')))
                    cursor_last_pos = m.start('fn_name')
                    # NOTE: cursor could be collected together with line_begin, line_end,
                    # but we keep it here separately for easier debugging of file parsing problems
                    next_block['cursor'] = cursor_current
                    # - 'type'
                    next_block['type'] = 'function'
                    # - 'start' detected earlier

        while indent_current > 0:
            # log all
            logging.warning("Non-matching opening bracket '{' detected")
            count_mismatched_brackets += 1
            indent_current -= 1

        for (ind, each) in enumerate(blocks):
            each = each # used
            block = blocks[len(blocks) - 1 - ind]
            self.finalize_block(text, block, len(text))

        self.add_lines_data(text, blocks)
        self.add_regions(data, blocks)
        
        return count_mismatched_brackets

            