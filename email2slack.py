#!/usr/bin/env python

from __future__ import print_function

import re
import sys
import os
import argparse
from configparser import ConfigParser
from email.header import decode_header
try:
    from email.parser import BytesParser
except:
    BytesParser = None
from email.parser import Parser
from email.utils import parseaddr, getaddresses

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
            body = m[1].replace('\r\n', '\n')
            try:
                parameter = dict([x.split('=', 1) for x in content_type.split('; ')[1:]])
            except:
                parameter = {}
            if  parameter.get('format') == 'flowed' and parameter.get('delsp') == 'yes':
                body = body.replace(b' \n', '')
            body = body.rstrip() + '\n'

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
            return message['Content-Type'], body.replace(b'\033$B', b'\033$(Q').replace(b'\033(J', b'\033(B').decode(encoding=charset, errors='replace')
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
        chunks = re.split(r'(=\?[^?]+\?[BQ]\?[^?]+\?=)', re.sub(r'\r?\n\s+', ' ', raw_header))
        i = 0
        while i < len(chunks):
            if chunks[i].startswith('=?') and chunks[i].endswith('?=') and \
               i < len(chunks) - 2 and \
               chunks[i + 1] == ' ' and \
               chunks[i + 2].startswith('=?') and chunks[i + 2].endswith('?='):
                del(chunks[i + 1])
            i += 1

        for chunk in chunks:
            if chunk.find('=?') >= 0:
                for decoded_chunk, charset in decode_header(chunk):
                    if charset:
                        if charset == 'ISO-2022-JP':
                            charset = 'ISO-2022-JP-2004'
                            decoded_chunk = decoded_chunk.replace(b'\033$B', b'\033$(Q').replace(b'\033(J', b'\033(B')
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
        return ''.join(decoded)

class Slack(object):
    __debug = False

    def __init__(self, args):
        cfg = ConfigParser()
        candidate = [
            'email2slack',
             os.path.expanduser('~/.email2slack'),
            '/etc/email2slack',
            '/usr/local/etc/email2slack'
        ]
        if args.config:
            candidate.insert(0, args.config)
        cfg.read(candidate)

        Slack.__debug = args.debug
        default_slack = args.slack
        default_team = args.team
        default_channel = args.channel

        slack = {}
        if cfg.has_section('Team'):
            for name, url in cfg.items('Slack'):
                if name == 'default' and default_slack:
                    url = default_slack
                    default_slack = None
                slack[name] = url
        if default_slack:
            slack['default'] = default_slack

        self.__team = []
        if cfg.has_section('Team'):
            for pattern, team in cfg.items('Team'):
                if pattern == 'default':
                    pattern = r'.*'
                    if default_team:
                        team = default_team
                        default_team = None
                self.__team.append((re.compile(pattern), slack[team]))
        if default_team and slack.has_key(default_team):
            self.__team.append((re.compile(r'.*'), slack[default_team]))
        if len(self.__team) == 0 and slack.has_key('default'):
            self.__team.append((re.compile(r'.*'), slack['default']))

        self.__channel = []
        if cfg.has_section('Channel'):
            for pattern, channel in cfg.items('Channel'):
                if pattern == 'default':
                    pattern = r'.*'
                    if default_channel:
                        channel = default_channel
                        default_channel = None
                self.__channel.append((re.compile(pattern), channel))
        if default_channel:
            self.__channel.append((re.compile(r'.*'), default_channel))

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
                p.replace_with(p.get_text() + "\n")
            return re.sub('\n{2,}', '\n\n', soup.get_text()).lstrip('\n')

        def increment_of_url(text):
            URL_PATTERN = r'(https?://[-\w\d:#@%/;$()~_?+=.&]*)'
            DOMAINURL_PATTERN = r'(\b(?:[\w\d][-\w\d]+?\.)+\w{2,4}\b)'
            urls = re.findall(URL_PATTERN, text)
            domains = re.findall(DOMAINURL_PATTERN, text)
            return len(urls)*len('<>') + len(''.join(domains)) + len(urls)*len('<http://|>')

        def increment_of_callto(text):
            return len(re.findall(r'\b(\d{3}-\d{3}-\d{4}|\d{4}-\d{3}-\d{4})\b', text))*len('<callto:>')

        def increment_of_mailaddr(text):
            addrs = [a for n, a in getaddresses(re.sub(r'<mailto:[^>]+>', '', text).splitlines()) if a.find('@') >1]
            return len(''.join(addrs)) + len(addrs)*len('<mailto:|>')

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

        text = '*Date*: {:s}\n*From*: {:s}\n*To*: {:s}\n*Subject*: {:s}\n'.format(date, header_from, header_to, subject)
        msg_limit = 4000 \
                    - len(text) \
                    - increment_of_mailaddr(text) \
                    - len('``````\n')
        pretext = self.flags.get('pretext', False)
        escaped = html_escape(body)
        increment = increment_of_url(body) + increment_of_mailaddr(body) + increment_of_callto(body)
        if not pretext or len(escaped) + increment <= msg_limit:
            text = html_escape(text)
            if pretext:
                text += '```{:s}```\n'.format(escaped)
            else:
                text += '{:s}'.format(escaped)
            self.__post(url[0], self.__payload(text, channel=channel[0], footer='Posted by email2slack'))
            return

        heading = text
        continued = 'continued: {:s}\n'.format(subject)
        while len(body):
            msg_limit = 4000 \
                    - len(heading) \
                    - increment_of_mailaddr(heading) \
                    - len('``````\n')
            i = body.rfind('\n', 0, msg_limit) + 1
            chunk = body[0:i]
            increment = increment_of_url(chunk) + increment_of_mailaddr(chunk) + increment_of_callto(chunk)
            escaped = html_escape(chunk)
            increment += len(escaped) - len(chunk)
            while len(chunk) + increment >= msg_limit:
                chunk = chunk[:(msg_limit - increment)]
                i = chunk.rfind('\n', 0, len(chunk) - 1) + 1
                chunk = chunk[0:i]
                escaped = html_escape(chunk)
                increment = len(escaped) - len(chunk) + increment_of_url(chunk) + increment_of_mailaddr(chunk) + increment_of_callto(chunk)
            heading = html_escape(heading)
            if chunk:
                text = '{:s}```{:s}```'.format(heading, escaped)
                self.__post(url[0], self.__payload(text, channel=channel[0]))
                body = body[len(chunk):]
                heading = continued
            else:
                escaped = html_escape(body)
                text = '{:s}```{:s}```'.format(heading, escaped)
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
        if Slack.__debug:
            print(body['channel'])
            print(body['text'])
        else:
            requests.post(url, json=body)


def get_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--channel",
                    help=("default slack channel."))
    parser.add_argument("-d", "--debug", action='store_true',
                    help=("dry run, does not post to slack."))
    parser.add_argument("-f", "--config",
                    help=("email2slack config file."))
    parser.add_argument("-s", "--slack",
                    help=("default slack incoming hook."))
    parser.add_argument("-t", "--team",
                    help=("default slack team."))
    return parser

def main():
    args = get_arg_parser().parse_args()
    try:
        fp = sys.stdin.buffer
    except AttributeError:
        fp = sys.stdin
    mail = EmailParser.parse(fp)
    Slack(args).notice(mail)


if __name__ == '__main__':
    main()
