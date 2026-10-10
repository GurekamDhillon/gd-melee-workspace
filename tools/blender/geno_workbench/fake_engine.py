"""Synthetic engine-space fighter and localhost workbench MCP server.

All geometry is authored here from constants. Rotations use degrees and
right-handed matrices. Facing is a root rotation, never a reflection.

Source, built, and loaded hitboxes are separate snapshots: edits affect
list_hitboxes immediately, while frame_info changes after rebuild and reload.
"""

from __future__ import annotations

import copy
import json
import math
import socket
import socketserver
import threading
from typing import Callable

if __package__:
    from .wbspace import Mat4, mat4_from_12, mul
else:
    from wbspace import Mat4, mat4_from_12, mul


_JOINT_NAMES = (
    "TopN",
    "b_C_Base",
    "b_C_Pelvis",
    "b_C_Spine1",
    "b_C_Chest",
    "b_C_Head",
    "b_R_Arm1",
    "b_R_Arm2",
    "b_R_Hand",
)
_PARENTS = (-1, 0, 1, 2, 3, 4, 4, 6, 7)
_OFFSETS = (
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 5.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 1.5, 0.0),
    (0.0, 2.0, 0.0),
    (-1.5, 0.0, 0.0),
    (-1.8, 0.0, 0.0),
    (-1.8, 0.0, 0.0),
)
_ROLE_JOINT = {
    "TOP": 0,
    "ROOT": 1,
    "HIP": 2,
    "SPINE": 3,
    "CHEST": 4,
    "HEAD": 5,
    "ARM_R": 6,
    "FOREARM_R": 7,
    "HAND_R": 8,
}
_CLIPS = {"wait": "Wait", "jab": "Attack11", "dair": "AttackAirLw"}
ROW_FRAMES = {"wait": 40, "jab": 30, "dair": 39}
_TOOLS = (
    "engine_status",
    "engine_restart",
    "list_rows",
    "load_row",
    "set_frame",
    "play",
    "frame_info",
    "list_hitboxes",
    "run_checks",
    "suggest_hitbox_bone",
    "edit_hitbox",
    "list_attributes",
    "edit_attribute",
    "rebuild",
    "reload",
)
_CLOSE = object()
_MAX_REQUEST_BYTES = 4 * 1024 * 1024


def synthetic_plan() -> dict:
    return {
        "joints": [
            {
                "index": index,
                "name": name,
                "parent": _PARENTS[index],
                "synth": index == 0,
            }
            for index, name in enumerate(_JOINT_NAMES)
        ],
        "roles": {
            role: _JOINT_NAMES[index] for role, index in _ROLE_JOINT.items()
        },
        "role_joint": dict(_ROLE_JOINT),
        "scale": 1.0,
    }


def _translation(x: float, y: float, z: float) -> Mat4:
    return mat4_from_12(
        (1.0, 0.0, 0.0, x, 0.0, 1.0, 0.0, y, 0.0, 0.0, 1.0, z)
    )


def _ry(degrees: float) -> Mat4:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return mat4_from_12(
        (c, 0.0, s, 0.0, 0.0, 1.0, 0.0, 0.0, -s, 0.0, c, 0.0)
    )


