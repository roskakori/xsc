"""
Cxm is a command line tool and Python module to convert column based files such
as CSV and PRN to hierarchical XML files.

It uses a template, which is a valid XML document itself with XML processing
instructions to express loops and conditionals. Loops iterate over data files
row by row. XML attributes and text can use inline Python code to embed data.


Importing Python modules
------------------------

To import a Python module for usage by CXM expressions, use

  <?cxm import some_module?>

For example:

  <?cxm import errno?>

This imports the Python standard module `errno` so it can be used
by CXM expressions, for example:

  <text>access error code = ${errno.EACCES}</text>


Executing Python code
---------------------

To execute arbitrary Python code, use

  <?cxm python
  code
  ?>

For example:

  <?cxm python
  import errno
  global accessErrorCode
  accessErrorCode = errno.EACCES
  ?>


Traversing data
---------------

To traverse all rows in a data source specified on the command line, use

  <?cxm for dataSource?>
  ...
  <?cxm end for?>

For example, consider a data source defined using

  cxm ... customer:customers.csv@icd_customers.xls

The name under which the data source is available for cxm is `customer`. The data
to process are stored in a CSV file in `customers.csv`. A description of the file as a
cutplace interface definition is stored in `icd_customers.xls`.

To add a tag `<customer>` for each customer in `customers.csv`, use

  <?cxm for customer?>
  <customer id="${customder.id}" surname="${customer.lastName}" .../>
  <?cxm end for?>


Processing conditions
---------------------

Example:

  <?cxm if customer.id = loan.customer_id?>
  ...
  <?cxm end if?>
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
import logging
import optparse
import os
import re
import sys
import token
import tokenize
import StringIO
from xml.dom import minidom
from xml.dom.minidom import Node 

import cutplace
import cutplace.interface
import loxun

__version_info__ = (0, 1, 0)
__version__ = '.'.join(unicode(item) for item in __version_info__)

_Description = 'convert CSV, PRN, etc. to XML based on a template'

_log = logging.getLogger('cxm')

class CxmError(Exception):
    pass

class CxmSyntaxError(CxmError):
    pass

class CxmValueError(CxmError):
    pass

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
        raise NotImplementedError() # pragma: no cover

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
            oldVariables = globals().get('_cxmVariables')
            globals()['_cxmVariables'] = variables
            globals()[self.rider] = variables
            if self.childNodes:
                for cxmNode in self.childNodes:
                    cxmNode.write(xmlWriter, sourceNameToSourceMap)
            del globals()[self.rider]
            if oldVariables is not None:
                globals()['_cxmVariables'] = oldVariables
            else:
                del globals()['_cxmVariables']

class CxmIfNode(CxmNode):
    """
    Node to write children only if a condition if fulfilled. The condition is text describing a
    Python expression to be processed using ``eval()``.
    """
    def __init__(self, condition):
        super(CxmIfNode, self).__init__('if')
        self.condition = condition

    def write(self, xmlWriter, sourceNameToSourceMap):
        if self.childNodes:
            conditionFulfilled = eval(self.condition)
            if conditionFulfilled:
                for cxmNode in self.childNodes:
                    cxmNode.write(xmlWriter, sourceNameToSourceMap)

class CxmPythonNode(CxmNode):
    """
    Node to execute arbitrary Python code.
    """
    def __init__(self, code):
        assert code is not None
        super(CxmPythonNode, self).__init__('python')
        self.code = code

    def write(self, xmlWriter, sourceNameToSourceMap):
        exec self.code in globals()

class ElementNode(CxmNode):
    def __init__(self, name, attributes):
        super(ElementNode, self).__init__(name)
        self.attributeTemplates = []
        for attributeName, attributeValue in attributes:
            try:
                attributeTemplate = _InlineTemplate(attributeValue)
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
        if self.childNodes:
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
        self.template = _InlineTemplate(data)
    
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

class CxmInlineSyntaxError(CxmSyntaxError):
    # TODO: Add error location.
    pass

class CxmInlineValueError(CxmError):
    # TODO: Add error location.
    pass

class _InlineTemplate(object):
    """
    Internal representation of text that might use ``${...}`` to inline Python
    variables and code.
    """
    _StateInText = 't'
    _StateInTextAfterDollar = '$'
    _StateInPlaceHolder = '*'
    
    _ItemText = 'text'
    _ItemCode = 'code'
    
    attributeErrorRegEx = re.compile("\\'(?P<className>[a-zA-Z_][a-zA-Z0-9_]*)\\'.+\\'(?P<attributeName>[a-zA-Z_][a-zA-Z0-9_]*)\\'")
        # Regular expression to extract attribute name from attribute error.

    def __init__(self, templateDescripton):
        assert templateDescripton is not None
        self._state = _InlineTemplate._StateInText
        self._items = []
        self._text = u''
        for ch in templateDescripton:
            if self._state == _InlineTemplate._StateInText:
                if ch == '$':
                    self._append(_InlineTemplate._ItemText, _InlineTemplate._StateInTextAfterDollar)
                self._text += ch
            elif self._state == _InlineTemplate._StateInTextAfterDollar:
                assert self._text == u'$', "text=%r" % self._text
                if ch == '$':
                    self._append(_InlineTemplate._ItemText, _InlineTemplate._StateInText)
                elif ch == '{':
                    self._state = _InlineTemplate._StateInPlaceHolder
                    self._text = u''
                else:
                    # TODO: Add location to error message.
                    raise CxmInlineSyntaxError(u'$ must be followed by $ or { but found: %r' % ch)
            elif self._state == _InlineTemplate._StateInPlaceHolder:
                if ch == '}':
                    self._append(_InlineTemplate._ItemCode, _InlineTemplate._StateInText)
                else:
                    self._text += ch
            else:
                assert False
        if self._state == _InlineTemplate._StateInText:
            self._append(_InlineTemplate._ItemText)
        elif self._state == _InlineTemplate._StateInTextAfterDollar:
            # TODO: Add location to error message.
            raise CxmInlineSyntaxError(u'$ at end of template must be followed by $')
        elif self._state == _InlineTemplate._StateInPlaceHolder:
            raise CxmInlineSyntaxError('place holder must end with }')
        else:
            assert False

    def _possibleVariableName(self, attributeError):
        """
        Name of variable in ``attributeError`` or ``None``.
        """
        assert attributeError
        assert isinstance(attributeError, AttributeError)
        attributeErrorMatch = _InlineTemplate.attributeErrorRegEx.match(unicode(attributeError))
        if attributeErrorMatch:
            className = attributeErrorMatch.group('className')
            if className == _Variables.__name__:
                result = attributeErrorMatch.group('attributeName')
        return result

    def eval(self):
        """
        The value resulting by evaluating expressions embedded in ``${...}`` using
        current ``globals()``.
        """
        result = u''

        # If there are no variables (for example when using Python constants or expressions
        # without a <?cxm for?>), use an empty dummy variable dump.
        if '_cxmVariables' not in globals():
            globals()['_cxmVariables'] = _Variables()

        for itemType, itemText in self._items:
            if itemType == _InlineTemplate._ItemCode:
                try:
                    evaluatedText = eval(itemText)
                    if not isinstance(evaluatedText, basestring):
                        evaluatedText = unicode(evaluatedText)
                    result += evaluatedText
                except Exception, error:
                    _log.error(u'cannot evaluate expression: %s', itemText)
                    _log.error(u'currently defined variables:')
                    variables = globals()['_cxmVariables']
                    for variableName in sorted(variables.__dict__.keys()):
                        _log.error(u'  %s = %s', variableName, repr(variables.__dict__[variableName]))
                    detailMessage = unicode(error)
                    if isinstance(error, AttributeError):
                        # Extract unknown attribute name from error message.
                        unknownVariableName = self._possibleVariableName(error)
                        if unknownVariableName:
                            detailMessage = u'cannot find column "%s"' % unknownVariableName
                    _log.exception(error)
                    raise CxmValueError(u'cannot evaluate expression: %r: %s' % (itemText, detailMessage))
            elif itemType == _InlineTemplate._ItemText:
                result += itemText
            else:
                assert False
        return result

    def _append(self, itemType, newState=None):
        assert itemType in (_InlineTemplate._ItemCode, _InlineTemplate._ItemText)
        assert newState in (None, _InlineTemplate._StateInPlaceHolder, _InlineTemplate._StateInText, _InlineTemplate._StateInTextAfterDollar)
        if self._text:
            # TODO: De-HTML-escape '&lt;' to '<' and so on.
            self._items.append((itemType, self._text))
        if newState:
            self._state = newState
        self._text = u''

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __repr__(self):
        return '_InlineTemplate(%s)' % self._items

    def unicode(self):
        result = u''
        for itemType, itemText in self._items:
            if itemType == _InlineTemplate._ItemCode:
                result += u'${' + itemText + '}'
            elif itemType == _InlineTemplate._ItemText:
                result += itemText.replace(u'$', u'$$')
            else:
                assert False
        return result
            
class CxmTemplate(object):
    def __init__(self, cxmFilePath):
        self.content = CxmNode()
        self._cxmStack = [self.content]
        self._commandStack = []
    
        _log.info('read template "%s"', cxmFilePath)
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
                tagName = node.tagName
                attributes = node.attributes.items()
                _log.debug(u'%sadd tag: %s; %s', indent, tagName, attributes)
                elementNode = ElementNode(tagName, attributes)
                self._addChild(elementNode)
                self._pushCxmNode(elementNode)
                self._processNode(node)
                self._popCxmNode()
            elif nodeType == Node.TEXT_NODE:
                _log.debug(u'%sadd text: %r' , indent, node.data)
                self._addChild(TextNode(node.data))
            elif nodeType == Node.COMMENT_NODE:
                _log.debug(u'%sadd comment: %r' , indent, node.data)
                self._addChild(CommentNode(node.data))
            elif nodeType == Node.PROCESSING_INSTRUCTION_NODE:
                target = node.target
                data = node.data
                if target == 'cxm':
                    # TODO: Use Python tokenizer to split and syntax check cxm processing instructions. 
                    words = data.strip().split()
                    if not words:
                        raise CxmSyntaxError('cxm command must be specified')
                    command = words[0]
                    wordCount = len(words)
                    if command == 'for':
                        if wordCount != 2:
                            raise CxmSyntaxError(u'for command must match <?cxm for {rider}?> but is: %s' % data)
                        rider = words[1]
                        cxmForNode = CxmForNode(rider)
                        _log.debug(u'%sadd cxm command: %s %s', indent, command, rider)
                        self._addChild(cxmForNode)
                        self._pushCommand(cxmForNode)
                    elif command == 'end':
                        if wordCount == 1:
                            raise CxmInlineSyntaxError(u'cxm command to end must be specified')
                        if wordCount > 2:
                            raise CxmInlineSyntaxError(u'text after cxm command to end must be removed: %r' % words[2:])
                        commandToEnd = words[1]
                        _log.debug(u'%send cxm command: %s', indent, commandToEnd)
                        self._popCommand(commandToEnd)
                    elif command == 'if':
                        if wordCount < 2:
                            raise CxmSyntaxError(u'if command must match <?cxm if {condition}?> but is: %s' % data)
                        # TODO: Remove check below once Python tokenizer is used to parse cxm processing instructions.
                        if not data.startswith('if'):
                            raise NotImplementedError("cannot process white space before 'if'")
                        condition = data[2:]
                        cxmIfNode = CxmIfNode(condition)
                        _log.debug(u'%sadd cxm command: %s %s', indent, command, condition)
                        self._addChild(cxmIfNode)
                        self._pushCommand(cxmIfNode)
                    elif command == 'import':
                        # TODO: Use python tokenizer to validate that module name is a Python name.
                        # TODO: Add 'import x as y' syntax.
                        if wordCount == 1:
                            raise CxmInlineSyntaxError(u'Python module to import must be specified')
                        if wordCount > 2:
                            raise CxmInlineSyntaxError(u'text after Python module to import must be removed: %r' % words[2:])
                        moduleToImport = words[1]
                        try:
                            _log.info('import %s', moduleToImport)
                            globals()[moduleToImport] = __import__(moduleToImport)
                        except Exception, error:
                            raise CxmError(u'cannot cxm import module %r: %s' % (moduleToImport, error))
                    elif command == 'python':
                        code = data[len('python'):]
                        cmxPythonNode = CxmPythonNode(code)
                        _log.debug(u'%sadd cxm command: %s %s', indent, command, code)
                        self._addChild(cmxPythonNode)
                    else:
                        raise CxmSyntaxError(u'cannot process unknown cxm command: <?cxm %s ...?>' % target)
                else:
                    raise NotImplementedError(u'target=%r' % target)
            else:
                raise NotImplementedError(u'nodeType=%r' % nodeType)
    
class DataSource(object):
    """
    Source data and interface to be converted to XML.
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
        with open(dataFilePath, 'rb') as dataFile:
            self.dataFilePath = dataFile
            self.data = []
            for row in cutplace.interface.validatedRows(self.interface, dataFile):
                self.data.append(row)

