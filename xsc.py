"""
Xsc is a command line tool and Python module to convert column based files
such as CSV and PRN to hierarchical XML files.

It uses a template, which is a valid XML document itself with XML
processing instructions to express loops and conditionals. Loops iterate
over data files row by row. XML attributes and text can use inline Python
code to embed data.


Installation
------------

Xsc is available from `PyPI <http://pypi.python.org/>`_ and can be
installed using::

  $ easy_install xsc

Provided you are connected to the internet, this also installs a few
required Python modules:

  * coverage, a developer module for testing
  * cutplace, a tool to describe and validate data
  * loxun, a module to write XML files
  * nose, a developer module for testing
  * xlrd, a module to read Excel files
pux
All of them are available from PyPI and can be downloaded and installed
separately.


Tutorial
--------

This section provides a tutorial on using xsc to convert a simple CSV file
containing customer data in an XML file.

Here is the source CSV file::

  id,surname,firstname,dateOfBirth
  1,Doe,John,1957-03-08
  2,Miller,Jane,1946-10-04
  3,Webster,Mike,1974-12-23

As you can see, the first row contains headings for the various columns
where the other rows contain the actual data. This is the kind of CSV file
xsc can process out of the box. If your CSV file has header rows or columns
that cannot be mapped to a header, you either have to remove them manually
or provide a specific interface control document using `cutplace
<http://cutplace.sourceforge.net>`_.

Our goal is to get an XML document that looks like::

  <?xml version="1.0" encoding="utf-8"?>
  <customers>
    <person>
      <surname>Doe</surname>
      <firstname>John</firstname>
      <dateOfBirth>1957-03-08</dateOfBirth>
    </person>
    <person>
      <surname>Miller</surname>
      <firstname>Jane</firstname>
      <dateOfBirth>1946-10-04</dateOfBirth>
    </person>
    <person>
      <surname>Webster</surname>
      <firstname>Mike</firstname>
      <dateOfBirth>1974-12-23</dateOfBirth>
    </person>
  </customers>

First, we have to provide a xsc template. This is a XML document by itself
and can contain processing instructions to read data from data sources such
as CSV files and use inline Python expressions to generate text and XML
attribute values.

To get the desired output, we need the following template::

  <?xml version="1.0" encoding="utf-8"?>
  <customers>
    <?xsc for customers?>
    <person>
      <surname>${customers.surname}</surname>
      <firstname>${customers.surname}</firstname>
      <dateOfBirth>${customers.dateOfBirth}</dateOfBirth>
    </person>
    <?xsc end for?>
  </customers>

The line::

  <?xsc for customers?>

tells xsc to read the data source  ``customers`` row by row and generate
XML code until::

  <?xsc end for?>

for each row. As you probably guessed, we are going to point the data
source ``customers`` to our CSV file.

In the line::

  <surname>${customers.surname}</surname>

the ``${customers.surname}`` tells xsc to insert the value of the row
``surname`` in current row read from the data source ``customers``.  In the
CSV file provided, the first data row has a ``surname`` column with the
value ``Doe``. For the next row, the value is ``Miller`` and so on.

You could use the same syntax to assign a value to an attribute, for
example::

  <person surname="${customers.surname}" .../>

If needed, you can use namespaces just like you are used to:

  <some:person surname="${customers.surname}" .../>

Furthermore you are can use any Python function you like to compute
expressions within ``${...}``, for example::

  <person surname="${customers.surname.upper()}" id="n${'%05d' % (long(id)+100)" .../>

Note that all values read are unicode strings, so you have to convert them
to Python ``long``, ``Decimal``, ``datetime`` and so on if you want to use
them for computations on any of these types.

Now that we have a template (``customers.xsc``) and a data source
(``customers.csv``), we can finally generate our XML document. Open a new
console and change the current folder to the location where the CSV and XSC
file are stored. Then run::

  $ xsc customers.xsc customers:customers.csv

This tells xsc to generate an XML file based on the template
``customers.xsc`` with a data source named ``customers`` read from the file
``customers.csv``.

By default, the output is stored in the same folder as the template under
the same name but with the suffix ``.xml``. You can set a specific output
file using the command line option ``--output``, for example::

  $ xsc --output /tmp/northern_customers.xml customers.xsc customers:customers.csv

If ``customers.csv`` has a more complex format than "CSV with a header
row", you can describe it in a cutplace interface definition in, say,
``cid_customers.xls`` and add it to the data source description after an at
sign (@)::

  $ xsc customers.xsc customers:customers.csv@cid_customers.xls

To learn more about cutplace and how you can use it to describe a data
source, visit <http://cutplace.sourceforge.net>.

Computing text and attribute values
-----------------------------------

Apart from processing instructions, you can use inline python code to
compute text and attribute values in the document. Simply embed the code in
a ``${...}``, for example::

    <img src="${name.lower()}.png" alt="image of ${name}"/>
    This is ${name}.

Assuming the Python variable ``name`` holds the value ``"Bob"``, the
resulting XML code is::

    <img src="bob.png" alt="image of Bob"/>
    This is Bob.

To set variables to values retrieved from a data source, use ``<?xsc
for?>`` (see `Traversing data`_). To set variables to specific values using
possibly complex computations, use ``<?xsc python?>`` (see `Executing
Python code`_).


Importing Python modules
------------------------

To import a Python module for usage by XSC expressions, use::

  <?xsc import some_module?>

For example::

  <?xsc import errno?>

This imports the Python standard module `errno` so it can be used
by XSC expressions, for example::

  <text>access error code = ${errno.EACCES}</text>


Executing Python code
---------------------

To execute arbitrary Python code, use::

  <?xsc python
  code
  ?>

For example::

  <?xsc python
  import errno
  accessErrorCode
  accessErrorCode = errno.EACCES
  ?>

Variables, functions, imports and so are are added to the global scope and
can be used by later ``<?xsc python?>`` instructions and inline code.


Traversing data
---------------

To traverse all rows in a data source specified on the command line, use::

  <?xsc for dataSource?>
  ...
  <?xsc end for?>

For example, consider a data source defined using::

  $ xsc ... customer:customers.csv@icd_customers.xls

The name under which the data source is available for xsc is `customer`.
The data to process are stored in a CSV file in `customers.csv`. A
description of the file as a cutplace interface definition is stored in
`icd_customers.xls`.

To add a tag `<customer>` for each customer in `customers.csv`, use::

  <?xsc for customer?>
  <customer id="${customder.id}" surname="${customer.lastName}" .../>
  <?xsc end for?>


Conditionals and joins
----------------------

Sometimes XML fragments are optional and should show up in the output
only if certain conditions are met. For such a case, xsc provides a
processing instruction of the form::

  <?xsc if condition?>
  ...
  <?xsc end if?>

where *condition* is a boolean Python expression typically resolving to
``True`` or ``False``. Of course, the expression can resolve to any other
value too, in which case the usual Python rules apply whether it should be
interpreted as ``True`` or ``False``.

Apart from adding optional XML fragments, this can be used to simulate
functionality similar to data base joins. As an example consider an XML
document that contain a ``<customer>`` tag for each customer in a data
source and embed a ``<loan>`` in it for each loan the current customer
has::

  <customer id="${customer.id}" ...>
  <?xsc if customer.id = loan.customer_id?>
    <loan id="${loan.id}" ... />
  <?xsc end if?>
  </customer>

Security considerations
-----------------------

Xsc templates can contain arbitrary Python code that can do pretty much
everything any Python script can do. To achieve the concise and powerful
possibilities available to templates, on a technical level xsc liberally
uses ``eval()`` and ``exec``. Both of them imply that you think about who
can modify xsc templates and how.

Just like any Python code, xsc templates can remove files, connect to
databases, send emails and so on. This enables anybody how can modify a xsc
template to remove or modify important system files or publish sensitive
data processed by xsc to unintended places.

Keep this in mind when deploying xsc based applications within your
organization.

The easiest solution to ensure that your xsc based application does not do
anything worse that other applications is to integrate xsc templates in the
same organizational processes as Python code. Typically this means that xsc
templates are modified only by developers, are put under the same version
control as Python source code and use the same test and release management
process as the rest of your Python application.
"""
# Copyright (C) 2011-2012 Thomas Aglassinger
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

