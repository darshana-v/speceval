import os
import re
import time
import docker
import atexit
from typing import Optional

from .base import Verifier, VerificationResult, VerificationStatus


class SMTCheckerVerifier(Verifier):
    """Verify Solidity contracts using solc's built-in SMTChecker.

    SMTChecker is integrated into the Solidity compiler and supports
    checking assertions, overflow/underflow, division-by-zero,
    and user-provided require/assert conditions without external tools.
    """

    IMAGE_NAME = "speceval/solidity:latest"
    TMP_DIR = "/tmp/"

    def __init__(self, engine: str = "chc", timeout_per_query: int = 10000) -> None:
        assert engine in ("chc", "bmc", "all"), (
            f"SMTChecker engine must be 'chc', 'bmc', or 'all', got '{engine}'"
        )
        self.engine = engine
        self.timeout_per_query = timeout_per_query
        self.client = docker.from_env()
        self.container = self.client.containers.run(
            self.IMAGE_NAME,
            "/bin/bash",
            detach=True,
            tty=True,
        )
        assert self.container.status == "created", "Container failed to start"
        atexit.register(self.clean_up)

    def verify(
        self,
        spec_path: str,
        timeout: int = 1800,
        basedir: str = "",
    ) -> VerificationResult:
        spec_path = os.path.abspath(spec_path)
        start = time.monotonic()

        dest_dir = self.TMP_DIR if not basedir else os.path.join(self.TMP_DIR, basedir)
        if basedir:
            self.container.exec_run(["mkdir", "-p", dest_dir])

        _copy_to_container(self.container, spec_path, dest_dir)
        path_in_container = os.path.join(dest_dir, os.path.basename(spec_path))

        cmd = (
            f"timeout {timeout} solc"
            f" --model-checker-engine {self.engine}"
            f" --model-checker-timeout {self.timeout_per_query}"
            f" --model-checker-targets assert,underflow,overflow,divByZero"
            f" {path_in_container}"
        )

        exec_result = self.container.exec_run(cmd.split())
        duration = time.monotonic() - start

        if exec_result.exit_code == 124:
            _cleanup_tar(spec_path)
            return VerificationResult(
                status=VerificationStatus.TIMEOUT,
                error_count=-1,
                raw_output="Timeout",
                spec_path=spec_path,
                duration_seconds=duration,
            )

        output = exec_result.output.decode("utf-8")
        _cleanup_tar(spec_path)
        return self._extract_output(output, spec_path, duration)

    def _extract_output(
        self, output: str, spec_path: str, duration: float
    ) -> VerificationResult:
        output = output.replace(os.getcwd() + "/", "")

        compilation_errors = re.findall(r"Error:", output)
        if compilation_errors and "CHC" not in output and "BMC" not in output:
            return VerificationResult(
                status=VerificationStatus.COMPILE_ERROR,
                error_count=999,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )

        warnings = re.findall(r"Warning: CHC: .*might", output)
        assertion_failures = re.findall(r"Warning: CHC: Assertion violation", output)
        overflow_failures = re.findall(r"Warning: CHC: .*overflow", output)

        n_failures = len(assertion_failures) + len(overflow_failures) + len(warnings)

        if "Internal compiler error" in output:
            return VerificationResult(
                status=VerificationStatus.INTERNAL_ERROR,
                error_count=-5,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )

        if n_failures > 0:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                error_count=n_failures,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            error_count=0,
            raw_output=output,
            spec_path=spec_path,
            duration_seconds=duration,
        )

    def clean_up(self) -> None:
        try:
            self.container.stop()
            self.container.remove()
        except Exception:
            pass


def _copy_to_container(container, src_path: str, dest_dir: str) -> None:
    import tarfile
    import io

    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar.add(src_path, arcname=os.path.basename(src_path))
    tar_stream.seek(0)
    container.put_archive(dest_dir, tar_stream)


def _cleanup_tar(path: str) -> None:
    tar_file = path + ".tar"
    if os.path.exists(tar_file):
        os.remove(tar_file)
