# conftest.py
# genlayer-test Direct Mode automatically handles WASI & SDK paths via direct_deploy

import os
import sys
import tempfile


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


_patch_windows_fd0_injection()
