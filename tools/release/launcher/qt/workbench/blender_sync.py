"""Qt Workbench -> Blender view follower, loaded through GW_WB_DRIVER.

bootstrap.py runs this file with runpy.run_path after loading/calibrating the
fighter. Only the polling thread owns its independent, short-timeout McpClient;
only the Blender timer touches the add-on session or bpy. ui_view_state returns
the complete engine reply already obtained by the Qt window. This driver never
sends load_row, set_frame, rebuild, or other engine commands.

An ACK is the revision currently displayed successfully, not merely received.
A local Blender gesture clears it and consumes the outstanding Qt revision so
that the old request cannot fight scrubbing/playback. A new Qt revision resumes
following. An explicit available:false tombstone invalidates an older Qt view
without posing or changing the Blender session. Importing this module does not
install the Blender timer.
"""

from __future__ import annotations

import os
import threading


POLL_INTERVAL = 0.10
SOCKET_TIMEOUT = 0.35
_DRIVER_KEY = "geno_workbench_qt_view_sync"

# Worker::call (English/Spanish) and McpServer::handle overlap replies.
# McpClient flattens both tool errors and JSON-RPC errors into WbError text;
# no structured error code survives to distinguish these transient failures.
_OVERLAP_ERRORS = frozenset((
    "a command is already in progress",
    "ya hay un comando en curso",
    "a tool call is already in progress",
))


class FrameFollower:
    """Main-thread adapter, usable with the real WbSession without Blender."""

    def __init__(self, session):
        self.session = session
        self.revision = 0
        self._handled_revision = 0
        self._discard_next = False
        self._signature = self._view_signature()

    def _view_signature(self):
        session = self.session
        return (id(session.info), session.source_row, session.row, session.frame,
                session.cache.generation, id(session.last_rebuild), session.stale)

    def observe(self, *, busy=False, ready=True):
        """Withdraw the ACK as soon as Blender-local work replaces the view."""
        signature = self._view_signature()
        if signature != self._signature or busy or self.session.pending_frame is not None:
            self.revision = 0
            self._discard_next = True
        self._signature = signature
        if not self.session.connected or not ready:
            self.revision = 0

    def consume(self, reply, *, busy=False, ready=True):
        """Apply one new snapshot, or defer without acknowledging it.

        busy means a Blender user owns the view (scrub/play/calibration/rebuild).
        ready means a registered, calibrated viewport hook can show the frame.
        Cache cancellation is nonblocking; reset is safe only after it exits.
        """
        from geno_workbench import travel, wbspace

        session = self.session
        self.observe(busy=busy, ready=ready)
        if not session.connected:
            return False
        if not isinstance(reply, dict):
            raise ValueError("ui_view_state result must be an object")
        revision = session._integer(reply.get("revision"), "revision")
        if reply.get("available") is False:
            # Remote engine work or a Qt reset superseded its cached snapshot.
            # Tombstones deliberately have no row/info; consume their revision
            # before parsing a frame so an older deferred reply cannot replay.
            if revision >= self._handled_revision:
                self.revision = 0
                self._handled_revision = revision
                self._discard_next = False
            return False
        if self._discard_next:
            self._handled_revision = max(self._handled_revision, revision)
            self._discard_next = False
            return False
        if revision == 0 or revision <= self._handled_revision:
            return False
        if not ready:
            return False

        # Validate everything before replacing the last successfully received
        # state. _read_frame alone validates row/frame; posing also needs schema
        # 2 and finite 3x4 bone/root matrices.
        row = session._row_name(reply.get("row"))
        info = reply.get("info")
        if not isinstance(info, dict):
            raise ValueError("ui_view_state info must be an object")
        parsed = session._read_frame(info, row)
        if not wbspace.bone_matrices(parsed[0]):
            raise ValueError("ui_view_state info contains no bone matrices")
        wbspace.root_matrix(parsed[0])
        hitboxes = session.source_boxes(session._items(reply, "hitboxes"))
        anchor = session.travel_anchor
        if row != session.source_row or anchor is None:
            # A frame-1 snapshot supplies the normal row origin. If Qt first
            # shows a later frame, use that first received origin; never reuse
            # another row's origin or seek the engine to manufacture one.
            anchor = travel.anchor_of(parsed[0])

        if session.cache.loading:
            session.cache.cancel(wait=False)
            return False
        # Qt may have changed row, facing, or rebuilt since the cache was filled.
        # No old reply is safe to reuse, and prefetch must not restart here.
        session.cache.reset("qt view")
        session.loaded_row = row
        session._store_frame(parsed)
        session.travel_anchor = anchor
        session.hitboxes = hitboxes
        session.suggestion = None
        session.row_lengths.pop(row, None)
        session.last_error = ""
        self.revision = 0
        self._handled_revision = revision
        try:
            session._fire_frame()
            # The fighter hook catches its own errors into last_error; checking
            # only hook_error would claim synchronization when posing failed.
            if session.hook_error or session.last_error:
                return False
            if not session.set_status(session._frame_status()):
                return False
            self.revision = revision
            return True
        finally:
            self._signature = self._view_signature()