__version_info__ = (0, 1, 1)
__version__ = '.'.join(unicode(item) for item in __version_info__)

_Description = 'convert CSV, PRN, etc. to XML based on a template'

_log = logging.getLogger('xsc')

class XscError(Exception):
    pass

class XscSyntaxError(XscError):
    pass

class XscValueError(XscError):
    pass

class XscNode(object):
    def __init__(self, name=None):
        self.name = name
        self.childNodes = None

    def addChild(self, xscNodeToAdd):
        if self.childNodes is None:
            self.childNodes = [xscNodeToAdd]
        else:
            self.childNodes.append(xscNodeToAdd)

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

class XscForNode(XscNode):
    def __init__(self, rider):
        super(XscForNode, self).__init__('for')
        self.rider = rider

    def write(self, xmlWriter, sourceNameToSourceMap):
        # TODO: Check that rider name has not been used by other <?for ...?> on the stack.
        source = sourceNameToSourceMap[self.rider]
        variables = _Variables()
        for row in source.data:
            variables.setNamesAndValues(source.interface.fieldNames, row)
            oldVariables = globals().get('_xscVariables')
            globals()['_xscVariables'] = variables
            globals()[self.rider] = variables
            if self.childNodes:
                for xscNode in self.childNodes:
                    xscNode.write(xmlWriter, sourceNameToSourceMap)
            del globals()[self.rider]
            if oldVariables is not None:
                globals()['_xscVariables'] = oldVariables
            else:
                del globals()['_xscVariables']

