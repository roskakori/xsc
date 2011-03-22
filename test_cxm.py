"""
Test for cxm
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

_EdmBalanceCxmPath = os.path.join('test', 'edmBalance.cxm')

class TextTemplateTest(unittest.TestCase):
    def testCanBuildTemplateWithTextAtEnd(self):
        textTemplate = cxm._TextTemplate('hello')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'hello')])

    def testCanBuildTemplateWithDollar(self):
        textTemplate = cxm._TextTemplate('$$')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('text', u'$')])

    def testCanBuildTemplateWithCode(self):
        textTemplate = cxm._TextTemplate('${2 + 3}')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [('code', u'2 + 3')])

    def testCanBuildMixedTemplate(self):
        textTemplate = cxm._TextTemplate('hugo has ${200 + 300}$$ and he likes it')
        self.assertTrue(textTemplate)
        self.assertEqual(textTemplate._items, [
            ('text', u'hugo has '),
            ('code', u'200 + 300'),
            ('text', u'$'),
            ('text', u' and he likes it')
        ])

class CxmTest(unittest.TestCase):
    def testCanParseEdmBalanceCxm(self):
        cxmTemplate = cxm.CxmTemplate(_EdmBalanceCxmPath)
        self.assertTrue(cxmTemplate)

    def testCanConvertEdmBalance(self):
        template = cxm.CxmTemplate(_EdmBalanceCxmPath)
        sourceNameToPathMap = {
            'edmNotification': (
                os.path.join('test', 'cid_edmBalanceNotification.xls'),
                os.path.join('test', 'edmBalanceNotification.csv')
            ),
            'edmPeriod': (
                os.path.join('test', 'cid_edmBalancePeriod.xls'),
                os.path.join('test', 'edmBalancePeriod.csv')
            )
        }
        targetXmlFilePath = os.path.join('test', 'edmBalance.xml')
        cxm.convert(template, sourceNameToPathMap, targetXmlFilePath)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('cutplace').setLevel(logging.WARNING)
    unittest.main()
