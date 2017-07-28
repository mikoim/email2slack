from setuptools import setup

try:
    import pypandoc

    long_description = pypandoc.convert('README.md', 'rst')
except:
    long_description = 'MIME E-mail forwarding script for Slack written in Python'

setup(
    name='email2slack',
    version='1.0.0a5',
    description='MIME E-mail forwarding script for Slack written in Python',
    long_description=long_description,
    url='https://github.com/mikoim/email2slack',
    author='Eshin Kunishima',
    author_email='ek@esh.ink',
    packages=['email2slack'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Communications',
        'Topic :: Communications :: Email',
        'Topic :: Communications :: Email :: Mail Transport Agents',
        'Topic :: Communications :: Chat',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='email slack forwarding',
    requires=[
        'beautifulsoup4',
        'certifi',
        'chardet',
        'idna',
        'lxml',
        'requests',
        'urllib3',
    ],
    install_requires=[
        'beautifulsoup4==4.6.0',
        'certifi==2017.4.17',
        'chardet==3.0.4',
        'idna==2.5',
        'lxml==3.8.0',
        'requests==2.18.2',
        'urllib3==1.22',
    ],
    entry_points={
        'console_scripts': [
            'email2slack = email2slack:main',
        ],
    },
)