class XscIfNode(XscNode):
    """
    Node to write children only if a condition if fulfilled. The condition is text describing a
    Python expression to be processed using ``eval()``.
    """
    def __init__(self, condition):
        super(XscIfNode, self).__init__('if')
        self.condition = condition

    def write(self, xmlWriter, sourceNameToSourceMap):
        if self.childNodes:
            conditionFulfilled = eval(self.condition)
            if conditionFulfilled:
                for xscNode in self.childNodes:
                    xscNode.write(xmlWriter, sourceNameToSourceMap)

class XscPythonNode(XscNode):
    """
    Node to execute arbitrary Python code.
    """
    def __init__(self, code):
        assert code is not None
        super(XscPythonNode, self).__init__('python')
        self.code = code

    def write(self, xmlWriter, sourceNameToSourceMap):
        exec self.code in globals()

class ElementNode(XscNode):
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
            for xscNode in self.childNodes:
                xscNode.write(xmlWriter, sourceNameToSourceMap)
        xmlWriter.endTag(self.name)

class DataNode(XscNode):
    def __init__(self, name, data):
        assert data is not None
        super(DataNode, self).__init__(name)
        self.data = data

    def addChild(self, xscNodeToAdd, sourceNameToSourceMap):
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

class XscInlineSyntaxError(XscSyntaxError):
    # TODO: Add error location.
    pass

class XscInlineValueError(XscError):
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
                    raise XscInlineSyntaxError(u'$ must be followed by $ or { but found: %r' % ch)
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
            raise XscInlineSyntaxError(u'$ at end of template must be followed by $')
        elif self._state == _InlineTemplate._StateInPlaceHolder:
            raise XscInlineSyntaxError('place holder must end with }')
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
        # without a <?xsc for?>), use an empty dummy variable dump.
        if '_xscVariables' not in globals():
            globals()['_xscVariables'] = _Variables()

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
                    variables = globals()['_xscVariables']
                    for variableName in sorted(variables.__dict__.keys()):
                        _log.error(u'  %s = %s', variableName, repr(variables.__dict__[variableName]))
                    detailMessage = unicode(error)
                    if isinstance(error, AttributeError):
                        # Extract unknown attribute name from error message.
                        unknownVariableName = self._possibleVariableName(error)
                        if unknownVariableName:
                            detailMessage = u'cannot find column "%s"' % unknownVariableName
                    _log.exception(error)
                    raise XscValueError(u'cannot evaluate expression: %r: %s' % (itemText, detailMessage))
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

