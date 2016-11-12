from codecs import open

from setuptools import setup

try:
    long_description = open('README.rst').read()
except:
    long_description = 'MIME E-mail forwarding script for Slack written in Python'

setup(
    name='email2slack',

    version='1.0.0a3',

    description='MIME E-mail forwarding script for Slack written in Python',
    long_description=long_description,

    url='https://github.com/mikoim/email2slack',

    author='Eshin Kunishima',
    author_email='ek@esh.ink',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Topic :: Communications',
        'Topic :: Communications :: Email',
        'Topic :: Communications :: Email :: Mail Transport Agents',
        'Topic :: Communications :: Chat',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='email slack forwarding',

    py_modules=['email2slack'],

    install_requires=[
        'chardet>=2.3.0',
        'requests>=2.10.0'
    ],

    entry_points={
        'console_scripts': [
            'email2slack = email2slack:main',
        ],
    },
)
