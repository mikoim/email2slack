#!/usr/bin/env python3

import sys
from configparser import ConfigParser
from email.parser import Parser
from email.header import decode_header

import chardet
import re
import requests


class EmailParser:
    @staticmethod
    def parse(mime_mail):
        parsed_mail = Parser().parsestr(mime_mail)
        result = {
            'From': EmailParser.parse_header(parsed_mail, 'From'),
            'To': EmailParser.parse_header(parsed_mail, 'To'),
            'Subject': EmailParser.parse_header(parsed_mail, 'Subject'),
            'body-plain': None,
            'body-html': None
        }

        messages = []
        if parsed_mail.is_multipart():
            for m in parsed_mail.get_payload():
                messages.append(EmailParser.extract_message(m))
        else:
            messages.append(EmailParser.extract_message(parsed_mail))

        for m in messages:
            content_type = m[0]
            body = m[1]

            if content_type is None or content_type.startswith('text/plain'):
                result['body-plain'] = body
            elif content_type.startswith('text/html'):
                result['body-html'] = body

        return result

    @staticmethod
    def extract_message(message):
        body = message.get_payload(decode=True)
        return message['Content-Type'], body.decode(encoding=chardet.detect(body)['encoding'])

    @staticmethod
    def parse_header(parsed_mail, field: str) -> str:
        try:
            raw_header = parsed_mail[field]
            decoded_string, charset = decode_header(raw_header)[0]
            if charset:
                decoded_string = decoded_string.decode(charset)
            return decoded_string

        except TypeError:
            return ''


class Slack:
    def __init__(self):
        cfg = ConfigParser()
        cfg.read(['email2slack', '~/.email2slack', '/etc/email2slack', '/usr/local/etc/email2slack'])

        slack = {s[0]: s[1] for s in cfg.items('Slack')}
        self.__team = [(re.compile(t[0]), slack[t[1]]) for t in cfg.items('Team')]
        self.__channel = [(re.compile(c[0]), c[1]) for c in cfg.items('Channel')]

    def notice(self, mail):
        address_to = mail['To']
        address_from = mail['From']
        subject = mail['Subject']
        body = mail['body-plain']

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
    raw_mail = ''.join([x for x in sys.stdin.read() if x is not None])
    mail = EmailParser.parse(raw_mail)
    Slack().notice(mail)


if __name__ == '__main__':
    main()