class XscTemplate(object):
    def __init__(self, xscFilePath):
        self.content = XscNode()
        self._xscStack = [self.content]
        self._commandStack = []

        _log.info('read template "%s"', xscFilePath)
        domDocument = minidom.parse(xscFilePath)
        self._processNode(domDocument)

    @property
    def currentXscNode(self):
        """
        The `XscNode` children currently should be appended to.
        """
        assert len(self._xscStack)
        return self._xscStack[-1]

    @property
    def currentCommand(self):
        """
        The `XscNode` of currently active command, e.g. ``<?xsc for ...?>``.
        """
        assert len(self._commandStack)
        return self._commandStack[-1]

    def _pushXscNode(self, xscNode):
        assert xscNode is not None
        self._xscStack.append(xscNode)

    def _popXscNode(self):
        # TODO: Add proper exception
        assert self._xscStack
        # TODO: Validate that popped command matches expected node name.
        self._xscStack.pop()

    def _pushCommand(self, xscCommandNode):
        assert xscCommandNode
        self._commandStack.append(xscCommandNode)
        self._pushXscNode(xscCommandNode)

    def _popCommand(self, expectedCommand):
        assert expectedCommand is not None
        # TODO: Add proper exception
        assert self._commandStack
        self._commandStack.pop()
        self._popXscNode()

    def _addChild(self, xscNode):
        assert xscNode
        self.currentXscNode.addChild(xscNode)

    def _createXscProcessingNode(self, domProcessingNode):
        assert domProcessingNode

    def _processNode(self, domNode):
        assert domNode
        for node in domNode.childNodes:
            _log.debug(u'process dom node: %s', node)
            nodeType = node.nodeType
            indent = '  ' * 2 * len(self._xscStack)
            if nodeType == Node.ELEMENT_NODE:
                tagName = node.tagName
                attributes = node.attributes.items()
                _log.debug(u'%sadd tag: %s; %s', indent, tagName, attributes)
                elementNode = ElementNode(tagName, attributes)
                self._addChild(elementNode)
                self._pushXscNode(elementNode)
                self._processNode(node)
                self._popXscNode()
            elif nodeType == Node.TEXT_NODE:
                _log.debug(u'%sadd text: %r' , indent, node.data)
                self._addChild(TextNode(node.data))
            elif nodeType == Node.COMMENT_NODE:
                _log.debug(u'%sadd comment: %r' , indent, node.data)
                self._addChild(CommentNode(node.data))
            elif nodeType == Node.PROCESSING_INSTRUCTION_NODE:
                target = node.target
                data = node.data
                if target == 'xsc':
                    # TODO: Use Python tokenizer to split and syntax check xsc processing instructions.
                    words = data.strip().split()
                    if not words:
                        raise XscSyntaxError('xsc command must be specified')
                    command = words[0]
                    wordCount = len(words)
                    if command == 'for':
                        if wordCount != 2:
                            raise XscSyntaxError(u'for command must match <?xsc for {rider}?> but is: %s' % data)
                        rider = words[1]
                        xscForNode = XscForNode(rider)
                        _log.debug(u'%sadd xsc command: %s %s', indent, command, rider)
                        self._addChild(xscForNode)
                        self._pushCommand(xscForNode)
                    elif command == 'end':
                        if wordCount == 1:
                            raise XscInlineSyntaxError(u'xsc command to end must be specified')
                        if wordCount > 2:
                            raise XscInlineSyntaxError(u'text after xsc command to end must be removed: %r' % words[2:])
                        commandToEnd = words[1]
                        _log.debug(u'%send xsc command: %s', indent, commandToEnd)
                        self._popCommand(commandToEnd)
                    elif command == 'if':
                        if wordCount < 2:
                            raise XscSyntaxError(u'if command must match <?xsc if {condition}?> but is: %s' % data)
                        # TODO: Remove check below once Python tokenizer is used to parse xsc processing instructions.
                        if not data.startswith('if'):
                            raise NotImplementedError("cannot process white space before 'if'")
                        condition = data[2:]
                        xscIfNode = XscIfNode(condition)
                        _log.debug(u'%sadd xsc command: %s %s', indent, command, condition)
                        self._addChild(xscIfNode)
                        self._pushCommand(xscIfNode)
                    elif command == 'import':
                        # TODO: Use python tokenizer to validate that module name is a Python name.
                        # TODO: Add 'import x as y' syntax.
                        if wordCount == 1:
                            raise XscInlineSyntaxError(u'Python module to import must be specified')
                        if wordCount > 2:
                            raise XscInlineSyntaxError(u'text after Python module to import must be removed: %r' % words[2:])
                        moduleToImport = words[1]
                        try:
                            _log.info('import %s', moduleToImport)
                            globals()[moduleToImport] = __import__(moduleToImport)
                        except Exception, error:
                            raise XscError(u'cannot xsc import module %r: %s' % (moduleToImport, error))
                    elif command == 'python':
                        code = data[len('python'):]
                        cmxPythonNode = XscPythonNode(code)
                        _log.debug(u'%sadd xsc command: %s %s', indent, command, code)
                        self._addChild(cmxPythonNode)
                    else:
                        raise XscSyntaxError(u'cannot process unknown xsc command: <?xsc %s ...?>' % target)
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
                    raise XscSyntaxError(u'%s must be a Python name but is: %r' % (name, text))
            else:
                # TODO: Improve error message by describing what a valid Python name actually is.
                raise XscSyntaxError(u'%s must be a valid Python name but is (type=%s): %r' % (name, tokyType, text))
    if not tokenCount:
        raise XscSyntaxError(u'%s must be a Python name instead of being empty')

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

        _log.info('write output "%s"', targetXmlFilePath)
        with open(targetXmlFilePath, 'wb') as targetXmlFile:
            with loxun.XmlWriter(targetXmlFile, pretty=False, sourceEncoding='utf-8') as self._xml:
                for xscNode in self._template.content.childNodes:
                    xscNode.write(self._xml, self._sourceNameToSourceMap)
            self._xml = None

    def dataFor(self, dataName):
        self._validateDataName(dataName)
        dataSource = self._sourceNameToSourceMap[dataName]
        return dataSource.data

    def _validateDataName(self, name):
        assert name is not None
        if not name:
            raise XscValueError('data source name must not be empty')
        # TODO: Validate that ``name`` is a valid Python name.
        if not name in self._sourceNameToSourceMap:
            raise XscValueError('data name is %r but must be one of: %s' % (name, sorted(self._sourceNameToSourceMap.keys())))

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
                humanReadableFieldNames = ', '.join(interface.fieldNames)
                _log.info('  found fields: %s', humanReadableFieldNames)
        converter.setInterface(dataName, interface)
        converter.setData(dataName, dataFilePath)
        _log.info('  found %d data rows', len(converter.dataFor(dataName)))
    converter.write(targetXmlFilePath)

