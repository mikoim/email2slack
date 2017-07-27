#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import unittest

from email2slack import EmailParser


class TestEmailParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = 10000

    def do(self, filename):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', filename)
        with open(path, mode='rb') as fp:
            return EmailParser.parse(fp)

    def test_ascii(self):
        self.assertEqual(self.do('ascii.txt'), {
            'Message-ID': '<x>',
            'Date': 'Thu, 27 Jul 2017 22:13:45 +0900',
            'From': 'Test Test <test@example.com>',
            'To': 'test@example.com',
            'Subject': 'test subject',
            'body-plain': 'test message\n',
            'body-html': None
        })

    def test_utf8(self):
        self.assertEqual(self.do('utf8.txt'), {
            'Message-ID': '<x>',
            'Date': 'Thu, 27 Jul 2017 22:21:52 +0900',
            'From': 'Test Test <test@example.com>',
            'To': 'test@example.com',
            'Subject': '日本語',
            'body-plain': 'このメールは日本語で書かれています\n',
            'body-html': None
        })

    def test_fail2ban(self):
        self.assertEqual(self.do('fail2ban.txt'), {
            'Message-ID': '<x>',
            'Date': 'Thu, 27 Jul 2017 19:28:46 +0900',
            'From': 'Fail2Ban <fail2ban@example.com>',
            'To': 'root@example.com',
            'Subject': '[Fail2Ban] sshd: started on xxx',
            'body-plain': 'Hi,\n\nThe jail sshd has been started successfully.\n\nRegards,\n\nFail2Ban\n',
            'body-html': None,
        })

    def test_html(self):
        self.assertEqual(self.do('html.txt'), {
            'Message-ID': '<x>',
            'Date': 'Thu, 27 Jul 2017 22:39:48 +0900',
            'From': 'Test Test <from@example.com>',
            'To': 'to@example.com',
            'Subject': 'HTML',
            'body-plain': 'red\n',
            'body-html': '<div dir="ltr"><span style="background-color:rgb(255,0,0)">red</span></div>\n'
        })


if __name__ == '__main__':
    unittest.main()
