# Softsync

_Sync softly_

#### Python 3.6+

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
provide direct support for symbolic links.  A good example of this is Amazon's S3, which
can represent directory hierarchies, but has no native method of storing a symbolic link
to another object.

### Install

`pip install softsync`

_Requires pip version >= 21.3.1_

### Usage

`softsync -h`
```
Usage: softsync cmd [-h] [args...]

commands:
  cp
  ls
  repair
```

#### cp

`softsync cp -h`
```
usage: softsync cp [-h] [-R src[:dest]] [-f] [-r] [-s] [-v] [--dry]
                   src-path [dest-path]

positional arguments:
  src-path
  dest-path

optional arguments:
  -h, --help            show this help message and exit
  -R src[:dest], --root src[:dest]
                        root dir(s)
  -f, --force           copy over duplicates
  -r, --recursive       recurse into sub-directories
  -s, --symbolic        produce symlink
  -v, --verbose         verbose output
  --dry                 dry run only
```

#### ls

`softsync ls -h`
```
usage: softsync ls [-h] [-R root] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -R root, --root root  root dir
```

#### repair

`softsync repair -h`
```
usage: softsync repair [-h] [-R root] [-r] [-v] [--dry] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -R root, --root root  root dir
  -r, --recursive       recurse into sub-directories
  -v, --verbose         verbose output
  --dry                 dry run only
```

### Examples

Start with a directory containing some regular files:

```
./
└── foo/
      ├── hello.txt
      └── world.txt
```

Then make a soft copy of one of the files:

`softsync cp foo/hello.txt bar`

This will yield:

```
./
└── foo/
      ├── hello.txt
      └── world.txt
└── bar/
      └── .softsync
```

Where the new softsync manifest file `./bar/.softsync` will contain:

```json
{
  "softlinks": [
    {
      "name": "hello.txt",
      "link": "../foo/hello.txt"
    }
  ]
}
```

Then make a soft copy of one of the files, giving the copy a different name:

`softsync cp foo/world.txt bar/mars.txt`

Now the manifest will contain:

```json
{
  "softlinks": [
    {
      "name": "hello.txt",
      "link": "../foo/hello.txt"
    },
    {
      "name": "mars.txt",
      "link": "../foo/world.txt"
    }
  ]
}
```

The `ls` command can be used to list the contents of a directory, eg:

`softsync ls foo`

Yields:

```
hello.txt
world.txt
```

And:

`softsync ls bar`

Yields:
```
hello.txt -> ../foo/hello.txt
mars.txt -> ../foo/world.txt
```

Finally, make materialised copies of files that may exist only as
softlinks, optionally using the `symbolic` option to produce symlinks
if desired:

`softsync cp -R bar:qux hello.txt`

`softsync cp -R bar:qux mars.txt --symbolic`

Yields:

```
./
└── foo/
      ├── hello.txt
      └── world.txt
└── bar/
      └── .softsync
└── qux/
      ├── hello.txt
      └── mars.txt -> ../foo/world.txt
```

Where `hello.txt` is a regular copy of the original `hello.txt` file,
and `mars.txt` is a symlink pointing to the original `world.txt` file.

The `cp` command supports the normal globbing patterns characters
in the source path, e.g: `*.txt` and `h?llo.*`, etc.  Note you will
probably need to single quote glob patterns to prevent the shell from
expanding them first.

The `cp` command also supports copying all the files in a directory,
just pass the directory itself as the source path parameter.

### Programmatic usage (coming soon)

The command line interface is just that, an interface.  All the
commands can be used programmatically by importing the softsync API
into your Python code.

When used programmatically, the API is even more flexible.  For
example, it can be provided with a "file rename" mapping function which will
be used when copying multiple files from source to destination.
Custom file filtering functions can also be can be used to select which
files to process.
