from pathlib import Path

from setuptools import find_packages, setup

long_description = Path("README.md").read_text(encoding="utf-8")

setup(
    name="revvlink",
    version="1.0.0",
    author="@JustNixx and @IamGroot",
    author_email="nksmay13@gmail.com",
    description=(
        "A robust and powerful, fully asynchronous Lavalink wrapper built for discord.py in Python."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ded-lmfao/RevvLink",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "aiohttp>=3.9.0,<4",
        "discord.py>=2.4.0",
        "yarl>=1.9.4",
        "typing_extensions>=4.5.0",
        "async_timeout; python_version < '3.11'",
    ],
)
