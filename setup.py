from setuptools import setup, find_namespace_packages

setup(
    name='tiny-service',
    version='0.3.0',
    install_requires=[
        'ulid-py',
        'msgpack',
        'ntplib',
        'aiohttp',
        'pytest-asyncio@git+git://github.com/pytest-dev/pytest-asyncio.git#egg=pytest-asyncio',
        'tuple-class-codegen@git+ssh://git@gitlab.titan.com/titan/tuple-class-codegen#egg=tuple-class-codegen'
    ],
    description='Service Module',
    packages=find_namespace_packages(include=['titan.*', 'tests.*', 'scripts.*']),
    data_files=[
        ('',['wheel-map.json', 'obfuscation-config.json']),
    ],
    entry_points={
        'console_scripts': [
        ]
    }
)