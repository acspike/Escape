#
# Escape: implements just enough of the deliverance concept to be useful
# Copyright (c) 2010 Aaron C Spike <aaron@ekips.org>
#
# WSGI Code patterned after the XSLT Middleware found at
# http://www.decafbad.com/2005/07/xmlwiki/lib/xmlwiki/xslfilter.py
#


from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

import xpath


def append(from_doc, from_path, to_doc, to_path):
    '''append one or more nodes from the source doc to a node in the destination doc'''
    to_node = xpath.findnode(to_path, to_doc)
    if to_node:
        from_nodes = xpath.find(from_path, from_doc)
        for x in from_nodes:
            to_node.appendChild(x)

def prepend(from_doc, from_path, to_doc, to_path):
    '''append one or more nodes from the source doc to a node in the destination doc'''
    to_node = xpath.findnode(to_path, to_doc)
    if to_node:
        from_nodes = xpath.find(from_path, from_doc)
        first = to_node.firstChild
        if first:
            for x in from_nodes:
                to_node.insertBefore(x, first)
        else:    
            for x in from_nodes:
                to_node.appendChild(x)

def replace(from_doc, from_path, to_doc, to_path):
    '''replace one node in the destination doc with one or more nodes from the source doc'''
    to_node = xpath.findnode(to_path, to_doc)
    if to_node:
        parent = to_node.parentNode
        from_nodes = xpath.find(from_path, from_doc)
        for x in from_nodes:
            parent.insertBefore(x, to_node)
        parent.removeChild(to_node)

def drop(from_doc, from_path):
    '''drop one or more nodes from a doc'''
    from_nodes = xpath.find(from_path, from_doc)
    for x in from_nodes:
        x.parentNode.removeChild(x)


class Filter(object):
    def __init__(self, wrapped_app):
        self.wrapped_app = wrapped_app
        self.status = '200 OK'
        self.headers = []
        self.exc_info = None
        # ruleset: list of tuples in the form (test(status, headers, env), transform(doc, template), template_str)
        self.ruleset = []

    def start_response(self, status, response_headers, exc_info=None):
        self.status = status
        self.headers = response_headers
        self.exc_info = exc_info
        
    def __call__(self, environ, start_response):
        self.environ = environ
        self.server_start_response = start_response
        return self.__iter__()
        
    def __iter__(self):
        input_iter = self.wrapped_app(self.environ, self.start_response).__iter__()
        output_headers = []
        
        # check rules to see if any apply
        rules = []
        for rule in self.ruleset:
            if rule[0](self.status, self.headers, self.environ):
                rules.append(rule)
                
        # if there are applicable rules 
        # try parsing
        input_doc = None
        if rules:
            try:
                input_doc = parseString(''.join(list(input_iter))).documentElement
            except ExpatError:
                pass
        
        # if no rules or parse failure return original
        if len(rules)==0 or input_doc is None:
            output_headers = self.headers
            output_iter = input_iter
        else:       
            # apply applicable rules in turn
            for rule in rules:
                test, transform, template_str = rule
                try: 
                    template_doc = parseString(template_str).documentElement
                except ExpatError:
                    continue
                transform(input_doc, template_doc)
                input_doc = template_doc
                
            # back to xml
            output = input_doc.toxml()
            output_iter = [output].__iter__()
                        
            # copy headers to output and adjust length
            for header_name,header_value in self.headers:
                if header_name.lower() == 'content-length':
                    header_value = len(output)
                output_headers.append((header_name,header_value))
        
        self.server_start_response(self.status, output_headers, self.exc_info)
        return output_iter

