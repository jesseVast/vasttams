"""Setup script for tams-client package"""

from setuptools import setup, find_packages

setup(
    name="vasttamsclient",
    version="1.0.0",
    description="Python client library for TAMS (Time-addressable Media Store) API",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Jesse Thaloor",
    author_email="jthaloor@vastdata.com",
    url="https://github.com/bbctams/bbctams",
    packages=find_packages(where="."),
    package_dir={"": "."},
    python_requires=">=3.10",
    install_requires=[
        "aiohttp>=3.9.0",
        "pydantic>=2.0.0",
        "typing-extensions>=4.0.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)