def _rz(degrees: float) -> Mat4:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return mat4_from_12(
        (c, -s, 0.0, 0.0, s, c, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    )


def _fk(plan: dict, local: dict[int, Mat4], root: Mat4) -> dict[int, Mat4]:
    parents = {}
    for joint in plan["joints"]:
        index = joint["index"]
        if index in parents:
            raise ValueError("duplicate joint index")
        parents[index] = joint["parent"]
    if 0 not in parents:
        raise ValueError("synthetic plan must contain joint 0")

    world = {0: root}
    visiting = set()

    def visit(index: int) -> Mat4:
        if index in world:
            return world[index]
        if index in visiting:
            raise ValueError("joint hierarchy contains a cycle")
        if index not in parents or index not in local:
            raise ValueError(f"unknown synthetic joint {index}")
        parent = parents[index]
        if parent not in parents:
            raise ValueError(f"unknown parent for joint {index}")
        visiting.add(index)
        world[index] = mul(visit(parent), local[index])
        visiting.remove(index)
        return world[index]

    for index in parents:
        visit(index)
    return world


def rest_world(plan: dict) -> dict[int, Mat4]:
    local = {
        index: _translation(*offset) for index, offset in enumerate(_OFFSETS)
    }
    return _fk(plan, local, _translation(0.0, 0.0, 0.0))


def _integer(value: object, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _facing(value: int) -> int:
    if isinstance(value, bool) or value not in (-1, 1):
        raise ValueError("facing must be -1 or 1")
    return int(value)


def _point(x: float, y: float, z: float = 0.0) -> dict:
    return {"x": float(x), "y": float(y), "z": float(z)}


def _position(matrix: Mat4) -> dict:
    return _point(matrix[0][3], matrix[1][3], matrix[2][3])


def _matrix12(matrix: Mat4) -> list[float]:
    return [float(matrix[row][column]) for row in range(3) for column in range(4)]


def _apply(matrix: Mat4, point: dict) -> dict:
    vector = (point["x"], point["y"], point["z"])
    coordinates = [
        sum(matrix[row][column] * vector[column] for column in range(3))
        + matrix[row][3]
        for row in range(3)
    ]
    return _point(*coordinates)


def _source_attributes() -> list[dict]:
    # Invented values; metadata follows the public Geno numeric schema.
    fields = (
        ("weight", 73.25, "number", "misc", "weight", "Fighter weight", None, None),
        ("walk_max_vel", 1.25, "number", "ground", "Melee units/frame", "Maximum walk speed", None, None),
        ("gravity", 0.125, "number", "air", "Melee units/frame^2", "Gravity", None, None),
        ("initial_shield_size", 7.5, "number", "shield_ecb", "Melee units", "Initial shield size", None, None),
        ("normal_landing_lag", 6, "number", "landing", "frames", "Normal landing lag", None, None),
        ("rapid_jab_window", 4, "integer", "misc", "frames", "Rapid jab input window", None, None),
        ("jumps.max", 3, "integer", "jump", "count", "Total jumps including ground jump", 1, 250),
        ("jumps.air_vy.0", None, "number", "jump", "Melee units/frame", "Per-air-jump vertical impulse", None, None),
    )
    return [{"name": name, "value": value, "type": kind, "group": group,
             "unit": unit, "description": description,
             "range": {"minimum": low, "maximum": high},
             "source_file": "gameplay.json" if value is not None else "", "write_file": "gameplay.json"}
            for name, value, kind, group, unit, description, low, high in fields]


def _source_hitboxes() -> dict:
    def record(row: str) -> dict:
        return {
            "ordinal": 0,
            "line": 1,
            "slot": 0,
            "joint": "HAND_R",
            "damage": 3.0 if row == "jab" else 8.0,
            "size": 2.8,
            "x": 0.0,
            "y": 0.0,
            "z": 1.0,
            "angle": 361 if row == "jab" else 270,
            "kbg": 100,
            "fkb": 0,
            "bkb": 20,
            "start_frame": 5,
            "end_frame": 8,
        }

    return {"wait": [], "jab": [record("jab")], "dair": [record("dair")]}


def _active_hitboxes(
    matrices: dict[int, Mat4],
    records: list[dict],
    frame: int,
) -> list[dict]:
    hits = []
    for record in records:
        if not record["start_frame"] <= frame <= record["end_frame"]:
            continue
        joint = _ROLE_JOINT[record["joint"]]
        offset = _point(record["x"], record["y"], record["z"])
        hits.append(
            {
                "ordinal": record["ordinal"],
                "slot": record["slot"],
                "joint": joint,
                "active": True,
                "offset": offset,
                "world": _apply(matrices[joint], offset),
                "radius": record["size"],
                "damage": record["damage"],
                "start_frame": record["start_frame"],
                "end_frame": record["end_frame"],
            }
        )
    return hits


def synthetic_provider(
    row: str,
    frame: int,
    facing: int = 1,
    root_x: float = 0.0,
) -> dict:
    if row not in _CLIPS:
        raise ValueError(f"unknown row: {row}")
    frame = _integer(frame, "frame", 1)
    facing = _facing(facing)
    root_x = float(root_x)
    if not math.isfinite(root_x):
        raise ValueError("root_x must be finite")

    plan = synthetic_plan()
    local = {
        index: _translation(*offset) for index, offset in enumerate(_OFFSETS)
    }
    t = frame - 1
    local[3] = mul(local[3], _ry(1.0 * t))
    local[6] = mul(local[6], _rz(4.0 * t))
    local[7] = mul(local[7], _rz(2.0 * t))
    root = mul(_translation(root_x, 0.0, 0.0), _ry(90.0 * facing))
    matrices = _fk(plan, local, root)

    bones = [
        {
            "joint": joint["index"],
            "parent": joint["parent"],
            "name": joint["name"],
            "pos": _position(matrices[joint["index"]]),
            "mtx": _matrix12(matrices[joint["index"]]),
        }
        for joint in plan["joints"]
    ]
    pairs = ((4, 5), (4, 6), (6, 7), (7, 8), (2, 4))
    hurtboxes = [
        {
            "joint_a": a,
            "joint_b": b,
            "a": _position(matrices[a]),
            "b": _position(matrices[b]),
            "radius": 1.0,
        }
        for a, b in pairs
    ]

    return {
        "schema": 2,
        "row": row,
        "clip": _CLIPS[row],
        "frame": frame,
        "facing": facing,
        "bones": bones,
        "root": {
            "joint": 0,
            "mtx": _matrix12(root),
            "pos": _position(root),
            "facing": facing,
        },
        "hitboxes": _active_hitboxes(matrices, _source_hitboxes()[row], frame),
        "hurtboxes": hurtboxes,
        "ecb": {
            "bottom": _point(root_x, 0.0),
            "top": _point(root_x, 9.0),
            "left": _point(root_x - 3.0, 4.5),
            "right": _point(root_x + 3.0, 4.5),
        },
        "floorY": 0.0,
        "lowestY": min(matrix[1][3] for matrix in matrices.values()),
    }


def _rpc_error(request_id: object, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _rpc_result(request_id: object, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _tool_result(body: dict, is_error: bool = False) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    body, separators=(",", ":"), allow_nan=False
                ),
            }
        ],
        "isError": is_error,
    }


