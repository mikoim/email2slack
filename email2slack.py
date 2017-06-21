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
from email.utils import parseaddr

import chardet
import requests

from bs4 import BeautifulSoup, Comment

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
            'Date': None,
            'body-plain': None,
            'body-html': None
        }
        result['From'] = EmailParser.parse_header(parsed_mail, 'From')
        result['To'] = EmailParser.parse_header(parsed_mail, 'To')
        result['Subject'] = EmailParser.parse_header(parsed_mail, 'Subject')
        result['Date'] = EmailParser.parse_header(parsed_mail, 'Date')

        messages = []
        extracted = EmailParser.extract_message(parsed_mail)
        if extracted:
             if isinstance(extracted, list):
                 messages.extend(extracted)
             else:
                 messages.append(extracted)

        for m in messages:
            content_type = m[0]
            body = m[1].replace('\r\n', '\n').rstrip()

            if content_type is None or content_type.startswith('text/plain'):
                if result['body-plain']:
                    result['body-plain'] += body
                else:
                    result['body-plain'] = body
            elif content_type.startswith('text/html'):
                if result['body-html']:
                    result['body-html'] += body
                else:
                    result['body-html'] = body

        return result

    @staticmethod
    def extract_message(message):
        if message.is_multipart():
            messages = []
            for m in message.get_payload():
                extracted = EmailParser.extract_message(m)
                if extracted:
                    if isinstance(extracted, list):
                        messages.extend(extracted)
                    else:
                        messages.append(extracted)
            return messages

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
        decoded = []
        raw_header = parsed_mail.get(field, '')
        # decode_header does not work well in some case,
        # eg. FW: =?ISO-2022-JP?B?GyRCR1s/LklURz0bKEI=?=: 
        for chunk in re.split(r'(=\?[^?]+\?[BQ]\?[^?]+\?=)', raw_header):
            if chunk.find('=?') >= 0:
                for decoded_chunk, charset in decode_header(chunk):
                    if charset:
                        if charset == 'ISO-2022-JP':
                            charset = 'ISO-2022-JP-2004'
                            decoded_chunk = decoded_chunk.replace(b'\033$B', b'\033$(Q')
                        elif charset == 'SJIS':
                            charset = 'CP932'
                        elif charset == 'EUC-JP':
                            charset = 'EUCJIS2004'
                        try:
                            decoded_chunk = decoded_chunk.decode(charset, errors='replace')
                        except TypeError:
                            pass
                    else:
                        decoded_chunk = decoded_chunk.decode()
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
        self.flags = {}
        if cfg.has_section('Flags'):
            self.flags['pretext'] = cfg.getboolean('Flags', 'pretext')
        self.mime_part = {}
        if cfg.has_section('MIME Part'):
            self.mime_part = [(re.compile(x[0]), x[1]) for x in cfg.items('MIME Part')]
        self.pretext = []
        if cfg.has_section('PreText'):
            self.pretext = [(re.compile(x[0]), x[1]) for x in cfg.items('PreText')]

    def notice(self, mail):

        def html_escape(text):
            return text \
                 .replace('&', '&amp;') \
                 .replace('<', '&lt;') \
                 .replace('>', '&gt;')

        def get_html_text(html):
            soup = BeautifulSoup(html, "lxml")
            for e in soup(['style', 'script', '[document]', 'head', 'title']):
                e.extract()
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for td in soup.find_all("td"):
                td.replace_with(td.get_text() + " ")
            for tr in soup.find_all("tr"):
                tr.replace_with(tr.get_text() + "\n")
            for p in soup.find_all("p"):
                p.replace_with(tr.get_text() + "\n")
            return re.sub('\n{2,}', '\n\n', soup.get_text()).lstrip('\n')

        header_to = mail['To']
        address_to = parseaddr(header_to)[1]
        header_from = mail['From']
        address_from = parseaddr(header_from)[1]
        subject = mail['Subject']
        date = mail['Date']
        mime_part = [x[1] for x in self.mime_part if x[0].match(address_from)]
        if len(mime_part) and mime_part[0] == 'html' and mail['body-html']:
            body = get_html_text(mail['body-html'])
            self.flags['pretext'] = False
        elif mail['body-plain']:
            body = mail['body-plain']
        elif mail['body-html']:
            body = get_html_text(mail['body-html'])

        url = [r[1] for r in self.__team if r[0].match(address_to)]
        if url is None:
            raise Exception('team not found: {:s}'.format(header_to))

        channel = [r[1] for r in self.__channel if r[0].match(address_to)]
        if channel is None:
            raise Exception('channel not found: {:s}'.format(header_to))

        body = html_escape(body)
        text = html_escape('*Date*: {:s}\n*From*: {:s}\n*To*: {:s}\n*Subject*: {:s}\n'.format(date, header_from, header_to, subject))
        msg_limit = 4000 - len(text) - 7 - 88
        pretext = self.flags.get('pretext', False)
        if len(body) <= msg_limit or not pretext:
            if pretext:
                text += '```{:s}```\n'.format(body)
            else:
                text += '{:s}'.format(body)
            self.__post(url[0], self.__payload(text, channel=channel[0], footer='Posted by email2slack'))
            return

        heading = text
        continued = 'continued: {:s}\n'.format(subject)
        while len(body):
            i = -1
            if len(body) >= msg_limit:
                i = body.rfind('\n', 0, msg_limit)
            if i >= 0:
                i = i + 1
                text = '{:s}```{:s}```'.format(heading, body[0:i])
                self.__post(url[0], self.__payload(text, channel=channel[0]))
                body = body[i:]
                heading = continued
            else:
                text = '{:s}```{:s}```'.format(heading, body)
                self.__post(url[0], self.__payload(text, channel=channel[0]))
                break
        self.__post(url[0], self.__payload('', channel=channel[0], footer='Posted by email2slack'))

    @staticmethod
    def __payload(text, username=None, channel=None, footer=None):
        result = {'text': text}
        attachments = None

        if username:
            result['username'] = username
        if channel:
            result['channel'] = channel
        if footer:
            if attachments is None: attachments = [{}]
            attachments[0]["footer"] = footer
        if attachments:
            result['attachments'] = attachments

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
