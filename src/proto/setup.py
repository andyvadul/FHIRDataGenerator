#!/usr/bin/env python3
"""
Setup script for FHIR Resource Data Generator
Alternative to requirements.txt for more advanced dependency management
"""

from setuptools import setup, find_packages

# Read README for long description
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "FHIR Resource Data Generator - Generate synthetic FHIR data"

setup(
    name="fhir-data-generator",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Generate synthetic FHIR resource data with flattened schema",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/fhir-data-generator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    
    # Core dependencies (always required)
    install_requires=[
        "fhir.resources>=7.0.0",
        "pandas>=1.5.0", 
        "pyarrow>=10.0.0",
    ],
    
    # Optional dependencies grouped by feature
    extras_require={
        "json5": ["json5"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov",
            "black",
            "flake8", 
            "mypy",
            "pre-commit",
        ],
        "docs": [
            "mkdocs",
            "mkdocs-material",
        ],
        "all": [
            "json5",
            "pytest>=7.0.0",
            "pytest-cov", 
            "black",
            "flake8",
            "mypy",
            "pre-commit",
            "mkdocs",
            "mkdocs-material",
        ]
    },
    
    # Entry points for command-line usage
    entry_points={
        "console_scripts": [
            "fhir-generate=generate_fhir_data:main",
        ],
    },
)