def _parsedOptions(arguments):
    usage = 'usage: %prog [options] TEMPLATE [DATASOURCE ...]'
    epilog = 'TEMPLATE is an XML file typically using \'.xsc\' as suffix. DATASOURCE describes a data source using \'NAME[:DATAFILE[@CIDFILE]]\'. For more information, visit <http://pypi.python.org/pypi/xsc/>.'
    parser = optparse.OptionParser(usage=usage, description=_Description, epilog=epilog, version=__version__)
    parser.add_option('-o', '--output',dest='outXmlPath', metavar='FILE',
        help='XML file where to store output (default: same as TEMPLATE but with suffix \'.xml\'')

    options, others = parser.parse_args(arguments)
    if not others:
        parser.error('TEMPLATE to process must be specified')
    xscTemplatePath = others[0]
    sourceDefinitions = others[1:]

    # Create sources from text matching: 'name:data@cid'
    dataSourceMap = {}
    for sourceDefinition in sourceDefinitions:
        try:
            name, dataPath, icdPath = splitDataSourceDefintion(sourceDefinition)
            if name in dataSourceMap:
                parser.error(u'duplicate data source name must be resolved: %s' % name)
            dataSourceMap[name] = (dataPath, icdPath)
        except XscSyntaxError, error:
            parser.error('cannot process data source definition: %s' % error)

    # Compute output file.
    if options.outXmlPath is None:
        XmlSuffix = '.xml'
        baseXscTemplatePath, xscTemplateSuffix = os.path.splitext(xscTemplatePath)
        if xscTemplateSuffix.lower() == XmlSuffix.lower():
            parser.error('--output must be specified or suffix of TEMPLATE must be changed to something other than %r' % xscTemplateSuffix)
        options.outXmlPath = baseXscTemplatePath + XmlSuffix
    return options, xscTemplatePath, dataSourceMap

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
        options, xscTemplatePath, dataSourceMap = _parsedOptions(actualArguments[1:])
        template = XscTemplate(xscTemplatePath)
        if dataSourceMap:
            convert(template, dataSourceMap, options.outXmlPath)
        else:
            # No data source means: validate *.xsc without conversion.
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

def mainWithExit():
    """
    Main function for command line call using ``sys.exit()`` to be used
    for standalone command line application.
    """
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('cutplace').setLevel(logging.WARNING)
    sys.exit(main()[0])

if __name__ == '__main__': # pragma: no cover
    mainWithExit()
