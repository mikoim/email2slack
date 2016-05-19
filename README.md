# email2slack

E-mail forwarding script for Slack written in Python.
I tested on Python 3.x and Postfix.

## Demo

![Slack](slack-demo.png)

## Requirements

 - Python 3.x (Not tested in Python 2.x)
 - chardet : https://github.com/chardet/chardet
 - requests : https://github.com/kennethreitz/requests

## Getting Started

```bash
git clone https://github.com/mikoim/email2slack.git
cd email2slack

# Install dependencies
pip3 install -r requirements.txt

# Install email2slack
cp email2slack.py /usr/local/bin/email2slack.py && chmod +x /usr/local/bin/email2slack.py
cp email2slack /usr/local/etc/

# Before using, You must edit config file
vim /usr/local/etc/email2slack
```

### Postfix
```bash
vim /etc/postfix/aliases

...

iamauser: |/usr/local/bin/email2slack.py

...

newaliases
```