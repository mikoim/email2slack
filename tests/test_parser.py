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

    def test_euc_jp(self):
        self.assertEqual(self.do('euc-jp.txt'), {
            'Message-ID': '<x>',
            'Date': 'Fri, 28 Jul 2017 02:05:35 +0900',
            'From': 'x <x>',
            'To': 'test@example.com',
            'Subject': 'EUC-JPで日本語',
            'body-plain': 'このメールはEUC-JPでエンコードされています．\n',
            'body-html': None
        })

    def test_iso_2022_jp(self):
        self.assertEqual(self.do('iso-2022-jp.txt'), {
            'Message-ID': '<x>',
            'Date': 'Fri, 28 Jul 2017 02:05:35 +0900',
            'From': 'x <x>',
            'To': 'test@example.com',
            'Subject': 'ISO-2022-JPで日本語',
            'body-plain': 'このメールはISO-2022-JPでエンコードされています．\n',
            'body-html': None
        })

    def test_shift_jis(self):
        self.assertEqual(self.do('shift_jis.txt'), {
            'Message-ID': '<x>',
            'Date': 'Fri, 28 Jul 2017 02:05:35 +0900',
            'From': 'x <x>',
            'To': 'test@example.com',
            'Subject': 'Shift_JISで日本語',
            'body-plain': 'このメールはShift_JISでエンコードされています．\n',
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

    def test_mailman(self):
        self.assertEqual(self.do('mailman.txt'), {
            'Message-ID': '<x>',
            'Date': 'Wed, 19 Jul 2017 09:17:38 +0000',
            'From': 'x <y@z>',
            'To': 'test@example.com',
            'Subject': '[test 00001] test',
            'body-plain': '😀\n',
            'body-html': None
        })


if __name__ == '__main__':
    unittest.main()
