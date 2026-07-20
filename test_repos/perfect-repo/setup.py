from setuptools import find_packages, setup

setup(
    name="awesome-processor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
    ],
)
