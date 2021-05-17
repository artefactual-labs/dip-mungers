from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="dip-mungers",
    description="DIP download and upload scripts.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/axfelix/dip-mungers",
    author="Alex Garnett",
    author_email="axfelix@gmail.com",
    license="MIT",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dip-metadata=dip_mungers.dip_metadata:main",
            "dip-retrieve=dip_mungers.dip_retrieve:main",
            "dip-upload=dip_mungers.dip_upload:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
