# Softsync

_Sync softly_

Softsync helps you create and manage symbolic links to real files.  But, rather than
store the links as separate files, as with traditional symlinks (think: `ln -s source target`),
the links are stored in a single manifest file, per directory.  These kinds of links
are called "softlinks".

Softsync comprises a small collection of commands.  The main one is the `cp` command.
Use it to create new softlinks to real files (or other softlinks).  It can also be
used to "materialise" softlinked files into copies of their real counterparts (in
either hard or symbolic link form).

What's the point?  This utility may be of use for simulating the benefits of symbolic links
where the underlying storage supports the concept of files and directories, but does not
provide direct support for symbolic links.  A good example of this is Amazon's S3, which
can represent directory hierarchies, but has no native method of storing a symbolic link
to another object.
