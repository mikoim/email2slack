from __future__ import print_function
from __future__ import unicode_literals

import re
from email.header import decode_header
from email.parser import Parser

try:
    from email.parser import BytesParser
except:
    BytesParser = None

import chardet

try:
    from nkf import nkf
except:
    nkf = None


def unfold_flowed(text):
    lines = text.splitlines()
    nlines = len(lines)
    i = 0
    while i < nlines - 1:
        if not lines[i].endswith(' ') or lines[i] == '-- ':
            i += 1
            continue

        quote = re.match(r'\s*(>\s*)+', lines[i])
        if quote:
            quote = quote.group(0)
            if lines[i + 1].startswith(quote):
                nquote = re.match(r'\s*(>\s*)+', lines[i + 1]).group(0)
                if nquote != quote:
                    i += 1
                    continue
                lines[i] = lines[i][:len(lines[i]) - 1] + lines[i + 1][len(quote):]
                del (lines[i + 1])
                nlines -= 1
                continue
        elif not re.match(r'\s*(>\s*)+', lines[i + 1]):
            lines[i] = lines[i][:len(lines[i]) - 1] + lines[i + 1]
            del (lines[i + 1])
            nlines -= 1
            continue
        i += 1
    return '\n'.join(lines)


class EmailParser(object):
    @staticmethod
    def parse(mime_mail_fp):
        if callable(BytesParser):
            parsed_mail = BytesParser().parse(mime_mail_fp)
        else:
            parsed_mail = Parser().parse(mime_mail_fp)
        result = {
            'From': EmailParser.parse_header(parsed_mail, 'From'),
            'To': EmailParser.parse_header(parsed_mail, 'To'),
            'Subject': EmailParser.parse_header(parsed_mail, 'Subject'),
            'Date': EmailParser.parse_header(parsed_mail, 'Date'),
            'Message-ID': EmailParser.parse_header(parsed_mail, 'Message-ID'),
            'body-plain': None,
            'body-html': None
        }

        messages = []
        extracted = EmailParser.extract_message(parsed_mail)
        if extracted:
            if isinstance(extracted, list):
                messages.extend(extracted)
            else:
                messages.append(extracted)

        for m in messages:
            content_type = m[0]
            if content_type:
                content_type = content_type.lower()
            body = m[1].replace('\r\n', '\n')
            try:
                parameter = dict([x.split('=', 1) for x in content_type.split('; ')[1:]])
            except:
                parameter = {}
            if parameter.get('format') == 'flowed' and parameter.get('delsp') == 'yes':
                body = unfold_flowed(body)
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
            if callable(nkf):
                body = nkf('-Jwx', body)
                charset = 'utf-8'
            else:
                charset = 'ISO-2022-JP-2004'
                body = body.replace(b'\033$B', b'\033$(Q').replace(b'\033(J', b'\033(B')
        elif charset == 'SJIS':
            if callable(nkf):
                body = nkf('-Swx', body)
                charset = 'utf-8'
            else:
                charset = 'CP932'
        elif charset == 'EUC-JP':
            if callable(nkf):
                body = nkf('-Ew', body)
                charset = 'utf-8'
            else:
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
                del (chunks[i + 1])
            i += 1

        for chunk in chunks:
            if chunk.find('=?') >= 0:
                for decoded_chunk, charset in decode_header(chunk):
                    if charset:
                        if charset == 'ISO-2022-JP':
                            if callable(nkf):
                                decoded_chunk = nkf('-Jw', decoded_chunk)
                                charset = 'utf-8'
                            else:
                                charset = 'ISO-2022-JP-2004'
                                decoded_chunk = decoded_chunk \
                                    .replace(b'\033$B', b'\033$(Q') \
                                    .replace(b'\033(J', b'\033(B')
                        elif charset == 'SJIS':
                            if callable(nkf):
                                decoded_chunk = nkf('-Sw', decoded_chunk)
                                charset = 'utf-8'
                            else:
                                charset = 'CP932'
                        elif charset == 'EUC-JP':
                            if callable(nkf):
                                decoded_chunk = nkf('-Ew', decoded_chunk)
                                charset = 'utf-8'
                            else:
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
