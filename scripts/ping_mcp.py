#!/usr/bin/env python3
"""
MCP Health & Active Ping Utility (THLawDeka)
ทดสอบการเชื่อมต่อ (Active Probe) ของ Legal MCP Servers:
1. fourcorners-tlex (HTTP JSON-RPC Ping)
2. slegaltools-legal-v2 (Stdio FastMCP Handshake)
3. thai-legal (HTTP Stream/SSE Probe)
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".agents", "mcp_config.json"
)

def ping_http_jsonrpc(
    name: str,
    url: str,
    headers: Dict[str, str],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """ส่งคำขอ JSON-RPC Ping ไปยัง HTTP MCP Server"""
    t0 = time.time()
    req_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) THLawDeka-MCP-Ping/1.0"
    }
    if headers:
        req_headers.update(headers)

    ping_payload = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1}).encode("utf-8")
    req = urllib.request.Request(url, data=ping_payload, headers=req_headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = round((time.time() - t0) * 1000, 1)
            raw = response.read().decode("utf-8", errors="replace")
            try:
                res_json = json.loads(raw)
                if "result" in res_json or res_json.get("jsonrpc") == "2.0":
                    return {
                        "name": name,
                        "type": "http",
                        "endpoint": url,
                        "status": "ONLINE",
                        "latency_ms": latency_ms,
                        "details": "JSON-RPC 2.0 Ping OK"
                    }
            except json.JSONDecodeError:
                pass

            return {
                "name": name,
                "type": "http",
                "endpoint": url,
                "status": "ONLINE",
                "latency_ms": latency_ms,
                "details": f"HTTP {response.status} OK"
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - t0) * 1000, 1)
        if e.code in (400, 405, 406):
            return {
                "name": name,
                "type": "http",
                "endpoint": url,
                "status": "ONLINE",
                "latency_ms": latency_ms,
                "details": f"Responsive (HTTP {e.code})"
            }
        return {
            "name": name,
            "type": "http",
            "endpoint": url,
            "status": "DEGRADED",
            "latency_ms": latency_ms,
            "details": f"HTTP {e.code}: {e.reason}"
        }
    except Exception as e:
        latency_ms = round((time.time() - t0) * 1000, 1)
        return {
            "name": name,
            "type": "http",
            "endpoint": url,
            "status": "OFFLINE",
            "latency_ms": latency_ms,
            "details": f"Connection Error: {str(e)}"
        }

def ping_http_stream(
    name: str,
    url: str,
    headers: Dict[str, str],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """ทดสอบการเชื่อมต่อ HTTP SSE / Stream MCP Server"""
    t0 = time.time()
    req_headers = {
        "Accept": "text/event-stream, application/json",
        "User-Agent": "THLawDeka-MCP-Ping/1.0"
    }
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = round((time.time() - t0) * 1000, 1)
            return {
                "name": name,
                "type": "http-sse",
                "endpoint": url,
                "status": "ONLINE",
                "latency_ms": latency_ms,
                "details": f"HTTP {response.status} Stream OK"
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - t0) * 1000, 1)
        if e.code in (200, 400, 405, 406):
            return {
                "name": name,
                "type": "http-sse",
                "endpoint": url,
                "status": "ONLINE",
                "latency_ms": latency_ms,
                "details": f"Responsive (HTTP {e.code})"
            }
        return {
            "name": name,
            "type": "http-sse",
            "endpoint": url,
            "status": "DEGRADED",
            "latency_ms": latency_ms,
            "details": f"HTTP {e.code}: {e.reason}"
        }
    except Exception as e:
        latency_ms = round((time.time() - t0) * 1000, 1)
        return {
            "name": name,
            "type": "http-sse",
            "endpoint": url,
            "status": "OFFLINE",
            "latency_ms": latency_ms,
            "details": f"Connection Error: {str(e)}"
        }

def ping_stdio_process(
    name: str,
    command: str,
    args: List[str],
    env: Dict[str, str],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """ทดสอบ Handshake กับ Stdio MCP Process"""
    t0 = time.time()
    if not os.path.exists(command):
        return {
            "name": name,
            "type": "stdio",
            "endpoint": command,
            "status": "OFFLINE",
            "latency_ms": 0.0,
            "details": f"Executable not found: {command}"
        }

    cmd = [command] + (args or [])
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            text=True
        )

        init_msg = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-ping", "version": "1.0"}
            },
            "id": 1
        }
        p.stdin.write(json.dumps(init_msg) + "\n")
        p.stdin.flush()

        response_line = p.stdout.readline()
        try:
            if p.stdin:
                p.stdin.close()
            if p.stdout:
                p.stdout.close()
            if p.stderr:
                p.stderr.close()
            p.terminate()
            p.wait(timeout=1.0)
        except (subprocess.TimeoutExpired, Exception):
            p.kill()

        latency_ms = round((time.time() - t0) * 1000, 1)
        if response_line:
            res_json = json.loads(response_line.strip())
            if "result" in res_json:
                return {
                    "name": name,
                    "type": "stdio",
                    "endpoint": f"{os.path.basename(command)} -> {os.path.basename(args[0]) if args else ''}",
                    "status": "ONLINE",
                    "latency_ms": latency_ms,
                    "details": "MCP Handshake OK"
                }

        return {
            "name": name,
            "type": "stdio",
            "endpoint": command,
            "status": "DEGRADED",
            "latency_ms": latency_ms,
            "details": "Process started but empty handshake response"
        }
    except Exception as e:
        latency_ms = round((time.time() - t0) * 1000, 1)
        return {
            "name": name,
            "type": "stdio",
            "endpoint": command,
            "status": "OFFLINE",
            "latency_ms": latency_ms,
            "details": f"Process Error: {str(e)}"
        }

def ping_all_mcp_servers(config_path: Optional[str] = None, timeout: float = 5.0) -> List[Dict[str, Any]]:
    """ตรวจสอบสถานะของทุก MCP Server ใน mcp_config.json"""
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"MCP Config file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    servers = config.get("mcpServers", {})
    results = []

    for name, srv in servers.items():
        srv_type = srv.get("type", "")
        if "command" in srv:
            res = ping_stdio_process(
                name=name,
                command=srv["command"],
                args=srv.get("args", []),
                env=srv.get("env", {}),
                timeout=timeout
            )
        elif name == "fourcorners-tlex" or srv_type == "http":
            res = ping_http_jsonrpc(
                name=name,
                url=srv.get("url", ""),
                headers=srv.get("headers", {}),
                timeout=timeout
            )
        else:
            res = ping_http_stream(
                name=name,
                url=srv.get("url", ""),
                headers=srv.get("headers", {}),
                timeout=timeout
            )
        results.append(res)

    return results

def format_terminal_table(results: List[Dict[str, Any]]) -> str:
    """จัดรูปแบบตารางสรุปผล Ping ที่สวยงามบน Terminal"""
    lines = []
    lines.append("\n=== THLawDeka MCP Servers Active Ping Health Card ===")
    header = f"{'Server Name':<22} | {'Type':<10} | {'Status':<12} | {'Latency':<10} | {'Details'}"
    lines.append(header)
    lines.append("-" * len(header) + "-" * 20)

    all_online = True
    for r in results:
        status_str = r["status"]
        if status_str == "ONLINE":
            status_icon = "🟢 ONLINE"
        elif status_str == "DEGRADED":
            status_icon = "🟡 DEGRADED"
            all_online = False
        else:
            status_icon = "🔴 OFFLINE"
            all_online = False

        latency_str = f"{r['latency_ms']} ms"
        lines.append(
            f"{r['name']:<22} | {r['type']:<10} | {status_icon:<12} | {latency_str:<10} | {r['details']}"
        )

    lines.append("-" * len(header) + "-" * 20)
    summary = f"Overall Status: {'All Servers Healthy' if all_online else 'Some Servers Degraded/Offline'}"
    lines.append(summary + "\n")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="THLawDeka Legal MCP Servers Active Health Check CLI")
    parser.add_argument("--config", help="Path to mcp_config.json")
    parser.add_argument("--timeout", type=float, default=5.0, help="Probe timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    try:
        results = ping_all_mcp_servers(config_path=args.config, timeout=args.timeout)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(format_terminal_table(results))

        has_offline = any(r["status"] == "OFFLINE" for r in results)
        sys.exit(1 if has_offline else 0)
    except Exception as e:
        print(f"Error during MCP ping: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
