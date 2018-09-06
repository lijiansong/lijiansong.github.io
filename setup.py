from setuptools import setup, find_packages

print(find_packages())

setup(
    name='mysite',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'libsass>=0.13.3,<1',
        'PyYAML>=3.12,<4',
        'Markdown>=2.6.9,<3',
        'Pygments>=2.2.0,<3',
        'htmlmin>=0.1.11,<2',
        'rcssmin>=1.0.6,<2',
        'rjsmin>=1.0.12,<2',
        'Jinja2>=2.9.6,<3',
        'isodate>=0.6.0,<1',
        'python-dateutil>=2.7.3,<3',
    ],
    extras_require={
        "dev": [
            "mypy>=0.620,<1",
            "flake8>=3.5.0,<4",
        ],
    },
    setup_requires=[],
    tests_require=[],
)