def _checkPythonName(name, text):
    assert name
    assert text is not None
    TokyTypesToSkip = set([token.DEDENT, token.ENDMARKER, token.INDENT, token.NEWLINE])
    tokenCount = 0
    for toky in tokenize.generate_tokens(StringIO.StringIO(text).readline):
        tokyType = toky[0]
        if tokyType not in TokyTypesToSkip:
            tokenCount += 1
            if tokenCount == 1:
                if tokyType != token.NAME:
                    raise CxmSyntaxError(u'%s must be a Python name but is: %r' % (name, text))
            else:
                # TODO: Improve error message by describing what a valid Python name actually is.
                raise CxmSyntaxError(u'%s must be a valid Python name but is (type=%s): %r' % (name, tokyType, text))
    if not tokenCount:
        raise CxmSyntaxError(u'%s must be a Python name instead of being empty')

def splitDataSourceDefintion(definition):
    """
    The name, data path and icd path of a data source definition in ``text`` using the template
    ``<name>:<data path>@<cid path>``.
    """
    assert definition is not None

    colonIndex = definition.find(':')
    hasColon = (colonIndex != -1)
    if hasColon:
        dataSourceName = definition[:colonIndex]
    else:
        dataSourceName = definition
    _checkPythonName('data source name', dataSourceName)

    if hasColon:
        dataSourcePath = definition[colonIndex + 1:]
        # TODO: Allow to escape @ by using @@.
        atIndex = dataSourcePath.find('@')
        if atIndex == -1:
            cidPath = None
        else:
            cidPath = dataSourcePath[atIndex + 1:]
            dataSourcePath = dataSourcePath[:atIndex]
    else:
        dataSourcePath = None
        cidPath = None
    result = (dataSourceName, dataSourcePath, cidPath)
    return result

