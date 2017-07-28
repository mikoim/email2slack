from __future__ import print_function
from __future__ import unicode_literals

import os
import re
from email.utils import parseaddr, getaddresses

import requests
from bs4 import BeautifulSoup

from .compat import *


class Slack(object):
    __debug = False

    def __init__(self, args):
        cfg = compat_configparser()
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
        if default_team and default_team in slack:
            self.__team.append((re.compile(r'.*'), slack[default_team]))
        if len(self.__team) == 0 and 'default' in slack:
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
            self.flags['pretext'] = cfg.getboolean('Flags', 'pretext', fallback=False)
        self.mime_part = {}
        if cfg.has_section('MIME Part'):
            self.mime_part = [(re.compile(x[0]), x[1]) for x in cfg.items('MIME Part')]
        self.pretext = []
        if cfg.has_section('PreText'):
            self.pretext = [(re.compile(x[0]), x[1]) for x in cfg.items('PreText')]

    def notify(self, mail):

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
            return len(urls) * len('<>') + len(''.join(domains)) + len(urls) * len('<http://|>')

        def increment_of_callto(text):
            return len(re.findall(r'\b(\d{3}-\d{3}-\d{4}|\d{4}-\d{3}-\d{4})\b', text)) * len('<callto:>')

        def increment_of_mailaddr(text):
            addrs = [
                a for n, a in getaddresses(
                    [x for x in re.sub(r'<mailto:[^>]+>', '', text).replace(' ', '\n').splitlines() if x.find('@') > 1]
                )
            ]
            return len(''.join(addrs)) + len(addrs) * len('<mailto:|>')

        header_to = mail['To']
        address_to = parseaddr(header_to)[1]
        header_from = mail['From']
        address_from = parseaddr(header_from)[1]
        subject = mail['Subject']
        date = mail['Date']
        message_id = mail['Message-ID']
        mime_part = [x[1] for x in self.mime_part if x[0].match(address_from)]
        if len(mime_part) and mime_part[0] == 'html' and mail['body-html']:
            body = get_html_text(mail['body-html'])
            self.flags['pretext'] = False
        elif mail['body-plain']:
            body = mail['body-plain']
        elif mail['body-html']:
            body = get_html_text(mail['body-html'])
        else:
            body = ''

        url = [r[1] for r in self.__team if r[0].match(address_to)]
        if url is None:
            raise Exception('team not found: {:s}'.format(header_to))

        channel = [r[1] for r in self.__channel if r[0].match(address_to)]
        if channel is None:
            raise Exception('channel not found: {:s}'.format(header_to))

        text = '*Date*: {:s}\n*From*: {:s}\n*To*: {:s}\n*Subject*: {:s}\n'.format(date, header_from, header_to, subject)
        msg_limit = 4000 \
                    - len(html_escape(text)) \
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
            self.__post(url[0], self.__payload(
                text,
                channel=channel[0],
                footer='Posted by email2slack. Original mail is {:s}.'.format(html_escape(message_id))
            ))
            return

        heading = text
        continued = 'continued: {:s}\n'.format(subject)

        body = body.splitlines()
        escaped = escaped.splitlines()
        increment = [increment_of_url(x) + increment_of_mailaddr(x) + increment_of_callto(x) for x in body]

        msg_limit = 4000 \
                    - len(html_escape(heading)) \
                    - increment_of_mailaddr(heading) \
                    - len('``````\n')

        while body:
            i = 0
            l = 0
            lines = len(body)
            while i < lines and l + len(escaped[i]) + increment[i] + 1 < msg_limit:
                l += len(escaped[i]) + increment[i] + 1
                i += 1
            chunk = '\n'.join(escaped[0:i]) + '\n'
            text = '{:s}```{:s}```'.format(heading, chunk)
            self.__post(url[0], self.__payload(text, channel=channel[0]))
            body = body[i:]
            escaped = escaped[i:]
            increment = increment[i:]
            if not heading.startswith('continued:'):
                heading = continued
                msg_limit = 4000 \
                            - len(html_escape(heading)) \
                            - increment_of_mailaddr(heading) \
                            - len('``````\n')
        self.__post(url[0], self.__payload(
            '',
            channel=channel[0],
            footer='Posted by email2slack. Original mail is {:s}.'.format(html_escape(message_id))
        ))

    @staticmethod
    def __payload(text, username=None, channel=None, footer=None):
        result = {'text': text}
        attachments = None

        if username:
            result['username'] = username
        if channel:
            result['channel'] = channel
        if footer:
            if attachments is None:
                attachments = [{}]
            attachments[0]["footer"] = footer
        if attachments:
            result['attachments'] = attachments

        return result

    @staticmethod
    def __post(url, body):
        if Slack.__debug:
            print(body['channel'])
            if body['text']:
                print(body['text'])
            if 'attachments' in body:
                for k, v in body['attachments'][0].items():
                    print(v)
        else:
            requests.post(url, json=body)
