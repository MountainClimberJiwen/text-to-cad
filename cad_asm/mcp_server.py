#!/usr/bin/env python3
"""
cad-asm MCP Server — Expose cad-asm tools via Model Context Protocol (stdio).

Any MCP-compatible client (Claude Code, Cursor, Windsurf, Hermes via mcporter)
can discover and call these tools without knowing internal CLI details.

Usage:
    python -m cad_asm.mcp_server

The server reads JSON-RPC messages from stdin and writes responses to stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cad_asm.agent_interface import AgentInterface


api = AgentInterface()


def _send(response: dict) -> None:
    payload = json.dumps(response)
    print(payload, flush=True)


def handle_list_tools() -> dict:
    return {
        "tools": [
            {
                "name": "cad_asm_init",
                "description": "Initialize an assembly workspace from a task JSON",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "object", "description": "AssemblyTask dict"},
                        "workspace": {"type": "string", "description": "Workspace directory path"},
                    },
                    "required": ["task", "workspace"],
                },
            },
            {
                "name": "cad_asm_run",
                "description": "Auto-run assembly loop until complete, error, or review gate",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "auto": {"type": "boolean", "default": False},
                        "max_iterations": {"type": "integer", "default": 100},
                    },
                    "required": ["workspace"],
                },
            },
            {
                "name": "cad_asm_step",
                "description": "Execute a single assembly step",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "continue": {"type": "boolean", "default": False},
                    },
                    "required": ["workspace"],
                },
            },
            {
                "name": "cad_asm_status",
                "description": "Read current workspace state and pending review",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                    },
                    "required": ["workspace"],
                },
            },
            {
                "name": "cad_asm_decide",
                "description": "Submit a review decision (approve, reject, modify)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "decision": {"type": "string", "enum": ["approve", "reject", "modify"]},
                        "reason": {"type": "string"},
                        "modified_transform": {"type": "object"},
                    },
                    "required": ["workspace", "decision"],
                },
            },
            {
                "name": "cad_asm_export",
                "description": "Export final assembly to STEP/STL/URDF",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "format": {"type": "string", "enum": ["step", "stl", "urdf"], "default": "step"},
                    },
                    "required": ["workspace"],
                },
            },
        ],
    }


def handle_call_tool(name: str, args: dict) -> dict:
    try:
        if name == "cad_asm_init":
            ws = api.init_task(args["task"], args["workspace"])
            return {"content": [{"type": "text", "text": f"Workspace initialized: {ws}"}]}

        if name == "cad_asm_run":
            result = api.run(args["workspace"], auto=args.get("auto", False), max_iterations=args.get("max_iterations", 100))
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]}

        if name == "cad_asm_step":
            result = api.step(args["workspace"], continue_=args.get("continue", False))
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]}

        if name == "cad_asm_status":
            result = api.status(args["workspace"])
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]}

        if name == "cad_asm_decide":
            api.decide(
                args["workspace"],
                args["decision"],
                args.get("reason", ""),
                args.get("modified_transform"),
            )
            return {"content": [{"type": "text", "text": "Decision recorded."}]}

        if name == "cad_asm_export":
            path = api.export(args["workspace"], args.get("format", "step"))
            return {"content": [{"type": "text", "text": f"Exported: {path}" if path else "Export failed"}]}

        return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": f"Error: {e}"}]}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method = msg.get("method")
        req_id = msg.get("id")

        if method == "initialize":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "cad-asm", "version": "0.1.0"}}})
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": req_id, "result": handle_list_tools()})
        elif method == "tools/call":
            params = msg.get("params", {})
            result = handle_call_tool(params.get("name"), params.get("arguments", {}))
            _send({"jsonrpc": "2.0", "id": req_id, "result": result})
        elif method == "notifications/initialized":
            pass
        else:
            _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})


if __name__ == "__main__":
    main()