class Converter(object):
    def __init__(self, template):
        assert template is not None

        self._template = template
        self._sourceNameToSourceMap = {}
        self._xml = None

    def setInterface(self, name, interface):
        assert name
        assert interface is not None
        source = DataSource(name)
        source.setInterface(interface)
        self._sourceNameToSourceMap[name] = source

    def setData(self, name, dataFilePath):
        self._validateDataName(name)
        source = self._sourceNameToSourceMap[name]
        source.setData(dataFilePath)
        
    def write(self, targetXmlFilePath):
        assert targetXmlFilePath is not None

        with open(targetXmlFilePath, 'wb') as targetXmlFile:
            with loxun.XmlWriter(targetXmlFile, pretty=False, sourceEncoding='utf-8') as self._xml:
                for cxmNode in self._template.content.childNodes:
                    cxmNode.write(self._xml, self._sourceNameToSourceMap)
            self._xml = None

    def dataFor(self, dataName):
        self._validateDataName(dataName)
        dataSource = self._sourceNameToSourceMap[dataName]
        return dataSource.data

    def _validateDataName(self, name):
        assert name is not None
        if not name:
            raise CxmValueError('data source name must not be empty')
        # TODO: Validate that ``name`` is a valid Python name.
        if not name in self._sourceNameToSourceMap:
            raise CxmValueError('data name is %r but must be one of: %s' % (name, sorted(self._sourceNameToSourceMap.keys())))

