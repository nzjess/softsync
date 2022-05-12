import setuptools

setuptools.setup(
    name="softsync",
    version="0.7.0-beta",
    python_requires=">=3.6",
    license="MIT",
    license_file="LICENSE",
    description="Sync softly",
    long_description="""
Softsync helps you create and manage symbolic links to real files.  But, rather than
store the links as separate files, as with traditional symlinks (think: `ln -s source target`),
the links are stored in a single manifest file, per directory.  These kinds of links
are called "softlinks".

Softsync comprises a small collection of commands.  The main one is the `cp` command.
Use it to create new softlinks to real files (or other softlinks).  It can also be
used to "materialise" softlinked files into copies of their real counterparts (in
either real or symbolic link form).

What's the point?  This utility may be of use for simulating the benefits of symbolic links
where the underlying storage supports the concept of files and directories, but does not
provide direct support for symbolic links.  A good example of this is Amazon's S3, which has
no native method of storing a symbolic link to another object (and none of the many suggested
workarounds to this are suitable for your use-case).
    """,
    long_description_content_type="text/markdown",
    author="Jesse McLaughlin",
    author_email="jesse@ubercraft.org",
    url="https://github.com/nzjess/softsync",
    download_url="https://github.com/nzjess/softsync/archive/refs/tags/v0.7.0-beta.tar.gz",
    keywords=["FILESYSTEM", "SYMLINK", "UTILITY"],
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "pathlib3x>=1.3.9",
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.4"
        ],
    },
    entry_points={"console_scripts": ["softsync=softsync:run"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
)
