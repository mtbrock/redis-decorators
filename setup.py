from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')
repo_url = 'https://github.com/mtbrock/redis-decorators'

setup(
    name='redis-decorators',
    version='1.0.0',
    description='Cache function return values automatically with decorators.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=repo_url,
    author='Matt Brock',
    author_email='mtbrock@gmail.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        "Programming Language :: Python :: 3.10",
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='redis, redis-py, cache, caching, decorators',
    packages=find_packages(),
    python_requires='>=3.6, <4',
    install_requires=['redis'],
    project_urls={
        'Bug Reports': f'{repo_url}/issues',
        'Source': repo_url,
    },
)
