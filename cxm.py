"""
Cxm is a command line tool and Python module to convert column based files such
as CSV and PRN to hierarchical XML files.
"""
# Copyright (C) 2011 Thomas Aglassinger
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cutplace
import cutplace.interface
import logging
import loxun
import sys

from collections import namedtuple #@UnusedImport
from string import Template
from xml.dom import minidom
from xml.dom.minidom import Node 

__version__ = "0.1"

_log = logging.getLogger('cxm')

class CxmNode(object):
    def __init__(self, name=None):
        self.name = name
        self.childNodes = None

    def addChild(self, cxmNodeToAdd):
        if self.childNodes is None:
            self.childNodes = [cxmNodeToAdd]
        else:
            self.childNodes.append(cxmNodeToAdd)

    def write(self, xmlWriter, sourceNameToSourceMap):
        raise NotImplementedError()

class _Variables(object):
    """
    Dump for arbitrary attributes.
    """
    def setNamesAndValues(self, names, values):
        assert names
        assert values
        assert len(names) == len(values)
        for index in range(len(names)):
            name = names[index]
            value = values[index]
            self.__dict__[name] = value

class CxmForNode(CxmNode):
    def __init__(self, rider):
        super(CxmForNode, self).__init__('for')
        self.rider = rider

    def write(self, xmlWriter, sourceNameToSourceMap):
        # TODO: Check that rider name has not been used by other <?for ...?> on the stack.
        source = sourceNameToSourceMap[self.rider]
        variables = _Variables()
        for row in source.data:
            variables.setNamesAndValues(source.interface.fieldNames, row)
            globals()[self.rider] = variables
            if self.childNodes:
                for cxmNode in self.childNodes:
                    cxmNode.write(xmlWriter, sourceNameToSourceMap)
            del globals()[self.rider]

class ElementNode(CxmNode):
    def __init__(self, name, attributes):
        super(ElementNode, self).__init__(name)
        self.attributeTemplates = []
        for attributeName, attributeValue in attributes:
            try:
                attributeTemplate = _TextTemplate(attributeValue)
            except:
                # TODO: Create proper error with location and attribute text.
                _log.error(u'%s.%s = %r', name, attributeName, attributeValue)
                raise
            self.attributeTemplates.append((attributeName, attributeTemplate))

    def write(self, xmlWriter, sourceNameToSourceMap):
        processedAttributes = {}
        for name, attributeTemplate in self.attributeTemplates:
            attributeValue = attributeTemplate.eval()
            if name == u'xmlns':
                xmlWriter.addNamespace(u'', attributeValue)
            elif name.startswith(u'xmlns:'):
                xmlWriter.addNamespace(name[6:], attributeValue)
            else:
                processedAttributes[name] = attributeValue
        xmlWriter.startTag(self.name, processedAttributes)
        for cxmNode in self.childNodes:
            cxmNode.write(xmlWriter, sourceNameToSourceMap)
        xmlWriter.endTag(self.name)
            
class DataNode(CxmNode):
    def __init__(self, name, data):
        assert data is not None
        super(DataNode, self).__init__(name)
        self.data = data

    def addChild(self, cxmNodeToAdd, sourceNameToSourceMap):
        raise TypeError('data node cannot not have children')

class TextNode(DataNode):
    def __init__(self, data):
        super(TextNode, self).__init__('text', data)
        self.template = _TextTemplate(data)
    
    def write(self, xmlWriter, sourceNameToSourceMap):
        assert xmlWriter
        xmlWriter.text(self.template.eval())

class CommentNode(DataNode):
    def __init__(self, data):
        super(CommentNode, self).__init__('comment', data)

    def write(self, xmlWriter, sourceNameToSourceMap):
        assert xmlWriter
        xmlWriter.comment(self.data)
    
class ProcessInstructionNode(DataNode):
    def __init__(self, target, data):
        super(ProcessInstructionNode, self).__init__(u'instruction: %s' % target, data)

    def write(self, xmlWriter, sourceNameToSourceMap):
        assert xmlWriter
        xmlWriter.processingInstruction(self.target, self.data)

class TemplateSyntaxError(ValueError):
    pass

