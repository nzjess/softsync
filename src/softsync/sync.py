from pathlib3x import Path

from typing import TYPE_CHECKING

from softsync.exception import SyncException

if TYPE_CHECKING:
    from softsync.common import Options
    from softsync.context import SoftSyncContext


def sync(src_file: Path, src_ctx: "SoftSyncContext",
         dest_file: Path, dest_ctx: "SoftSyncContext",
         options: "Options") -> None:
    if dest_ctx.root.scheme.path_exists(dest_file):
        if dest_ctx.root.scheme.path_is_dir(dest_file):
            raise SyncException(f"destination is a directory: {dest_file}")
        if not options.force:
            raise SyncException(f"destination file exists: {dest_file}")
        if not options.dry_run:
            dest_ctx.root.scheme.path_unlink(dest_file)
    if not options.dry_run:
        dest_ctx.root.scheme.path_mkdir(dest_file.parent)
        if options.symbolic:
            src_ctx.root.scheme.path_symlink_to(src_file, dest_file)
        else:
            src_ctx.root.scheme.path_hardlink_to(src_file, dest_file)
