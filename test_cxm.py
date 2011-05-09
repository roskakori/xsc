"""
Test for cxm.
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
import cxm
import logging
import os.path
import unittest

def _testFilePath(name):
    return os.path.join('test', name)

_EdmBalanceCxmPath = _testFilePath('edmBalance.cxm')
_CustomersCxmPath = _testFilePath('customers.cxm')
_ImportCxmPath = _testFilePath('import.cxm')

class CheckPythonNameTest(unittest.TestCase):
    def testCanProcessValidName(self):
        cxm._checkPythonName('test', 'some_name')

    def testCanProcessValidUnicodeName(self):
        cxm._checkPythonName('test', u'some_name')

    def testCanProcessNameWithWhtitespace(self):
        cxm._checkPythonName('test', '\tsome_name \n ')

    def testRejectsNumber(self):
        self.assertRaises(cxm.CxmSyntaxError, cxm._checkPythonName, 'test', '123')

    def testRejectsTwoNames(self):
        self.assertRaises(cxm.CxmSyntaxError, cxm._checkPythonName, 'test', 'two names')

    def testRejectsEmptyName(self):
        self.assertRaises(cxm.CxmSyntaxError, cxm._checkPythonName, 'test', '')

class SplitDataSourceDefinitionTest(unittest.TestCase):
    def testCanSplitNameDataAndCid(self):
        self.assertEqual(cxm.splitDataSourceDefintion('a:b@c'), ('a', 'b', 'c'))

    def testCanSplitNameAndDataWithoutCid(self):
        self.assertEqual(cxm.splitDataSourceDefintion('a:b'), ('a', 'b', None))

    def testCanSplitNameWithoutDataAndCid(self):
        self.assertEqual(cxm.splitDataSourceDefintion('a'), ('a', None, None))

    def testFailWithEmptyName(self):
        self.assertRaises(cxm.CxmSyntaxError, cxm.splitDataSourceDefintion, '')
        self.assertRaises(cxm.CxmSyntaxError, cxm.splitDataSourceDefintion, ' \t\n')

    def testFailWithNonPythonName(self):
        self.assertRaises(cxm.CxmSyntaxError, cxm.splitDataSourceDefintion, '123')

class TextTemplateTest(unittest.TestCase):
    def testCanBuildTemplateWithTextAtEnd(self):
        textTemplate = cxm._InlineTemplate('hello')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'hello')])

    def testCanBuildTemplateWithDollar(self):
        textTemplate = cxm._InlineTemplate('$$')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'$')])

    def testCanBuildTemplateWithCode(self):
        textTemplate = cxm._InlineTemplate('${2 + 3}')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('code', u'2 + 3')])

    def testCanBuildMixedTemplate(self):
        textTemplate = cxm._InlineTemplate('hugo has ${200 + 300}$$ and he likes it')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [
            ('text', u'hugo has '),
            ('code', u'200 + 300'),
            ('text', u'$'),
            ('text', u' and he likes it')
        ])

class CxmImportTest(unittest.TestCase):
    def testCanResolveImportedSymbols(self):
        template = cxm.CxmTemplate(_ImportCxmPath)
        self.assertTrue(template)
        targetXmlFilePath = os.path.join('test', 'import.xml')
        cxm.convert(template, {}, targetXmlFilePath)

class CxmTest(unittest.TestCase):
    def testCanValidateEdmBalanceCxm(self):
        cxmTemplate = cxm.CxmTemplate(_EdmBalanceCxmPath)
        self.assertTrue(cxmTemplate)

    def testCanConvertEdmBalance(self):
        template = cxm.CxmTemplate(_EdmBalanceCxmPath)
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
        cxm.convert(template, sourceNameToPathMap, targetXmlFilePath)

    def testCanConverLoansBalance(self):
        template = cxm.CxmTemplate(_CustomersCxmPath)

class MainTest(unittest.TestCase):
    def _testMainRaisesSystemExit(self, arguments, expectedExitCode=0):
        assert arguments is not None
        actualArguments = ['test']
        actualArguments.extend(arguments)
        try:
            cxm.main(actualArguments)
            self.fail("cmx.main() must raise SystemExit") # pragma: no cover
        except SystemExit, error:
            self.assertEqual(error.code, expectedExitCode, 'exit code is %d instead of %d with arguments: %s' % (error.code, expectedExitCode, actualArguments))

    def testCanShowVersion(self):
        self._testMainRaisesSystemExit(['--version'])

    def testCanShowHelp(self):
        self._testMainRaisesSystemExit(['--help'])

    def testCanValidateEdm(self):
        cxm.main(['test', _EdmBalanceCxmPath])

    def testCanProcessEdm(self):
        cxm.main([
            _EdmBalanceCxmPath,
            'edmNotification:%s@%s' % (_testFilePath('edmBalanceNotification.csv'), _testFilePath('cid_edmBalanceNotification.xls')),
            'edmPeriod:%s@%s' % (_testFilePath('edmBalancePeriod.csv'), _testFilePath('cid_edmBalancePeriod.xls'))
        ])

    def testCanProcessCustomers(self):
        cxm.main([
            'test',
            _CustomersCxmPath,
            'customers:%s' % _testFilePath('customers.csv'),
        ])

    def testFailsOnMissingTemplate(self):
        self._testMainRaisesSystemExit([], 2)

if __name__ == '__main__': # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('cutplace').setLevel(logging.WARNING)
    unittest.main()