class _Handler(socketserver.StreamRequestHandler):
    def setup(self) -> None:
        super().setup()
        owner = self.server.workbench
        with owner._connections_lock:
            owner._connections.add(self.request)

    def handle(self) -> None:
        owner = self.server.workbench
        try:
            while not owner._stopping.is_set():
                raw = self.rfile.readline(_MAX_REQUEST_BYTES + 1)
                if not raw:
                    return
                if len(raw) > _MAX_REQUEST_BYTES:
                    response = _rpc_error(None, -32600, "request exceeds the size limit")
                    self._send(response)
                    return
                if not raw.strip():
                    continue
                try:
                    request = json.loads(raw)
                except ValueError:
                    self._send(_rpc_error(None, -32700, "invalid JSON"))
                    continue

                response = owner._rpc(request)
                if response is _CLOSE:
                    return
                if response is not None:
                    self._send(response)
        except OSError:
            return

    def _send(self, response: dict) -> None:
        wire = (
            json.dumps(response, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
        self.wfile.write(wire)
        self.wfile.flush()

    def finish(self) -> None:
        try:
            super().finish()
        except OSError:
            pass
        finally:
            owner = self.server.workbench
            with owner._connections_lock:
                owner._connections.discard(self.request)


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False

    def __init__(self, address: tuple[str, int], owner: FakeWorkbench):
        self.workbench = owner
        super().__init__(address, _Handler)


class FakeWorkbench:
    """Persistent synthetic session shared by its connected MCP clients.

    drop_after counts tool calls since construction. A value of N permits
    N calls and drops the next one before dispatch. Handshake and tools/list
    messages do not count. Received calls, including dropped calls, are logged.
    """

    def __init__(
        self,
        provider: Callable = synthetic_provider,
        host: str = "127.0.0.1",
        port: int = 0,
    ):
        if host not in ("127.0.0.1", "localhost"):
            raise ValueError("fake workbench must bind to IPv4 localhost")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("port must be an integer between 0 and 65535")

        self.provider = provider
        self.host = "127.0.0.1"
        self.port = port
        self._bind_port = port
        self.calls: list[tuple[str, dict]] = []
        self.stale = False
        self.fail_next: str | None = None
        self.build_mode: str = "full"
        self.rebuild_unconfigured = False   # a project with no build: rebuild answers "rebuild not configured"
        self.label_rows_by_clip = False
        self.bare_load_row = False
        self.checks_unload = False   # run_checks fails the way the real one did: row dropped, then frame 0 asked for
        self.drop_after: int | None = None
        self.current_row = "wait"
        self.frame = 1
        self.facing = 1
        self.root_x = 0.0

        self.attribute_proposals = False
        self._attributes = _source_attributes()
        self.built_attributes = {item["name"]: item["value"] for item in self._attributes}
        self.loaded_attributes = dict(self.built_attributes)
        self._source = _source_hitboxes()
        self._built = copy.deepcopy(self._source)
        self._loaded = copy.deepcopy(self._source)
        self._state_lock = threading.RLock()
        self._connections_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._connections: set[socket.socket] = set()
        self._stopping = threading.Event()
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> int:
        with self._lifecycle_lock:
            if self._server is not None:
                return self.port
            server = _Server((self.host, self._bind_port), self)
            self._stopping.clear()
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                name="geno-fake-workbench",
                daemon=True,
            )
            self._server = server
            self._thread = thread
            self.port = server.server_address[1]
            try:
                thread.start()
            except BaseException:
                self._server = None
                self._thread = None
                server.server_close()
                raise
            return self.port

    def stop(self) -> None:
        with self._lifecycle_lock:
            server = self._server
            if server is None:
                return
            self._stopping.set()
            server.shutdown()

            with self._connections_lock:
                connections = list(self._connections)
            for connection in connections:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    connection.close()
                except OSError:
                    pass

            server.server_close()
            if self._thread is not None:
                self._thread.join(timeout=1.0)
            self._server = None
            self._thread = None

    def set_facing(self, facing: int) -> None:
        value = _facing(facing)
        with self._state_lock:
            self.facing = value

    def _row_arg(self, args: dict) -> str:
        row = args.get("row", self.current_row)
        if not isinstance(row, str) or row not in _CLIPS:
            raise ValueError(f"unknown row: {row}")
        return row

    def _frame_info(self) -> dict:
        info = self.provider(
            self.current_row,
            self.frame,
            facing=self.facing,
            root_x=self.root_x,
        )
        if self.provider is synthetic_provider:
            matrices = {
                bone["joint"]: mat4_from_12(bone["mtx"])
                for bone in info["bones"]
            }
            info["hitboxes"] = _active_hitboxes(
                matrices, self._loaded[self.current_row], self.frame
            )
        if self.label_rows_by_clip:
            # The real engine labels the loaded move with its clip ("AttackAirLw"), not the row name ("dair").
            info["row"] = info["clip"]
        return info

    def _edit_hitbox(self, args: dict) -> dict:
        row = self._row_arg(args)
        ordinal = _integer(args.get("ordinal", 0), "ordinal")
        records = self._source[row]
        position = next(
            (i for i, record in enumerate(records) if record["ordinal"] == ordinal),
            None,
        )
        if position is None:
            raise ValueError(f"no hitbox ordinal {ordinal} in row {row}")

        record = records[position]
        editable = set(record) - {"ordinal", "line"}
        changes = args.get("changes")
        if changes is None:
            changes = {key: value for key, value in args.items() if key in editable}
        if not isinstance(changes, dict):
            raise ValueError("changes must be a dictionary")
        changes = dict(changes)
        if "field" in args:
            changes[args["field"]] = args.get("value")
        if set(changes) - editable:
            raise ValueError("unknown hitbox field")

        updated = dict(record)
        updated.update(changes)
        if updated["joint"] not in _ROLE_JOINT:
            raise ValueError("joint must name a role in the synthetic plan")
        for key in ("slot", "kbg", "fkb", "bkb"):
            updated[key] = _integer(updated[key], key)
        for key in ("start_frame", "end_frame"):
            updated[key] = _integer(updated[key], key, 1)
        if updated["end_frame"] < updated["start_frame"]:
            raise ValueError("end_frame must not precede start_frame")
        for key in ("damage", "size", "x", "y", "z", "angle"):
            updated[key] = float(updated[key])
            if not math.isfinite(updated[key]):
                raise ValueError(f"{key} must be finite")
        if updated["size"] < 0 or updated["damage"] < 0:
            raise ValueError("size and damage must not be negative")

        records[position] = updated
        self.stale = True
        return {"changed": True}

    def _edit_attribute(self, args: dict) -> dict:
        name = args.get("name")
        item = next((row for row in self._attributes if row["name"] == name), None)
        if item is None:
            raise ValueError(f"unknown fighter attribute: {name}")
        value = args.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if item["type"] == "integer" and int(value) != value:
            raise ValueError(f"{name} must be an integer")
        bounds = item["range"]
        if ((bounds["minimum"] is not None and value < bounds["minimum"])
                or (bounds["maximum"] is not None and value > bounds["maximum"])):
            raise ValueError(f"{name} is outside its schema range")
        if item["value"] == value:
            return {"applied": False, "note": "no change"}
        if self.attribute_proposals or args.get("propose"):
            return {"proposed": True, "entry": 1}
        was_unset = item["value"] is None
        item["value"] = value
        item["source_file"] = "gameplay.json"
        if was_unset and name.startswith("jumps.air_vy."):
            index = int(name.rsplit(".", 1)[1])
            if index < 15:
                self._attributes.append(dict(item, name=f"jumps.air_vy.{index + 1}",
                                             value=None, source_file=""))
        self.stale = True
        return {"applied": True, "entry": 1}

    def _execute(self, tool: str, args: dict) -> dict:
        if tool == "engine_status":
            return {"status": "running"}
        if tool == "engine_restart":
            self.current_row = "wait"
            self.frame = 1
            return {"status": "running"}
        if tool == "list_rows":
            return {
                "rows": [
                    {
                        "name": row,
                        "motions": [clip],
                        "tag": row,
                        "clip": clip,
                        "aerial": row == "dair",
                        "hitboxes": len(self._source[row]),
                        "frames": ROW_FRAMES[row],
                    }
                    for row, clip in _CLIPS.items()
                ]
            }
        if tool == "load_row":
            self.current_row = self._row_arg(args)
            self.frame = 1
            if self.bare_load_row:
                return {"ok": True}  # what the real server answers
            return self._frame_info()
        if tool == "set_frame":
            if self.current_row is None:
                raise ValueError("no row loaded; call load_row first")
            wanted = _integer(args.get("frame"), "frame", 1)
            length = ROW_FRAMES.get(self.current_row)
            if length is not None and wanted > length:
                # what the real server says once the move has ended (it used to hang until a timeout)
                raise ValueError(
                    f"frame {wanted} is past the end of this move (the fighter is at frame 1 "
                    f"of action 29; last frame {length})"
                )
            self.frame = wanted
            return self._frame_info()
        if tool == "play":
            frames = _integer(args.get("frames", 1), "frames")
            step = _integer(args.get("step", 1), "step", 1)
            self.frame += frames * step
            return self._frame_info()
        if tool == "frame_info":
            return self._frame_info()
        if tool == "list_hitboxes":
            return {"hitboxes": copy.deepcopy(self._source[self._row_arg(args)])}
        if tool == "list_attributes":
            return {"attributes": copy.deepcopy(self._attributes)}
        if tool == "edit_attribute":
            return self._edit_attribute(args)
        if tool == "run_checks":
            if self.checks_unload:
                self.current_row = None
                raise ValueError("frame 0 is past the end of this move (the fighter is at frame 1 of action 219)")
            return {
                "problems": [
                    {
                        "kind": "wrong_limb",
                        "row": "jab",
                        "message": "jab hitbox 0 is on FOOT_R; expected HAND_R",
                        "ordinal": 0,
                    }
                ],
                "engine": True,
            }
        if tool == "suggest_hitbox_bone":
            return {"suggested": "HAND_R", "current": "FOOT_R", "scores": []}
        if tool == "edit_hitbox":
            return self._edit_hitbox(args)
        if tool == "rebuild":
            if self.rebuild_unconfigured:
                raise ValueError("rebuild not configured")
            self._built = copy.deepcopy(self._source)
            self.built_attributes = {item["name"]: item["value"] for item in self._attributes}
            self.stale = False
            return {"rebuilt": True, "mode": self.build_mode, "build_seconds": 1.5}
        if tool == "reload":
            self._loaded = copy.deepcopy(self._built)
            self.loaded_attributes = dict(self.built_attributes)
            self.stale = False
            return {"reloaded": True}
        raise ValueError(f"unknown tool: {tool}")

    def _rpc(self, request: object) -> object:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return _rpc_error(None, -32600, "invalid JSON-RPC request")
        if "id" not in request:
            return None

        request_id = request["id"]
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(method, str) or not isinstance(params, dict):
            return _rpc_error(request_id, -32600, "invalid method or parameters")
        if method == "initialize":
            return _rpc_result(
                request_id,
                {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "geno_fake_workbench", "version": "0.1.0"},
                },
            )
        if method == "tools/list":
            return _rpc_result(
                request_id,
                {
                    "tools": [
                        {
                            "name": name,
                            "description": f"Synthetic workbench tool: {name}",
                            "inputSchema": {"type": "object", "properties": {}},
                        }
                        for name in _TOOLS
                    ]
                },
            )
        if method != "tools/call":
            return _rpc_error(request_id, -32601, f"unknown method: {method}")

        tool = params.get("name")
        args = params.get("arguments", {})
        if not isinstance(tool, str) or not isinstance(args, dict):
            return _rpc_error(request_id, -32602, "invalid tool name or arguments")

        with self._state_lock:
            previous_count = len(self.calls)
            self.calls.append((tool, copy.deepcopy(args)))
            if self.drop_after is not None and previous_count >= self.drop_after:
                return _CLOSE
            if self.fail_next is not None:
                message = str(self.fail_next)
                self.fail_next = None
                return _rpc_result(
                    request_id, _tool_result({"error": message}, True)
                )
            if tool not in _TOOLS:
                return _rpc_error(request_id, -32602, f"unknown tool: {tool}")
            try:
                result = _tool_result(self._execute(tool, args))
            except Exception as exc:
                result = _tool_result(
                    {"error": str(exc) or type(exc).__name__}, True
                )
            return _rpc_result(request_id, result)
