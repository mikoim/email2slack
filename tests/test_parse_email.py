from email2slack import EmailParser


def test_text_email():
    email = """Return-Path: <test_from@test>
X-Original-To: test_to@test
Delivered-To: test_to@test
From: test_from@test
Subject: subject_test
To: test_to@test
Date: Sat, 12 Nov 2016 23:37:27 +0900 (JST)

message_test"""

    assert EmailParser.parse(email) == {
        'From': 'test_from@test',
        'To': 'test_to@test',
        'Subject': 'subject_test',
        'body-plain': 'message_test',
        'body-html': None
    }


def test_text_email_abnormal():
    email = """Return-Path: <test_from@test>
X-Original-To: test_to@test
Delivered-To: test_to@test

message_test"""

    assert EmailParser.parse(email) == {
        'From': '',
        'To': '',
        'Subject': '',
        'body-plain': 'message_test',
        'body-html': None
    }


def test_text_email_utf8():
    email = """Return-Path: <test_from@test>
X-Original-To: test_to@test
Delivered-To: test_to@test
From: test_from@test
Subject: =?UTF-8?B?8J+RgfCfkJ1N?=
To: test_to@test
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: base64

8J+QjQ0K"""

    assert EmailParser.parse(email) == {
        'From': 'test_from@test',
        'To': 'test_to@test',
        'Subject': '👁🐝M',
        'body-plain': '🐍\r\n',
        'body-html': None
    }


def test_html_email():
    email = """Return-Path: <test_from@test>
X-Original-To: test_to@test
Delivered-To: test_to@test
From: test_from@test
Subject: subject_test
To: test_to@test
Date: Sat, 12 Nov 2016 23:37:27 +0900 (JST)
Content-Type: multipart/alternative; boundary=94eb2c14a07ea8d44d05411b334d

--94eb2c14a07ea8d44d05411b334d
Content-Type: text/plain; charset=UTF-8

message_test

--94eb2c14a07ea8d44d05411b334d
Content-Type: text/html; charset=UTF-8

<b>message_test</b>

--94eb2c14a07ea8d44d05411b334d--"""

    assert EmailParser.parse(email) == {
        'From': 'test_from@test',
        'To': 'test_to@test',
        'Subject': 'subject_test',
        'body-plain': 'message_test\n',
        'body-html': '<b>message_test</b>\n'
    }
