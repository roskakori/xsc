"""
Test for xsc.
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
import xsc
import logging
import os.path
import unittest

def _testFilePath(name):
    return os.path.join('test', name)

_CustomersXscPath = _testFilePath('customers.xsc')
_EdmBalanceXscPath = _testFilePath('edmBalance.xsc')
_EmptyXscPath = _testFilePath('empty.xsc')
_ImportXscPath = _testFilePath('import.xsc')
_MissingEndForXscPath = _testFilePath('brokenMissingEndFor.xsc')
_MissingEndIfXscPath = _testFilePath('brokenMissingEndIf.xsc')
_NamespaceXscPath = _testFilePath('namespace.xsc')
_PythonXscPath = _testFilePath('python.xsc')

class _ExpectedFileTest(unittest.TestCase):
    def assertFileMatches(self, actualFilePath):
        assert actualFilePath is not None
        actualFolderPath, actualNamePath = os.path.split(actualFilePath)
        expectedFilePath = os.path.join(actualFolderPath, 'expected', actualNamePath)
        with open(expectedFilePath, 'rb') as expectedFile:
            with open(actualFilePath, 'rb') as actualFile:
                lineNumber = 1
                hasLines = True
                while hasLines:
                    actualLine = actualFile.readline()
                    expectedLine = expectedFile.readline()
                    if not actualLine or not expectedLine:
                        hasLines = False
                    self.assertEqual(actualLine.rstrip('\n\r'), expectedLine.rstrip('\n\r'), 'file "%s", line %d:\n  a:%r\n  e:%r' % (actualFilePath, lineNumber, actualLine, expectedLine))
                    lineNumber += 1

class CheckPythonNameTest(unittest.TestCase):
    def testCanProcessValidName(self):
        xsc._checkPythonName('test', 'some_name')

    def testCanProcessValidUnicodeName(self):
        xsc._checkPythonName('test', u'some_name')

    def testCanProcessNameWithWhtitespace(self):
        xsc._checkPythonName('test', '\tsome_name \n ')

    def testRejectsNumber(self):
        self.assertRaises(xsc.XscSyntaxError, xsc._checkPythonName, 'test', '123')

    def testRejectsTwoNames(self):
        self.assertRaises(xsc.XscSyntaxError, xsc._checkPythonName, 'test', 'two names')

    def testRejectsEmptyName(self):
        self.assertRaises(xsc.XscSyntaxError, xsc._checkPythonName, 'test', '')

class SplitDataSourceDefinitionTest(unittest.TestCase):
    def testCanSplitNameDataAndCid(self):
        self.assertEqual(xsc.splitDataSourceDefintion('a:b@c'), ('a', 'b', 'c'))

    def testCanSplitNameAndDataWithoutCid(self):
        self.assertEqual(xsc.splitDataSourceDefintion('a:b'), ('a', 'b', None))

    def testCanSplitNameWithoutDataAndCid(self):
        self.assertEqual(xsc.splitDataSourceDefintion('a'), ('a', None, None))

    def testFailWithEmptyName(self):
        self.assertRaises(xsc.XscSyntaxError, xsc.splitDataSourceDefintion, '')
        self.assertRaises(xsc.XscSyntaxError, xsc.splitDataSourceDefintion, ' \t\n')

    def testFailWithNonPythonName(self):
        self.assertRaises(xsc.XscSyntaxError, xsc.splitDataSourceDefintion, '123')

class TextTemplateTest(unittest.TestCase):
    def testCanBuildTemplateWithTextAtEnd(self):
        textTemplate = xsc._InlineTemplate('hello')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'hello')])

    def testCanBuildTemplateWithDollar(self):
        textTemplate = xsc._InlineTemplate('$$')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'$')])

    def testCanBuildTemplateWithCode(self):
        textTemplate = xsc._InlineTemplate('${2 + 3}')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('code', u'2 + 3')])

    def testCanBuildMixedTemplate(self):
        textTemplate = xsc._InlineTemplate('hugo has ${200 + 300}$$ and he likes it')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [
            ('text', u'hugo has '),
            ('code', u'200 + 300'),
            ('text', u'$'),
            ('text', u' and he likes it')
        ])

class XscImportTest(unittest.TestCase):
    def testCanResolveImportedSymbols(self):
        template = xsc.XscTemplate(_ImportXscPath)
        self.assertTrue(template)
        targetXmlFilePath = os.path.join('test', 'import.xml')
        xsc.convert(template, {}, targetXmlFilePath)

class XscPythonTest(_ExpectedFileTest):
    def testCanProcessPythonCode(self):
        template = xsc.XscTemplate(_PythonXscPath)
        self.assertTrue(template)
        targetXmlFilePath = os.path.join('test', 'python.xml')
        xsc.convert(template, {}, targetXmlFilePath)
        self.assertFileMatches(targetXmlFilePath)

class XscTest(unittest.TestCase):
    def testCanValidateEdmBalanceXsc(self):
        xscTemplate = xsc.XscTemplate(_EdmBalanceXscPath)
        self.assertTrue(xscTemplate)

    def testCanConvertEdmBalance(self):
        template = xsc.XscTemplate(_EdmBalanceXscPath)
        sourceNameToPathMap = {
            'edmNotification': (
                os.path.join('test', 'edmBalanceNotification.csv'),
                os.path.join('test', 'cid_edmBalanceNotification.xls')
            ),
            'edmPeriod': (
                os.path.join('test', 'edmBalancePeriod.csv'),
                os.path.join('test', 'cid_edmBalancePeriod.xls')
            )
        }
        targetXmlFilePath = os.path.join('test', 'edmBalance.xml')
        xsc.convert(template, sourceNameToPathMap, targetXmlFilePath)

    def testCanConvertLoansBalance(self):
        template = xsc.XscTemplate(_CustomersXscPath)

class MainTest(_ExpectedFileTest):
    def assertXmlFileMatches(self, xscFilePath):
        assert xscFilePath is not None
        self.assertFileMatches(os.path.splitext(xscFilePath)[0] + '.xml')

    def _testMainRaisesSystemExit(self, arguments, expectedExitCode=0):
        assert arguments is not None
        actualArguments = ['test']
        actualArguments.extend(arguments)
        try:
            xsc.main(actualArguments)
            self.fail("cmx.main() must raise SystemExit") # pragma: no cover
        except SystemExit, error:
            self.assertEqual(error.code, expectedExitCode, 'exit code is %d instead of %d with arguments: %s' % (error.code, expectedExitCode, actualArguments))

    def testCanShowVersion(self):
        self._testMainRaisesSystemExit(['--version'])

    def testCanShowHelp(self):
        self._testMainRaisesSystemExit(['--help'])

    def testCanValidateEdm(self):
        exitCode, _ = xsc.main(['test', _EdmBalanceXscPath])
        self.assertEqual(exitCode, 0)

    def testCanProcessEdm(self):
        exitCode, _ = xsc.main([
            'test',
            _EdmBalanceXscPath,
            'edmNotification:%s@%s' % (_testFilePath('edmBalanceNotification.csv'), _testFilePath('cid_edmBalanceNotification.xls')),
            'edmPeriod:%s@%s' % (_testFilePath('edmBalancePeriod.csv'), _testFilePath('cid_edmBalancePeriod.xls'))
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_EdmBalanceXscPath)

    def testCanProcessCustomers(self):
        exitCode, _ = xsc.main([
            'test',
            _CustomersXscPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_CustomersXscPath)

    def testCanProcessEmptyConstructs(self):
        exitCode, _ = xsc.main([
            'test',
            _EmptyXscPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_EmptyXscPath)

    def testCanProcessNamespace(self):
        exitCode, _ = xsc.main([
            'test',
            _NamespaceXscPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_NamespaceXscPath)

    def testFailsOnMissingTemplate(self):
        self._testMainRaisesSystemExit([], 2)

    def testFailsOnMissingEndFor(self):
        # FIXME: Test for assertRaises XscSyntaxError
        exitCode, _ = xsc.main([
            'test',
            _MissingEndForXscPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)

    def testFailsOnMissingEndIf(self):
        # FIXME: Test for assertRaises XscSyntaxError
        exitCode, _ = xsc.main([
            'test',
            _MissingEndIfXscPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)

if __name__ == '__main__': # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('cutplace').setLevel(logging.WARNING)
    unittest.main()
