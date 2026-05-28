import os
import re
import time
import docker
import atexit

from .base import Verifier, VerificationResult, VerificationStatus
from .smtchecker import _copy_to_container, _cleanup_tar


class PrustiVerifier(Verifier):

    IMAGE_NAME = "formalbench/prusti:latest"
    TEMPLATE_DIR = "/home/prusti-template"
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

        if basedir:
            project_dir = os.path.join(self.TMP_DIR, basedir, "prusti-verify")
        else:
            project_dir = os.path.join(self.TMP_DIR, "prusti-verify")

        self.container.exec_run(["rm", "-rf", project_dir])
        self.container.exec_run(["cp", "-r", self.TEMPLATE_DIR, project_dir])

        _copy_to_container(self.container, spec_path, self.TMP_DIR)
        path_in_container = os.path.join(self.TMP_DIR, os.path.basename(spec_path))
        src_path = os.path.join(project_dir, "src", "lib.rs")
        self.container.exec_run(["cp", path_in_container, src_path])

        cmd = f"timeout {timeout} cargo-prusti"
        exec_result = self.container.exec_run(cmd.split(), workdir=project_dir)
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

        if "Successful verification" in output:
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                error_count=0,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )

        if "internal compiler error" in output or "Prusti internal error" in output:
            return VerificationResult(
                status=VerificationStatus.INTERNAL_ERROR,
                error_count=-5,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )

        verification_errors = len(re.findall(
            r"error: \[Prusti: verification error\]", output
        ))
        compilation_errors = len(re.findall(r"error\[E\d+\]", output))
        if compilation_errors == 0 and "could not compile" in output:
            compilation_errors = len(re.findall(r"^error:", output, re.MULTILINE))

        if verification_errors > 0:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                error_count=verification_errors,
                raw_output=output,
                spec_path=spec_path,
                duration_seconds=duration,
            )
        if compilation_errors > 0:
            return VerificationResult(
                status=VerificationStatus.COMPILE_ERROR,
                error_count=999,
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
