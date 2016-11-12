email2slack
===========

|PyPI version| |Build Status| |Coverage Status|

MIME E-mail forwarding script for Slack written in Python.

I tested on Python 3.5 and Postfix only. Please report test report and
sample configuration on other MTAs.

Demo
----

.. figure:: slack-demo.png
   :alt: Slack

   Slack

Requirements
------------

-  Python >= 3.3
-  chardet : https://github.com/chardet/chardet
-  requests : https://github.com/kennethreitz/requests

Getting Started
---------------

Install email2slack
~~~~~~~~~~~~~~~~~~~

From PyPI
^^^^^^^^^

.. code:: bash

    # Install email2slack
    pip3 install email2slack

    # Fetch configuration file from GitHub
    cd /usr/local/etc/
    curl -O https://raw.githubusercontent.com/mikoim/email2slack/master/email2slack

    # Before using, You must edit config file
    vim /usr/local/etc/email2slack

In this case, setuptools create script to call email2slack and place it
in ``bin`` directory automatically. So you should use the script in
Setup MTA section.

From GitHub repository
^^^^^^^^^^^^^^^^^^^^^^

.. code:: bash

    git clone https://github.com/mikoim/email2slack.git
    cd email2slack

    # Install dependencies
    pip3 install -r requirements.txt

    # Install email2slack
    cp email2slack.py /usr/local/bin/email2slack.py && chmod +x /usr/local/bin/email2slack.py
    cp email2slack /usr/local/etc/

    # Before using, You must edit config file
    vim /usr/local/etc/email2slack

Setup MTA
~~~~~~~~~

Postfix
^^^^^^^

.. code:: bash

    vim /etc/postfix/aliases

    ...

    # notice only, not forward
    user: |/usr/local/bin/email2slack.py

    # notice and forward e-mail to another user
    user: anotheruser, |/usr/local/bin/email2slack.py

    # notice and leave e-mail on same user
    user: \user, |/usr/local/bin/email2slack.py

    ...

    newaliases

.. |PyPI version| image:: https://badge.fury.io/py/email2slack.svg
   :target: https://badge.fury.io/py/email2slack
.. |Build Status| image:: https://travis-ci.org/mikoim/email2slack.svg?branch=master
   :target: https://travis-ci.org/mikoim/email2slack
.. |Coverage Status| image:: https://coveralls.io/repos/github/mikoim/email2slack/badge.svg?branch=master
   :target: https://coveralls.io/github/mikoim/email2slack?branch=master