def convert(template, sourceNameToSourceMap, targetXmlFilePath, autoDataEncoding='utf-8'):
    assert template is not None
    assert sourceNameToSourceMap is not None
    assert targetXmlFilePath is not None
    assert autoDataEncoding is not None

    converter = Converter(template)
    for dataName, source in sourceNameToSourceMap.items():
        dataFilePath, interfaceFilePath = source
        _log.info('read data "%s" from "%s"', dataName, dataFilePath)
        if interfaceFilePath:
            _log.info('  use interface "%s"', interfaceFilePath)
            interface = cutplace.interface.InterfaceControlDocument()
            interface.read(interfaceFilePath)
        else:
            with open(dataFilePath, 'rb') as dataFile:
                _log.info('  sniff interface')
                interface = cutplace.interface.createSniffedInterfaceControlDocument(dataFile, encoding=autoDataEncoding, header=1)
                _log.info('  found fields: %s', interface.fieldNames)
        converter.setInterface(dataName, interface)
        converter.setData(dataName, dataFilePath)
        _log.info('  found %d data rows', len(converter.dataFor(dataName)))
    converter.write(targetXmlFilePath)

def _parsedOptions(arguments):
    usage = 'usage: %prog [options] TEMPLATE [DATASOURCE ...]'
    epilog = 'TEMPLATE is an XML file typically using \'.cxm\' as suffix. DATASOURCE describes a data source using \'NAME[:DATAFILE[@CIDFILE]]\'. For more information, visit <http://pypi.python.org/pypi/cxm/>.'
    parser = optparse.OptionParser(usage=usage, description=_Description, epilog=epilog, version=__version__)
    parser.add_option('-o', '--output',dest='outXmlPath', metavar='FILE',
        help='XML file where to store output (default: same as TEMPLATE but with suffix \'.xml\'')

    options, others = parser.parse_args(arguments)
    if not others:
        parser.error('TEMPLATE to process must be specified')
    cxmTemplatePath = others[0]
    sourceDefinitions = others[1:]
    
    # Create sources from text matching: 'name:data@cid'
    dataSourceMap = {}
    for sourceDefinition in sourceDefinitions:
        try:
            name, dataPath, icdPath = splitDataSourceDefintion(sourceDefinition)
            if name in dataSourceMap:
                parser.error(u'duplicate data source name must be resolved: %s' % name)
            dataSourceMap[name] = (dataPath, icdPath)
        except CxmSyntaxError, error:
            parser.error('cannot process data source definition: %s' % error)

    # Compute output file.
    if options.outXmlPath is None:
        XmlSuffix = '.xml'
        baseCxmTemplatePath, cxmTemplateSuffix = os.path.splitext(cxmTemplatePath)
        if cxmTemplateSuffix.lower() == XmlSuffix.lower():
            parser.error('--output must be specified or suffix of TEMPLATE must be changed to something other than %r' % cxmTemplateSuffix)
        options.outXmlPath = baseCxmTemplatePath + XmlSuffix
    return options, cxmTemplatePath, dataSourceMap

def main(arguments=None):
    """
    Main function for command line call returning a tuple
    ``(exitCode, error)``. In case everything worked out, the result is
    ``(0, None)``.
    """
    if arguments == None:
        actualArguments = sys.argv
    else:
        actualArguments = arguments

    exitCode = 1
    exitError = None
    try:
        options, cxmTemplatePath, dataSourceMap = _parsedOptions(actualArguments[1:])
        template = CxmTemplate(cxmTemplatePath)
        if dataSourceMap:
            convert(template, dataSourceMap, options.outXmlPath)
        else:
            # No data source means: validate *.cxm without conversion.
            pass
        exitCode = 0
    except KeyboardInterrupt, error:
        _log.error('interrupted by user')
        exitError = error
    except EnvironmentError, error:
        _log.error(u'%s', error)
        exitError = error
    except Exception, error:
        _log.exception(error)
        exitError = error

    return exitCode, exitError

if __name__ == '__main__': # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    sys.exit(main()[0])
