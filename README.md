# Softsync

_Sync softly_

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

### Requires

python >= 3.6

pip >= 21.3.1

### Install

`pip install softsync`

`alias ss=softsync`

### Usage

`softsync -h`
```
Usage: softsync cmd [-h] [args...]

commands:
  cp
  rm
  ls
  repair
```

#### cp

The `cp` command is the central softsync command.  It has three main functions,
depending on what parameters are passed.  First, it creates softlinks, either to
real files or to other softlinks.  Second, it can reconstruct a root for just a
selection of files, into another root, following softlinks as required in order
to ensure that the real files that are softlinked to are present in the
reconstructed root.  And third, it can materialise real (or symlinked) copies
of softlinked files from one root into another.

`softsync cp -h`

```
usage: softsync cp [-h] [-R src[:dest]] [-f] [-r] [-c] [-s] [-v] [--dry]
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
  -c, --reconstruct     reconstruct file hierarchy
  -s, --symbolic        produce symlink
  -v, --verbose         verbose output
  --dry                 dry run only
```

#### rm

The `rm` command can be used to remove existing softlinks (or even real files,
if you really want to).

`softsync rm -h`

```
usage: softsync rm [-h] [-R root] [-f] [-r] [-v] [--dry] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -R root, --root root  root dir
  -f, --force           copy over duplicates
  -r, --recursive       recurse into sub-directories
  -v, --verbose         verbose output
  --dry                 dry run only
```

#### ls

The `ls` command can be used to produce listings the files in a directory,
including any softlinks present.

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

The `repair` command can be used to re-write the softsync manifest file in a
given directory according to the current contents of the directory - this may
be necessary if the softlink manifest gets into conflict with the real files
present.

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

_Note: none of the commands support the **--recursive** option, yet._

### Examples

Start with a directory containing some regular files and folders, like this:

```
./
├── alpha/
│   └── foo/
│       ├── hello.txt
│       └── world.txt
├── omega/
└── zeta/
```

This represents three "root" directories, `alpha`, `omega` and `zeta`.  The first
starts out with some normal files. The second two are empty, for now.

First make a soft copy of the `foo/hello.txt` file into a new `bar` subdirectory,
within the `alpha` root:

`softsync cp -R alpha foo/hello.txt bar`

This will yield:

```
./
├── alpha/
│   ├── foo/
│   │   ├── hello.txt
│   │   └── world.txt
│   └── bar/
│       └── .softsync
├── omega/
└── zeta/
```

Where the new softsync manifest file `./alpha/bar/.softsync` will contain:

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

Then make a soft copy of the `foo/world.txt` file, but this time giving the
copy a different name:

`softsync cp -R alpha foo/world.txt bar/mars.txt`

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

`softsync ls -R alpha foo`

Yields:

```
hello.txt
world.txt
```

And:

`softsync ls -R alpha bar`

Yields:
```
hello.txt -> ../foo/hello.txt
mars.txt -> ../foo/world.txt
```

Now, reconstruct a root from an existing one for just the file or files
you are interested in:

`softsync cp -R alpha:omega bar/mars.txt --reconstruct`

Yields:

```
./
├── alpha/
│   ├── foo/
│   │   ├── hello.txt
│   │   └── world.txt
│   └── bar/
│       └── .softsync
├── omega/
│   ├── foo/
│   │   └── world.txt
│   └── bar/
│       └── .softsync
└── zeta/
```

Where the softsync manifest file in `./omega/bar/.softsync` will have the
same contents as in the first step above.

Now reconstruct based on the `hello.txt` file, but this time using the
symbolic option:

`softsync cp -R alpha:omega bar/hello.txt --reconstruct --symbolic`

This yields:

```
./
├── alpha/
│   ├── foo/
│   │   ├── hello.txt
│   │   └── world.txt
│   └── bar/
│       └── .softsync
├── omega/
│   ├── foo/
│   │   ├── hello.txt -> ../../alpha/foo/world.txt
│   │   └── world.txt
│   └── bar/
│       └── .softsync
└── zeta/
```

The `./omega/bar/.softsync` manifest file will now contain softlinks for
both files.

Finally, make materialised copies of files that may exist only as
softlinks, optionally using the `symbolic` option to produce symlinks
if desired:

`softsync cp -R omega:zeta bar/hello.txt`

`softsync cp -R omega:zeta bar/mars.txt --symbolic`

Yields:

```
./
├── alpha/
│   ├── foo/
│   │   ├── hello.txt
│   │   └── world.txt
│   └── bar/
│       └── .softsync
├── omega/
│   ├── foo/
│   │   ├── hello.txt -> ../../alpha/foo/world.txt
│   │   └── world.txt
│   └── bar/
│       └── .softsync
└── zeta/
    └── bar/
        ├── hello.txt
        └── mars.txt -> ../../omega/foo/world.txt
```

Where the new `hello.txt` is a regular copy of the original `hello.txt` file,
and `mars.txt` is a symlink pointing to the original `world.txt` file.

The `cp` command supports the normal globbing patterns characters
in the source path, e.g: `*.txt` and `h?llo.*`, etc.  Note you will
probably need to single quote glob patterns to prevent the shell from
expanding them first.

The `cp` command also supports copying all the files in a directory,
just pass the directory itself as the source path parameter.

### Programmatic usage

The command line interface is just that, an interface.  All the
commands can be used programmatically by importing the softsync API
into your Python code.

The following is the programmatic equivalent of a couple of the commands from
the CLI examples above (and assuming the same working directory):

```python
from pathlib3x import Path

from softsync.common import Root, Options
from softsync.commands.cp import softsync_cp

# softsync cp -R alpha foo/world.txt bar/mars.txt
root = Root("alpha")
src_path = Path("foo/world.txt")
dest_path = Path("bar/mars.txt")
files = softsync_cp(
    root,
    src_path=src_path,
    dest_path=dest_path,
)
for file in files:
    print(file)

# softsync cp -R alpha:omega bar/mars.txt --reconstruct
src_root = Root("alpha")
dest_root = Root("omega")
src_path = Path("bar/mars.txt")
options = Options(
    reconstruct=True,
)
files = softsync_cp(
    src_root=src_root,
    src_path=src_path,
    dest_root=dest_root,
    options=options,
)
for file in files:
    print(file)

# softsync cp -R omega:zeta bar/mars.txt --symbolic
src_root = Root("omega")
dest_root = Root("zeta")
src_path = Path("bar/mars.txt")
options = Options(
    symbolic=True,
)
files = softsync_cp(
    src_root=src_root,
    src_path=src_path,
    dest_root=dest_root,
    options=options,
)
for file in files:
    print(file)
```

When used programmatically, the API is even more flexible.  For example,
it can be provided with a file name mapping function, which will be used
when copying multiple files from source to destination. Custom file
filtering functions can also be can be used to select which files to copy.
