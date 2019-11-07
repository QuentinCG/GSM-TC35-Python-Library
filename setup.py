from setuptools import setup
import io

with io.open('README.md', 'r', encoding='utf-8') as readme_file:
  readme = readme_file.read()

setup(
    name='GSMTC35',
    version='2.0',
    description='GSM TC35/MC35 controller (Send/Receive SMS/MMS/Call and a lot more!)',
    long_description=readme,
    url='https://github.com/QuentinCG/GSM-TC35-Python-Library',
    author='Quentin Comte-Gaz',
    author_email='quentin@comte-gaz.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Communications :: Telephony',
        'Topic :: Terminals :: Serial',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS X',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='gsm pdu tc35 mc35 at sms mms call phone pin puk phonebook imei imsi ucs2 7bit forward unlock lock',
    packages=["GSMTC35"],
    platforms='any',
    install_requires=["pyserial"],
    tests_require=["mock"],
    test_suite="tests",
    extras_require={
      'restapi': ["flask", "flask_restful", "flask-httpauth", "pyopenssl"]
    }
)
