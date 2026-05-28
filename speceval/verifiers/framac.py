import os
import re
import time
import docker
import atexit

from .base import Verifier, VerificationResult, VerificationStatus
from .smtchecker import _copy_to_container, _cleanup_tar


class FramaCVerifier(Verifier):

    IMAGE_NAME = "framac/frama-c:26.0.debian"
    TMP_DIR = "/tmp/"

    def __init__(self) -> None:
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
            f"timeout {timeout} frama-c -wp -wp-precond-weakening"
            f" -wp-no-callee-precond -warn-signed-overflow -warn-unsigned-overflow"
            f" -warn-invalid-pointer -wp-model Typed+ref"
            f" -wp-prover Alt-Ergo,Z3 -wp-print -wp-timeout 10"
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
        self, output: str, spec_path: str, duration: float,
    ) -> VerificationResult:
        lines = output.split("\n")

        for line in lines:
            if any(s in line for s in (
                "[kernel] Frama-C aborted:",
                "[kernel] Plug-in wp aborted",
                "[wp] Warning: No goal generated",
                "error: invalid preprocessing directive",
            )):
                return VerificationResult(
                    status=VerificationStatus.COMPILE_ERROR,
                    error_count=999,
                    raw_output=output,
                    spec_path=spec_path,
                    duration_seconds=duration,
                )

        if "Unexpected error" in output and "Please report as 'crash'" in output:
            return VerificationResult(
                status=VerificationStatus.INTERNAL_ERROR,
                error_count=-5,
                raw_output="Internal Frama-C bug",
                spec_path=spec_path,
                duration_seconds=duration,
            )

        timeout_in_requires = 0
        all_timeout = 0
        for line in lines:
            if "[wp] [Timeout] typed_" in line:
                if "_requires (" in line or "_requires_" in line:
                    timeout_in_requires += 1
                all_timeout += 1

        for line in lines:
            if "[wp] Proved goals:" in line:
                proportion = line.split(":")[-1]
                left, right = proportion.split("/")
                left, right = int(left.strip()), int(right.strip())
                if left + timeout_in_requires == right:
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        error_count=0,
                        raw_output=output,
                        spec_path=spec_path,
                        duration_seconds=duration,
                    )
                n_errors = right - left - all_timeout
                if n_errors <= 0:
                    return VerificationResult(
                        status=VerificationStatus.TIMEOUT,
                        error_count=-1,
                        raw_output=output,
                        spec_path=spec_path,
                        duration_seconds=duration,
                    )
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    error_count=n_errors,
                    raw_output=output,
                    spec_path=spec_path,
                    duration_seconds=duration,
                )

        return VerificationResult(
            status=VerificationStatus.TIMEOUT,
            error_count=-1,
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
