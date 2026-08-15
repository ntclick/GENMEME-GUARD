# conftest.py
# genlayer-test Direct Mode automatically handles WASI & SDK paths via direct_deploy

import os
import sys
import tempfile

# The genvm release the direct tests run against. Contract headers pin a runner
# hash, but gltest picks the *release tarball* to look that hash up in, and by
# default it asks GitHub for the newest one. That broke the whole suite once
# already: the newest tag became v0.3.0-rc7, a pre-release that ships no
# genvm-universal.tar.xz, so every test failed on a 404 from the download rather
# than on anything in the contract. A test run's toolchain should not change
# because someone else cut a tag, so the version is pinned here too.
#
# Bump this deliberately, together with the "Depends" hash in the contract
# header, and only after the suite passes on the new release. GENVM_RELEASE
# overrides it for a one-off check against another version.
GENVM_RELEASE = os.environ.get("GENVM_RELEASE", "v0.2.16")


def _pin_genvm_release() -> None:
    """Make gltest resolve the pinned release instead of the newest one.

    Two things are patched, because gltest has two ways of choosing:
    get_latest_version() asks GitHub, and list_cached_versions() reuses whatever
    is already on disk — reverse-sorted as strings, which puts "v0.2.9" ahead of
    "v0.2.16". Neither is what this suite wants. Downloading is untouched: the
    tarball is still cached, and a run only fetches when the pinned one is
    genuinely absent.
    """
    try:
        from gltest.direct import sdk_loader
    except ImportError:
        return

    if getattr(sdk_loader, "_release_pinned", False):
        return

    sdk_loader.get_latest_version = lambda: GENVM_RELEASE
    sdk_loader.list_cached_versions = lambda: []
    sdk_loader._release_pinned = True


def _patch_windows_fd0_injection() -> None:
    """Work around a Windows-only bug in gltest.direct.loader.

    _inject_message_to_fd0() dup2()s a temp file onto stdin (fd 0) and then
    calls os.unlink(path) while that fd is still open. POSIX allows deleting
    an open file (the inode survives until the last handle closes); Windows
    does not, so the same call raises
    PermissionError: [WinError 32] The process cannot access the file
    because it is being used by another process.

    This patches in a Windows-safe version that just swallows the unlink
    failure — the temp file is leaked to the OS temp dir instead of being
    removed immediately, same tradeoff genlayer-test accepts on POSIX once
    the last fd closes. No contract behavior changes; this only affects how
    the test harness feeds the calldata message into the WASI stdin mock.
    """
    if sys.platform != "win32":
        return

    try:
        from gltest.direct import loader as gltest_loader
    except ImportError:
        return

    if getattr(gltest_loader, "_win_fd0_patched", False):
        return

    original = gltest_loader._inject_message_to_fd0

    def _patched_inject_message_to_fd0(vm):
        import builtins

        real_unlink = os.unlink

        def _safe_unlink(path, *args, **kwargs):
            try:
                real_unlink(path, *args, **kwargs)
            except PermissionError:
                pass  # file still open via dup'd fd 0 on Windows; leaked to temp dir

        os.unlink = _safe_unlink
        try:
            return original(vm)
        finally:
            os.unlink = real_unlink

    gltest_loader._inject_message_to_fd0 = _patched_inject_message_to_fd0
    gltest_loader._win_fd0_patched = True


_pin_genvm_release()
_patch_windows_fd0_injection()