class ViewPoller:
    """Background mailbox; no session, bpy objects, or shared add-on socket."""

    def __init__(self, client_factory, *, pid=None, interval=POLL_INTERVAL):
        self._client_factory = client_factory
        self._pid = os.getpid() if pid is None else pid
        self._interval = interval
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._revision = 0
        self._reply = None
        self.failed = False
        self.error = ""
        self._thread = threading.Thread(target=self._run,
                                        name="geno-wb-qt-view", daemon=True)

    def start(self):
        self._thread.start()

    def acknowledge(self, revision):
        with self._lock:
            self._revision = revision

    def take(self):
        with self._lock:
            reply, self._reply = self._reply, None
        return reply

    def stop(self):
        # McpClient.close waits for its I/O lock. Never close it or join its
        # thread from a Blender timer: the worker closes its own short call.
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            connection = None
            retry = False
            try:
                connection = self._client_factory()
                connection.connect()
                while not self._stop.is_set():
                    with self._lock:
                        args = {"revision": self._revision, "pid": self._pid}
                    reply = connection.call("ui_view_state", args)
                    if not isinstance(reply, dict):
                        raise ValueError("ui_view_state result must be an object")
                    with self._lock:
                        self._reply = reply
                    if self._stop.wait(self._interval):
                        return
            except Exception as exc:
                if self._stop.is_set():
                    return
                message = str(exc).strip().casefold()
                # A GUI command can temporarily occupy the worker. Retry via
                # a new socket after timeout; a closed listener/disconnect or
                # unknown command ends this driver instead of polling forever.
                retry = (message in _OVERLAP_ERRORS or any(
                    word in message for word in ("busy", "timeout", "timed out")))
                if not retry:
                    self.error = str(exc)
                    self.failed = True
                    return
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass
            if retry and self._stop.wait(max(self._interval, 0.25)):
                return


