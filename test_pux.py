"""
Test for pux.
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
import pux
import logging
import os.path
import unittest

def _testFilePath(name):
    return os.path.join('test', name)

_CustomersPuxPath = _testFilePath('customers.pux')
_EdmBalancePuxPath = _testFilePath('edmBalance.pux')
_EmptyPuxPath = _testFilePath('empty.pux')
_ImportPuxPath = _testFilePath('import.pux')
_MissingEndForPuxPath = _testFilePath('brokenMissingEndFor.pux')
_MissingEndIfPuxPath = _testFilePath('brokenMissingEndIf.pux')
_NamespacePuxPath = _testFilePath('namespace.pux')
_PythonPuxPath = _testFilePath('python.pux')

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
        pux._checkPythonName('test', 'some_name')

    def testCanProcessValidUnicodeName(self):
        pux._checkPythonName('test', u'some_name')

    def testCanProcessNameWithWhtitespace(self):
        pux._checkPythonName('test', '\tsome_name \n ')

    def testRejectsNumber(self):
        self.assertRaises(pux.PuxSyntaxError, pux._checkPythonName, 'test', '123')

    def testRejectsTwoNames(self):
        self.assertRaises(pux.PuxSyntaxError, pux._checkPythonName, 'test', 'two names')

    def testRejectsEmptyName(self):
        self.assertRaises(pux.PuxSyntaxError, pux._checkPythonName, 'test', '')

class SplitDataSourceDefinitionTest(unittest.TestCase):
    def testCanSplitNameDataAndCid(self):
        self.assertEqual(pux.splitDataSourceDefintion('a:b@c'), ('a', 'b', 'c'))

    def testCanSplitNameAndDataWithoutCid(self):
        self.assertEqual(pux.splitDataSourceDefintion('a:b'), ('a', 'b', None))

    def testCanSplitNameWithoutDataAndCid(self):
        self.assertEqual(pux.splitDataSourceDefintion('a'), ('a', None, None))

    def testFailWithEmptyName(self):
        self.assertRaises(pux.PuxSyntaxError, pux.splitDataSourceDefintion, '')
        self.assertRaises(pux.PuxSyntaxError, pux.splitDataSourceDefintion, ' \t\n')

    def testFailWithNonPythonName(self):
        self.assertRaises(pux.PuxSyntaxError, pux.splitDataSourceDefintion, '123')

class TextTemplateTest(unittest.TestCase):
    def testCanBuildTemplateWithTextAtEnd(self):
        textTemplate = pux._InlineTemplate('hello')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'hello')])

    def testCanBuildTemplateWithDollar(self):
        textTemplate = pux._InlineTemplate('$$')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'$')])

    def testCanBuildTemplateWithCode(self):
        textTemplate = pux._InlineTemplate('${2 + 3}')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('code', u'2 + 3')])

    def testCanBuildMixedTemplate(self):
        textTemplate = pux._InlineTemplate('hugo has ${200 + 300}$$ and he likes it')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [
            ('text', u'hugo has '),
            ('code', u'200 + 300'),
            ('text', u'$'),
            ('text', u' and he likes it')
        ])

class PuxImportTest(unittest.TestCase):
    def testCanResolveImportedSymbols(self):
        template = pux.PuxTemplate(_ImportPuxPath)
        self.assertTrue(template)
        targetXmlFilePath = os.path.join('test', 'import.xml')
        pux.convert(template, {}, targetXmlFilePath)

class PuxPythonTest(_ExpectedFileTest):
    def testCanProcessPythonCode(self):
        template = pux.PuxTemplate(_PythonPuxPath)
        self.assertTrue(template)
        targetXmlFilePath = os.path.join('test', 'python.xml')
        pux.convert(template, {}, targetXmlFilePath)
        self.assertFileMatches(targetXmlFilePath)

class PuxTest(unittest.TestCase):
    def testCanValidateEdmBalancePux(self):
        puxTemplate = pux.PuxTemplate(_EdmBalancePuxPath)
        self.assertTrue(puxTemplate)

    def testCanConvertEdmBalance(self):
        template = pux.PuxTemplate(_EdmBalancePuxPath)
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
        pux.convert(template, sourceNameToPathMap, targetXmlFilePath)

    def testCanConvertLoansBalance(self):
        template = pux.PuxTemplate(_CustomersPuxPath)

class MainTest(_ExpectedFileTest):
    def assertXmlFileMatches(self, puxFilePath):
        assert puxFilePath is not None
        self.assertFileMatches(os.path.splitext(puxFilePath)[0] + '.xml')

    def _testMainRaisesSystemExit(self, arguments, expectedExitCode=0):
        assert arguments is not None
        actualArguments = ['test']
        actualArguments.extend(arguments)
        try:
            pux.main(actualArguments)
            self.fail("cmx.main() must raise SystemExit") # pragma: no cover
        except SystemExit, error:
            self.assertEqual(error.code, expectedExitCode, 'exit code is %d instead of %d with arguments: %s' % (error.code, expectedExitCode, actualArguments))

    def testCanShowVersion(self):
        self._testMainRaisesSystemExit(['--version'])

    def testCanShowHelp(self):
        self._testMainRaisesSystemExit(['--help'])

    def testCanValidateEdm(self):
        exitCode, _ = pux.main(['test', _EdmBalancePuxPath])
        self.assertEqual(exitCode, 0)

    def testCanProcessEdm(self):
        exitCode, _ = pux.main([
            'test',
            _EdmBalancePuxPath,
            'edmNotification:%s@%s' % (_testFilePath('edmBalanceNotification.csv'), _testFilePath('cid_edmBalanceNotification.xls')),
            'edmPeriod:%s@%s' % (_testFilePath('edmBalancePeriod.csv'), _testFilePath('cid_edmBalancePeriod.xls'))
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_EdmBalancePuxPath)

    def testCanProcessCustomers(self):
        exitCode, _ = pux.main([
            'test',
            _CustomersPuxPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_CustomersPuxPath)

    def testCanProcessEmptyConstructs(self):
        exitCode, _ = pux.main([
            'test',
            _EmptyPuxPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_EmptyPuxPath)

    def testCanProcessNamespace(self):
        exitCode, _ = pux.main([
            'test',
            _NamespacePuxPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)
        self.assertXmlFileMatches(_NamespacePuxPath)

    def testFailsOnMissingTemplate(self):
        self._testMainRaisesSystemExit([], 2)

    def testFailsOnMissingEndFor(self):
        # FIXME: Test for assertRaises PuxSyntaxError
        exitCode, _ = pux.main([
            'test',
            _MissingEndForPuxPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)

    def testFailsOnMissingEndIf(self):
        # FIXME: Test for assertRaises PuxSyntaxError
        exitCode, _ = pux.main([
            'test',
            _MissingEndIfPuxPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])
        self.assertEqual(exitCode, 0)

if __name__ == '__main__': # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('cutplace').setLevel(logging.WARNING)
    unittest.main()