class _TextTemplate(object):
    _StateInText = 't'
    _StateInTextAfterDollar = '$'
    _StateInPlaceHolder = '*'
    
    _ItemText = 'text'
    _ItemCode = 'code'

    def __init__(self, templateDescripton):
        assert templateDescripton is not None
        self._state = _TextTemplate._StateInText
        self._items = []
        self._text = u''
        for ch in templateDescripton:
            if self._state == _TextTemplate._StateInText:
                if ch == '$':
                    self._append(_TextTemplate._ItemText, _TextTemplate._StateInTextAfterDollar)
                self._text += ch
            elif self._state == _TextTemplate._StateInTextAfterDollar:
                assert self._text == u'$', "text=%r" % self._text
                if ch == '$':
                    self._append(_TextTemplate._ItemText, _TextTemplate._StateInText)
                elif ch == '{':
                    self._state = _TextTemplate._StateInPlaceHolder
                    self._text = u''
                else:
                    # TODO: Add location to error message.
                    raise TemplateSyntaxError(u'$ must be followed by $ or { but found: %r' % ch)
            elif self._state == _TextTemplate._StateInPlaceHolder:
                if ch == '}':
                    self._append(_TextTemplate._ItemCode, _TextTemplate._StateInText)
                else:
                    self._text += ch
            else:
                assert False
        if self._state == _TextTemplate._StateInText:
            self._append(_TextTemplate._ItemText)
        elif self._state == _TextTemplate._StateInTextAfterDollar:
            # TODO: Add location to error message.
            raise TemplateSyntaxError(u'$ at end of template must be followed by $')
        elif self._state == _TextTemplate._StateInPlaceHolder:
            raise TemplateSyntaxError('place holder must end with }')
        else:
            assert False

    def eval(self):
        result = u''
        for itemType, itemText in self._items:
            if itemType == _TextTemplate._ItemCode:
                try:
                    evaluatedText = eval(itemText)
                    result += evaluatedText
                except Exception, error:
                    _log.error(u'globals:')
                    for key in sorted(globals().keys()):
                        _log.error(u'  %s = %r', key, globals()[key])
                    _log.error(u'cannot evaluate expression: %s: %s' % (itemText, error))
                    raise
            elif itemType == _TextTemplate._ItemText:
                result += itemText
            else:
                assert False
        return result

    def _append(self, itemType, newState=None):
        assert itemType in (_TextTemplate._ItemCode, _TextTemplate._ItemText)
        assert newState in (None, _TextTemplate._StateInPlaceHolder, _TextTemplate._StateInText, _TextTemplate._StateInTextAfterDollar)
        if self._text:
            # TODO: De-HTML-escape '&lt;' to '<' and so on.
            self._items.append((itemType, self._text))
        if newState:
            self._state = newState
        self._text = u''

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __repr__(self):
        return '_TextTemplate(%s)' % self._items

    def unicode(self):
        result = u''
        for itemType, itemText in self._items:
            if itemType == _TextTemplate._ItemCode:
                result += u'${' + itemText + '}'
            elif itemType == _TextTemplate._ItemText:
                result += itemText.replace(u'$', u'$$')
            else:
                assert False
        return result
            
class CxmTemplate(object):
    def __init__(self, cxmFilePath):
        self.content = CxmNode()
        self._cxmStack = [self.content]
        self._commandStack = []
    
        domDocument = minidom.parse(cxmFilePath)
        self._processNode(domDocument)

    @property
    def currentCxmNode(self):
        """
        The `CxmNode` children currently should be appended to.
        """
        assert len(self._cxmStack)
        return self._cxmStack[-1]

    @property
    def currentCommand(self):
        """
        The `CxmNode` of currently active command, e.g. ``<?cxm for ...?>``.
        """
        assert len(self._commandStack)
        return self._commandStack[-1]

    def _pushCxmNode(self, cxmNode):
        assert cxmNode is not None
        self._cxmStack.append(cxmNode)

    def _popCxmNode(self):
        # TODO: Add proper exception
        assert self._cxmStack
        # TODO: Validate that popped command matches expected node name.
        self._cxmStack.pop()
        
    def _pushCommand(self, cxmCommandNode):
        assert cxmCommandNode
        self._commandStack.append(cxmCommandNode)
        self._pushCxmNode(cxmCommandNode)

    def _popCommand(self, expectedCommand):
        assert expectedCommand is not None
        # TODO: Add proper exception
        assert self._commandStack
        self._commandStack.pop()
        self._popCxmNode()

    def _addChild(self, cxmNode):
        assert cxmNode
        self.currentCxmNode.addChild(cxmNode)
        
    def _createCxmProcessingNode(self, domProcessingNode):
        assert domProcessingNode
        
    def _processNode(self, domNode):
        assert domNode
        for node in domNode.childNodes:
            _log.debug(u'process dom node: %s', node)
            nodeType = node.nodeType
            indent = '  ' * 2 * len(self._cxmStack)
            if nodeType == Node.ELEMENT_NODE:
                if node.prefix:
                    tagName = u'%s:%s' % (node.prefix, node.tagName)
                else:
                    tagName = node.tagName
                attributes = node.attributes.items()
                print u'%sadd tag: %s; %s' % (indent, tagName, attributes)
                elementNode = ElementNode(tagName, attributes)
                self._addChild(elementNode)
                self._pushCxmNode(elementNode)
                self._processNode(node)
                self._popCxmNode()
            elif nodeType == Node.TEXT_NODE:
                print u'%sadd text: %r' % (indent, node.data)
                self._addChild(TextNode(node.data))
            elif nodeType == Node.COMMENT_NODE:
                print u'%sadd comment: %r' % (indent, node.data)
                self._addChild(CommentNode(node.data))
            elif nodeType == Node.PROCESSING_INSTRUCTION_NODE:
                target = node.target
                data = node.data
                if target == 'cxm':
                    words = data.split()
                    if not words:
                        raise ValueError('cxm command must be specified')
                    command = words[0]
                    wordCount = len(words)
                    if command == 'for':
                        if wordCount != 2:
                            raise ValueError(u'for command must match <?for {rider}?> but is: %s' % data)
                        rider = words[1]
                        cxmForNode = CxmForNode(rider)
                        print u'%sadd cxm command: %s %s' % (indent, command, rider)
                        self._addChild(cxmForNode)
                        self._pushCommand(cxmForNode)
                    elif command == 'end':
                        if wordCount == 1:
                            raise ValueError(u'cxm command to end must be specified')
                        if wordCount > 2:
                            raise ValueError(u'text after cxm command to end must be removed: %r' % words[2:])
                        commandToEnd = words[1]
                        print u'%send cxm command: %s' % (indent, commandToEnd)
                        self._popCommand(commandToEnd)
                    else:
                        raise ValueError(u'cannot process unknown cxm command: <?cxm %s ...?>' % target)
                else:
                    raise NotImplementedError(u'target=%r' % target)
            else:
                raise NotImplementedError(u'nodeType=%r' % nodeType)
    