class _BlenderDriver:
    def __init__(self, bpy, api, client, operators, operators_fighter, pose, props):
        self.bpy = bpy
        self.api = api
        self.operators = operators
        self.fighter = operators_fighter
        self.pose = pose
        self.props = props
        self.session = api.session()
        self.connection = self.session.client
        self.project = self.session.project_dir
        # Read the endpoint on the main thread, then pass only values to the
        # worker. The ordinary session socket may belong to its cache worker.
        host, port = self.connection.host, self.connection.port
        self.poller = ViewPoller(lambda: client.McpClient(
            host=host, port=port, timeout=SOCKET_TIMEOUT))
        self.follower = FrameFollower(self.session)
        self._stopped = False
        self._reported_error = ""
        self._rejected_revision = None
        self._handlers = []
        # Keep the exact callable objects used for timer/handler registration.
        self.timer = self.tick
        self.close_handler = self.stop

    def start(self):
        self.poller.start()
        for name in ("load_pre", "quit_pre"):
            handlers = getattr(self.bpy.app.handlers, name, None)
            if handlers is not None:
                handlers.append(self.close_handler)
                self._handlers.append(handlers)
        self.bpy.app.timers.register(self.timer, first_interval=0.05)

    def stop(self, *_args):
        if self._stopped:
            return
        self._stopped = True
        self.poller.stop()
        for handlers in self._handlers:
            if self.close_handler in handlers:
                handlers.remove(self.close_handler)
        self._handlers.clear()
        if self.bpy.app.timers.is_registered(self.timer):
            self.bpy.app.timers.unregister(self.timer)
        namespace = self.bpy.app.driver_namespace
        if namespace.get(_DRIVER_KEY) is self:
            namespace.pop(_DRIVER_KEY, None)

    def _busy(self, settings, windows):
        # rebuild_reload currently runs synchronously on the main thread; its
        # new info/cache generation is noticed by observe before the next tick.
        # Also yield to the fighter hook mailbox used for background results.
        return (self.session.pending_frame is not None
                or getattr(settings, "playing", False)
                or getattr(self.operators, "_active_player", None) is not None
                or self.pose.is_calibrating()
                or getattr(self.fighter, "_IN_FRAME_UPDATE", False)
                or getattr(self.fighter, "_PENDING", None) is not None
                or any(getattr(window.screen, "is_animation_playing", False)
                       for window in windows))

    def _ready(self):
        # _frame_hook intentionally does nothing while calibrating and can show
        # overlays without a rig. Neither is a successfully synchronized fighter.
        if self.fighter._frame_hook not in self.session.on_frame:
            return False
        armature = self.fighter.active_armature(self.bpy.context)
        return armature is not None and self.pose.calibration_for(armature) is not None

    def tick(self):
        try:
            return self._tick()
        except Exception as exc:
            # Deleted RNA/window objects can fail before the snapshot handler.
            # Stop the transport even when Blender is already closing its UI.
            print("GENO_WB_QT_SYNC " + str(exc))
            try:
                self.stop()
            except Exception:
                pass
            return None

    def _tick(self):
        if self._stopped:
            return None
        context = self.bpy.context
        manager = getattr(context, "window_manager", None)
        windows = getattr(manager, "windows", ())
        settings = getattr(getattr(context, "scene", None), "geno_wb", None)
        if (not windows or settings is None or not self.session.connected
                or self.api.session() is not self.session
                or self.session.client is not self.connection
                or self.session.project_dir != self.project or self.poller.failed):
            self.stop()
            return None
        busy = self._busy(settings, windows)
        ready = not busy and self._ready()
        self.follower.observe(busy=busy, ready=ready)
        self.poller.acknowledge(self.follower.revision)
        reply = self.poller.take()
        if reply is None:
            return 0.05
        try:
            if reply.get("revision") == self._rejected_revision:
                return 0.05
            previous_pose = self.pose._LAST_APPLIED
            applied = self.follower.consume(reply, busy=busy, ready=ready)
            if applied and self.pose._LAST_APPLIED is previous_pose:
                # apply_frame returns a warning without posing when every bone
                # was skipped. Its success marker changes only after assigning
                # matrices, so data/overlay-only updates cannot produce an ACK.
                self.follower.revision = 0
                applied = False
            if applied:
                # The add-on's existing property copy suppresses callbacks.
                # Correct its engine-label/source-name distinction for the move
                # picker without invoking load_row or losing the engine label.
                choices = {item[0] for item in self.props.row_items()}
                if self.session.source_row in choices:
                    with self.props.suspend_frame_updates():
                        settings.move = self.session.source_row
                self.operators._redraw_ui()
            self.poller.acknowledge(self.follower.revision)
        except Exception as exc:
            self._rejected_revision = reply.get("revision")
            if self.follower.revision == self._rejected_revision:
                self.follower.revision = 0
                self.poller.acknowledge(0)
            message = str(exc)
            if message != self._reported_error:
                print("GENO_WB_QT_SYNC " + message)
                self._reported_error = message
        return 0.05


def install():
    """Install one follower for the bootstrapped, connected Blender session."""
    import bpy
    from geno_workbench import api, client, operators, operators_fighter, pose, props

    previous = bpy.app.driver_namespace.get(_DRIVER_KEY)
    if previous is not None:
        previous.stop()
    session = api.session()
    if not session.connected or not isinstance(session.client, client.McpClient):
        return None
    driver = _BlenderDriver(bpy, api, client, operators, operators_fighter, pose, props)
    bpy.app.driver_namespace[_DRIVER_KEY] = driver
    driver.start()
    return driver


if __name__ in ("__main__", "<run_path>"):
    install()
