from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


@dataclass
class SandboxRunResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    timed_out: bool
    backend: str


class SandboxExecutionError(RuntimeError):
    """Raised when the requested sandbox backend is unavailable."""


class BaseSandbox:
    backend_name = "unknown"

    def run(
        self,
        workspace: Path,
        command: list[str],
        *,
        stdin: str = "",
        env: dict[str, str] | None = None,
        timeout_ms: int = 2000,
        memory_limit_mb: int = 64,
    ) -> SandboxRunResult:
        raise NotImplementedError


class LocalSandbox(BaseSandbox):
    """Fallback runner used when Docker is unavailable in the current host."""

    backend_name = "local"

    def run(
        self,
        workspace: Path,
        command: list[str],
        *,
        stdin: str = "",
        env: dict[str, str] | None = None,
        timeout_ms: int = 2000,
        memory_limit_mb: int = 64,
    ) -> SandboxRunResult:
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)

        runner = list(command)
        prlimit = shutil.which("prlimit")
        if prlimit is not None:
            memory_bytes = max(memory_limit_mb, 32) * 1024 * 1024
            cpu_seconds = max(int(timeout_ms / 1000) + 1, 1)
            runner = [
                prlimit,
                f"--as={memory_bytes}",
                f"--cpu={cpu_seconds}",
                "--",
                *command,
            ]

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                runner,
                cwd=workspace,
                input=stdin,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=proc_env,
                timeout=max(timeout_ms / 1000, 0.1),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = (time.perf_counter() - started) * 1000
            return SandboxRunResult(
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                exit_code=-1,
                execution_time_ms=elapsed,
                timed_out=True,
                backend=self.backend_name,
            )

        elapsed = (time.perf_counter() - started) * 1000
        return SandboxRunResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            execution_time_ms=elapsed,
            timed_out=False,
            backend=self.backend_name,
        )


class DockerSandbox(BaseSandbox):
    backend_name = "docker"

    def __init__(self, image: str) -> None:
        self.image = image

    def run(
        self,
        workspace: Path,
        command: list[str],
        *,
        stdin: str = "",
        env: dict[str, str] | None = None,
        timeout_ms: int = 2000,
        memory_limit_mb: int = 64,
    ) -> SandboxRunResult:
        if shutil.which("docker") is None:
            raise SandboxExecutionError("docker command not found")

        docker_command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            "1",
            "--memory",
            f"{max(memory_limit_mb, 64)}m",
            "--pids-limit",
            "64",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--mount",
            f"type=bind,src={workspace},dst=/workspace",
            "--workdir",
            "/workspace",
            "--user",
            "1000:1000",
        ]
        merged_env = env or {}
        for key, value in merged_env.items():
            docker_command.extend(["-e", f"{key}={value}"])
        docker_command.append(self.image)
        docker_command.extend(command)

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                docker_command,
                input=stdin,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=max(timeout_ms / 1000, 0.1),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = (time.perf_counter() - started) * 1000
            return SandboxRunResult(
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                exit_code=-1,
                execution_time_ms=elapsed,
                timed_out=True,
                backend=self.backend_name,
            )

        elapsed = (time.perf_counter() - started) * 1000
        return SandboxRunResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            execution_time_ms=elapsed,
            timed_out=False,
            backend=self.backend_name,
        )


def docker_backend_available(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return inspect.returncode == 0


@lru_cache(maxsize=1)
def get_sandbox() -> BaseSandbox:
    settings = get_settings()
    backend = settings.sandbox_backend.lower()
    if backend == "local":
        return LocalSandbox()
    if backend == "docker":
        if not docker_backend_available(settings.sandbox_docker_image):
            raise SandboxExecutionError(f"Docker sandbox image is unavailable: {settings.sandbox_docker_image}")
        return DockerSandbox(settings.sandbox_docker_image)
    if docker_backend_available(settings.sandbox_docker_image):
        return DockerSandbox(settings.sandbox_docker_image)
    return LocalSandbox()


def dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
