from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cico_pipeline.config import load_config


CHAT_MODELS = {"splitter", "planner", "generator"}
ALL_MODELS = ["embedding", "splitter", "planner", "generator"]


def endpoint_host_port(base_url: str) -> tuple[str, int]:
    parsed = urlparse(base_url)
    host = parsed.hostname or "0.0.0.0"
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if host in {"0.0.0.0", "::"}:
        host = "0.0.0.0"
    return host, port


def vllm_command(name: str, cfg: dict[str, Any]) -> list[str]:
    host, port = endpoint_host_port(cfg["base_url"])
    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        cfg["model_name_or_path"],
        "--served-model-name",
        cfg["model_name_or_path"],
        "--host",
        host,
        "--port",
        str(port),
        "--trust-remote-code",
    ]
    service_cfg = cfg.get("service", {})
    if service_cfg.get("tensor_parallel_size") is not None:
        command.extend(["--tensor-parallel-size", str(service_cfg["tensor_parallel_size"])])
    if service_cfg.get("gpu_memory_utilization") is not None:
        command.extend(["--gpu-memory-utilization", str(service_cfg["gpu_memory_utilization"])])
    if service_cfg.get("max_model_len") is not None:
        command.extend(["--max-model-len", str(service_cfg["max_model_len"])])
    command.extend(str(arg) for arg in service_cfg.get("extra_args", []))
    return command


def embedding_command(cfg: dict[str, Any]) -> list[str]:
    host, port = endpoint_host_port(cfg["base_url"])
    service_cfg = cfg.get("service", {})
    return [
        sys.executable,
        "rag/embed_server.py",
        "--model-path",
        cfg["model_name_or_path"],
        "--host",
        host,
        "--port",
        str(port),
        "--max-seq-length",
        str(service_cfg.get("max_seq_length", 16384)),
    ]


def command_for(name: str, cfg: dict[str, Any]) -> list[str]:
    if name == "embedding":
        return embedding_command(cfg)
    if name in CHAT_MODELS:
        return vllm_command(name, cfg)
    raise ValueError(f"Unknown service: {name}")


def mock_command(name: str, cfg: dict[str, Any]) -> list[str]:
    host, port = endpoint_host_port(cfg["base_url"])
    command = [
        sys.executable,
        "mock_openai_server.py",
        "--role",
        name,
        "--host",
        host,
        "--port",
        str(port),
    ]
    service_cfg = cfg.get("service", {})
    if name == "embedding" and service_cfg.get("embedding_dim") is not None:
        command.extend(["--embedding-dim", str(service_cfg["embedding_dim"])])
    return command


def parse_models(value: str) -> list[str]:
    if value == "all":
        return ALL_MODELS
    models = [item.strip() for item in value.split(",") if item.strip()]
    invalid = [item for item in models if item not in ALL_MODELS]
    if invalid:
        raise ValueError(f"Unknown model service(s): {', '.join(invalid)}")
    return models


def start_services(
    config: dict[str, Any],
    models: list[str],
    service_dir: Path,
    dry_run: bool,
    mock: bool = False,
) -> list[subprocess.Popen]:
    log_dir = service_dir / "logs"
    pid_dir = service_dir / "pids"
    log_dir.mkdir(parents=True, exist_ok=True)
    pid_dir.mkdir(parents=True, exist_ok=True)

    processes = []
    for name in models:
        cfg = config["models"][name]
        command = mock_command(name, cfg) if mock else command_for(name, cfg)
        env = os.environ.copy()
        env["NO_PROXY"] = ",".join(
            filter(None, [env.get("NO_PROXY", ""), "127.0.0.1", "localhost", "0.0.0.0"])
        )
        env["no_proxy"] = ",".join(
            filter(None, [env.get("no_proxy", ""), "127.0.0.1", "localhost", "0.0.0.0"])
        )
        service_cfg = cfg.get("service", {})
        if service_cfg.get("cuda_visible_devices") is not None:
            env["CUDA_VISIBLE_DEVICES"] = str(service_cfg["cuda_visible_devices"])

        print(f"[{name}] {' '.join(command)}")
        if dry_run:
            continue

        log_path = log_dir / f"{name}.log"
        log_file = open(log_path, "a")
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
        processes.append(process)
        (pid_dir / f"{name}.pid").write_text(str(process.pid))
        print(f"[{name}] pid={process.pid} log={log_path}")

    return processes


def stop_services(service_dir: Path, models: list[str]) -> None:
    pid_dir = service_dir / "pids"
    for name in models:
        pid_path = pid_dir / f"{name}.pid"
        if not pid_path.exists():
            print(f"[{name}] no pid file")
            continue
        pid = int(pid_path.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[{name}] stopped pid={pid}")
        except ProcessLookupError:
            print(f"[{name}] pid not running: {pid}")
        pid_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start or stop CICO OpenAI-compatible model services.")
    parser.add_argument("--config", default="configs/cico_pipeline.yaml")
    parser.add_argument("--models", default="all", help="Comma-separated subset: embedding,splitter,planner,generator")
    parser.add_argument("--service-dir", default=".cico_services")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without starting services.")
    parser.add_argument("--mock", action="store_true", help="Start lightweight mock services instead of real model services.")
    parser.add_argument("--stop", action="store_true", help="Stop services recorded under --service-dir.")
    parser.add_argument("--wait", action="store_true", help="Keep this process attached after starting services.")
    args = parser.parse_args()

    models = parse_models(args.models)
    service_dir = Path(args.service_dir)
    if args.stop:
        stop_services(service_dir, models)
        return

    config = load_config(args.config)
    processes = start_services(config, models, service_dir, args.dry_run, args.mock)
    if args.wait and processes:
        try:
            while all(process.poll() is None for process in processes):
                time.sleep(2)
        except KeyboardInterrupt:
            for process in processes:
                process.terminate()


if __name__ == "__main__":
    main()
