#!/usr/bin/env python

from __future__ import print_function

import re
import sys
import os
from configparser import ConfigParser
from email.header import decode_header
try:
    from email.parser import BytesParser
except:
    BytesParser = None
from email.parser import Parser

import chardet
import requests

from bs4 import BeautifulSoup

# ToDo: add doc strings


class EmailParser(object):
    @staticmethod
    def parse(mime_mail_fp):
        if callable(BytesParser):
            parsed_mail = BytesParser().parse(mime_mail_fp)
        else:
            parsed_mail = Parser().parse(mime_mail_fp)
        result = {
            'From': None,
            'To': None,
            'Subject': None,
            'body-plain': None,
            'body-html': None
        }
	try:
            result['From'] = EmailParser.parse_header(parsed_mail, 'From')
	except TypeError:
	    result['From'] = ''
	try:
            result['To'] = EmailParser.parse_header(parsed_mail, 'To')
	except TypeError:
            result['To'] = ''
	try:
            result['Subject'] = EmailParser.parse_header(parsed_mail, 'Subject')
	except TypeError:
            result['Subject'] = ''

        messages = []
        if parsed_mail.is_multipart():
            for m in parsed_mail.get_payload():
                extracted = EmailParser.extract_message(m)
                if extracted:
                    messages.append(extracted)
        else:
            extracted = EmailParser.extract_message(parsed_mail)
            if extracted:
                messages.append(extracted)

        for m in messages:
            content_type = m[0]
            body = m[1].replace('\r\n', '\n').rstrip()

            if content_type is None or content_type.startswith('text/plain'):
                result['body-plain'] = body
            elif content_type.startswith('text/html'):
                result['body-html'] = body

        return result

    @staticmethod
    def extract_message(message):
        body = message.get_payload(decode=True)
        if not body:
            return None
        charset = chardet.detect(body)['encoding']
        if charset is None:
            charset = 'utf-8'
	elif charset == 'ISO-2022-JP':
	    charset = 'ISO-2022-JP-2004'
            return message['Content-Type'], body.replace(b'\033$B', b'\033$(Q').decode(encoding=charset, errors='replace')
	elif charset == 'SJIS':
	    charset = 'CP932'
	elif charset == 'EUC-JP':
	    charset = 'EUCJIS2004'

        return message['Content-Type'], body.decode(encoding=charset, errors='replace')

    @staticmethod
    def parse_header(parsed_mail, field):
        # type: (List[str], str) -> str
	if not parsed_mail.has_key(field):
	    return ''
        decoded = []
        raw_header = parsed_mail[field]
        # decode_header does not work well in some case,
        # eg. FW: =?ISO-2022-JP?B?GyRCR1s/LklURz0bKEI=?=: 
        for chunk in re.split(r'(=\?[^?]+\?[BQ]\?[^?]+\?=)', raw_header):
            if chunk.find('=?') >= 0:
                for decoded_chunk, charset in decode_header(chunk):
                    if charset:
                        try:
                            decoded_chunk = decoded_chunk.decode(charset)
                        except TypeError:
                            pass
                    decoded.append(decoded_chunk)
            elif chunk:
                decoded.append(chunk)
        return re.sub(r'\r?\n\s+', ' ', ''.join(decoded))

class Slack(object):
    def __init__(self, argv = []):
        cfg = ConfigParser()
        candidate = [
            'email2slack',
             os.path.expanduser('~/.email2slack'),
            '/etc/email2slack',
            '/usr/local/etc/email2slack'
        ]
        if len(argv) == 3 and argv[1] == '-f':
            cfg.read([argv[2]])
        else:
            cfg.read(candidate)

        slack = {s[0]: s[1] for s in cfg.items('Slack')}
        self.__team = [(re.compile(t[0]), slack[t[1]]) for t in cfg.items('Team')]
        self.__channel = [(re.compile(c[0]), c[1]) for c in cfg.items('Channel')]

    def notice(self, mail):
        address_to = mail['To']
        address_from = mail['From']
        subject = mail['Subject']
        if mail['body-plain']:
            body = mail['body-plain']
        elif mail['body-html']:
            body = re.sub('\n+', '\n', BeautifulSoup(mail['body-html'], "lxml").get_text()).lstrip('\n')

        text = 'From: {:s}\nTo: {:s}\nSubject: {:s}\n\n{:s}'.format(address_from, address_to, subject, body)

        url = [r[1] for r in self.__team if r[0].match(address_to)]
        if url is None:
            raise Exception('team not found: {:s}'.format(address_to))

        channel = [r[1] for r in self.__channel if r[0].match(address_to)]
        if channel is None:
            raise Exception('channel not found: {:s}'.format(address_to))

        self.__post(url[0], self.__payload(text, channel=channel[0]))

    @staticmethod
    def __payload(text, username=None, channel=None):
        result = {'text': text}

        if username:
            result['username'] = username
        if channel:
            result['channel'] = channel

        return result

    @staticmethod
    def __post(url, body):
        requests.post(url, json=body)


def main():
    try:
        fp = sys.stdin.buffer
    except AttributeError:
        fp = sys.stdin
    mail = EmailParser.parse(fp)
    Slack(sys.argv).notice(mail)


if __name__ == '__main__':
    main()