class _Source(object):
    """
    Source interface and data to be converted to XML.
    """
    def __init__(self, name):
        assert name
        self.name = name
        self.interface = None
        self.dataFilePath = None
        self.data = None
        self._instructionStack = []
    
    def setInterface(self, interface):
        self.interface = interface

    def setData(self, dataFilePath):
        _log.info('read data "%s"', dataFilePath)
        self.interface.validate(dataFilePath)
        with open(dataFilePath, 'rb') as dataFile:
            self.dataFilePath = dataFile
            self.data = []
            for row in cutplace.interface.validatedRows(self.interface, dataFile):
                self.data.append(row)
    
class Converter(object):
    def __init__(self, template):
        assert template is not None

        self._template = template
        self._sourceNameToSourceMap = {}
        self._xml = None

    def setInterface(self, name, interface):
        assert name
        assert interface is not None
        source = _Source(name)
        source.setInterface(interface)
        self._sourceNameToSourceMap[name] = source

    def setData(self, name, dataFilePath):
        assert name
        assert name in self._sourceNameToSourceMap, 'data name is %r but must be one of: %s' % (name, sorted(self._sourceNameToSourceMap.keys()))
        source = self._sourceNameToSourceMap[name]
        source.setData(dataFilePath)
        
    def _processedText(self, text):
        template = Template(text)
        template.substitute(self._variables)
        return text

    def write(self, targetXmlFilePath):
        assert targetXmlFilePath is not None

        with open(targetXmlFilePath, 'wb') as targetXmlFile:
            with loxun.XmlWriter(targetXmlFile, pretty=False, sourceEncoding='utf-8') as self._xml:
                for cxmNode in self._template.content.childNodes:
                    cxmNode.write(self._xml, self._sourceNameToSourceMap)
            self._xml = None

def convert(template, sourceNameToSourceMap, targetXmlFilePath):
    converter = Converter(template)
    for name, source in sourceNameToSourceMap.items():
        interfaceFilePath, dataFilePath = source
        interface = cutplace.interface.InterfaceControlDocument()
        interface.read(interfaceFilePath)
        converter.setInterface(name, interface)
        converter.setData(name, dataFilePath)
    converter.write(targetXmlFilePath)

def _parsedOptions(arguments):
    return None, None, None

def main(arguments=None):
    """
    Main function for command line call returning a tuple
    ``(exitCode, error)``. In cause everything worked out, the result is
    ``(0, None)``.
    """
    if arguments == None:
        actualArguments = sys.argv
    else:
        actualArguments = arguments

    logging.basicConfig(level=logging.INFO)

    # Parse and validate command line options.
    options, xmlOutFilePath, csvInFilePath = _parsedOptions(actualArguments)

    return 0, None

if __name__ == '__main__':
    sys.exit(main()[0])
