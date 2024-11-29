from setuptools import setup, find_packages

setup(
    name="accountability",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "robin_stocks",
    ],
) 