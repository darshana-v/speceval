import os
import re
import time
import docker
import atexit

from .base import Verifier, VerificationResult, VerificationStatus
from .smtchecker import _copy_to_container, _cleanup_tar


class OpenJMLVerifier(Verifier):

    IMAGE_NAME = "thanhlecong/openjml:latest"
    TMP_DIR = "/tmp/"

    def __init__(self, version: int = 21) -> None:
        assert version in (21, 17), "OpenJML version must be 21 or 17"
        self.version = version
        self.client = docker.from_env()
        self.container = self.client.containers.run(
            self.IMAGE_NAME, "/bin/bash", detach=True, tty=True,
        )
        assert self.container.status == "created", "Container failed to start"
        atexit.register(self.clean_up)

    def verify(
        self, spec_path: str, timeout: int = 1800, basedir: str = "",
    ) -> VerificationResult:
        spec_path = os.path.abspath(spec_path)
        start = time.monotonic()

        dest_dir = self.TMP_DIR if not basedir else os.path.join(self.TMP_DIR, basedir)
        if basedir:
            self.container.exec_run(["mkdir", "-p", dest_dir])

        _copy_to_container(self.container, spec_path, dest_dir)
        path_in_container = os.path.join(dest_dir, os.path.basename(spec_path))

        cmd = (
            f"timeout {timeout}"
            f" /home/openjml{self.version}/openjml"
            f" --esc --prover=cvc4 --nullable-by-default"
            f" --esc-max-warnings 1 {path_in_container}"
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
        self, output: str, spec_path: str, duration: float,
    ) -> VerificationResult:
        output = output.replace(os.getcwd() + "/", "")

        failure_count = len(re.findall(r"(\d+) verification failure", output))
        warning_count = len(re.findall(r"(\d+) warning", output))
        compilation_errors = len(re.findall(r"(\d+) error", output))

        if "Internal JML bug" in output:
            return VerificationResult(
                status=VerificationStatus.INTERNAL_ERROR,
                error_count=-5,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )

        total = failure_count + warning_count + compilation_errors
        if total > 0:
            status = VerificationStatus.FAILED if failure_count > 0 else VerificationStatus.COMPILE_ERROR
            return VerificationResult(
                status=status,
                error_count=total,
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
