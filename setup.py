from setuptools import setup, find_packages

setup(
    name="Pyhorst",
    version="1.0.0",
    description="Bronkhorst Flow Controller Interface",
    author="Hugo Cruz",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        'propar',
    ],
    python_requires='>=3.7',
)