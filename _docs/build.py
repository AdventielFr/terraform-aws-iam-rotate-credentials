#!/usr/bin/env python

import os
from os import listdir
import re
import MarkdownPP

class Variable:
    def __init__(self, name):
        self.name = name
        self.description = None
        self.type = 'string'
        self.default = None

class Output:
    def __init__(self, name):
        self.name = name
        self.description = ''

class Module:

    def __init__(self):
        self.variables = []
        self.outputs = []
        self.output_file = 'data.md'
        self.directory = os.path.dirname(os.path.realpath(__file__))+"/.."
        self.default_group = None

        self._regex_start_variable = re.compile('\\s*variable\\s+"([^"]*)"\\s*{', re.IGNORECASE)
        self._regex_start_output = re.compile('\\s*output\\s+"([^"]*)"\\s*{', re.IGNORECASE)
        self._regex_description = re.compile('\\s*description\\s*=\\s*"([^"]*)"', re.IGNORECASE)
        self._regex_type = re.compile('type\\s*=\\s*(.+)', re.IGNORECASE)
        self._regex_default = re.compile('default\\s*=\\s*(.+)', re.IGNORECASE)

    def _try_extract_variable(self, line):
        m = self._regex_start_variable.match(line)
        if m != None:
            return Variable(m.group(1))

    def _try_extract_output(self, line):
        m = self._regex_start_output.match(line)
        if m != None:
            return Output(m.group(1))

    def _try_extract_description(self, v, line):
        if v == None:
            return
        m = self._regex_description.match(line)
        if m != None:
            v.description = m.group(1).strip()

    def _try_extract_type(self, v, line):
        if v == None:
            return
        m = self._regex_type.match(line)
        if m != None:
            v.type = m.group(1)

    def _try_extract_default(self, v, line):
        if v == None:
            return
        if self.default_group != None:
            v.default = v.default + line
            if line == self.default_group:
                self.default_group = None
        else:
            m = self._regex_default.match(line)
            if m != None:
                v.default = m.group(1)
                if v.default.endswith('{'):
                    self.default_group = '}'
                if v.default.endswith('['):
                    self.default_group = ']'
 
    def _try_extract_variables(self, filename):
        result = [] 
        current = None
        with open(filename) as f:
            l = f.readline().strip()
            while l:
                if current == None:
                    current = self._try_extract_variable(l.strip())
                else:
                    if current != None and l.strip() == '}' and self.default_group == None:
                        result.append(current)
                        current = None
                    else:
                        self._try_extract_description(current, l.strip()) 
                        self._try_extract_default(current, l.strip()) 
                        self._try_extract_type(current,l.strip())
                l = f.readline()
            return result

    def _try_extract_outputs(self, filename):
        result = [] 
        current = None
        with open(filename) as f:
            l = f.readline().strip()
            while l:
                if current == None:
                    current = self._try_extract_output(l.strip())
                else:
                    if current !=None and l.strip()=='}':
                        result.append(current)
                        current = None
                    else:
                        self._try_extract_description(current, l.strip())
                l = f.readline()
            return result   

    def build(self):
        for filename in os.listdir(self.directory):
            if filename.endswith('.tf'):
                v = self._try_extract_variables(f'{self.directory}/{filename}')
                o = self._try_extract_outputs(f'{self.directory}/{filename}')
                if len(v)>0:
                    self.variables = self.variables + v
                if len(o)>0:
                    self.outputs = self.outputs + o

    def _md_format(self, src):
        if src == None:
            return None
        trg = src.strip()
        trg = trg.replace('_','\\_')
        trg = trg.replace('[','\\[')
        trg = trg.replace(']','\\]')
        return trg


    ## ---------------------------------
    ## write variable representation in markdown file
    ## ---------------------------------
    def _write_variable(self, variable, f):
        default = 'n/a'
        description = ''
        typ = ''
        if variable.default != None:
            default = self._md_format(variable.default)
        if variable.description != None:
            description = self._md_format(variable.description)
        if variable.type != None:
            typ = self._md_format(variable.type)
        f.write(
            '| {} | {} | {} | {} |\n'
            .format(
                self._md_format(variable.name),
                description,
                typ,
                default
            )
        )

    ## ---------------------------------
    ## write output representation in markdown file
    ## ---------------------------------
    def _write_output(self, output, f):
        default = 'n/a'
        description = ''
        if output.description != None:
            description = output.description.replace('_','\\_')
        f.write(
            '| {} | {} |\n'
            .format(
                output.name.replace('_','\\_'),
                description
            )
        )

    def save(self):
        with open(module.output_file,'w') as f:
            if len(module.variables)>0:
                module.variables.sort(key=lambda x: x.name)
                f.write('## Inputs\n')
                f.write('\n')
                f.write('| Name | Description | Type | Default |\n')
                f.write('|------|-------------|:----:|:-----:|\n')
                for variable in module.variables:
                    self._write_variable(variable, f)
            if len(module.outputs)>0:
                module.outputs.sort(key=lambda x: x.name)
                if len(module.variables)>0:
                    f.write('\n')
                f.write('## Outputs\n')
                f.write('\n')
                f.write('| Name | Description |\n')
                f.write('|------|-------------|\n')
                for output in module.outputs:
                   self._write_output(output, f)

## ---------------------------------
## parse directory to find variables and outputs 
## ---------------------------------

# prepare module
module = Module()
# find variables and outputs
module.build()
module.save()

mdpp = open(os.path.dirname(os.path.realpath(__file__))+'/README.mdpp', 'r')
md = open(os.path.dirname(os.path.realpath(__file__))+'/../README.md', 'w')
modules = list(MarkdownPP.modules)
MarkdownPP.MarkdownPP(input=mdpp, output=md, modules=modules)
mdpp.close()
md.close()
os.remove(os.path.dirname(os.path.realpath(__file__))+'/data.md')

