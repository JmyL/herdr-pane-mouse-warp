#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


def load_mod():
    path = Path(__file__).with_name("herdr-warp-on-window-focus")
    loader = SourceFileLoader("herdr_warp_on_window_focus", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


MOD = load_mod()


class DecideActionTest(unittest.TestCase):
    def test_recent_pane_warp_skips(self):
        self.assertEqual(
            MOD.decide_action(recent_pane=True, is_herdr=True, title_herdr=True),
            "skip",
        )

    def test_herdr_computes(self):
        self.assertEqual(
            MOD.decide_action(recent_pane=False, is_herdr=True, title_herdr=False),
            "compute",
        )

    def test_plain_kitty_skips(self):
        self.assertEqual(
            MOD.decide_action(recent_pane=False, is_herdr=False, title_herdr=False),
            "skip",
        )

    def test_title_fallback_computes(self):
        self.assertEqual(
            MOD.decide_action(recent_pane=False, is_herdr=False, title_herdr=True),
            "compute",
        )


class HelperTest(unittest.TestCase):
    def test_title_has_herdr(self):
        self.assertTrue(MOD.title_has_herdr("herdr"))
        self.assertTrue(MOD.title_has_herdr("codex: x (herdr-lab)"))
        self.assertFalse(MOD.title_has_herdr("codex: Implement title sync (app-ios)"))


class RecentPaneWarpFileTest(unittest.TestCase):
    def setUp(self):
        self._old = MOD.WARP_DIR
        self.td = tempfile.TemporaryDirectory()
        MOD.WARP_DIR = Path(self.td.name)

    def tearDown(self):
        MOD.WARP_DIR = self._old
        self.td.cleanup()

    def test_reads_stamp(self):
        (MOD.WARP_DIR / "last-pane-warp").write_text("900\n", encoding="utf-8")
        self.assertTrue(MOD.recent_pane_warp(now_ms=1000, skip_ms=200))
        self.assertFalse(MOD.recent_pane_warp(now_ms=1200, skip_ms=200))

    def test_normalizes_nanosecond_stamp(self):
        (MOD.WARP_DIR / "last-pane-warp").write_text("1786802984945927748\n", encoding="utf-8")
        self.assertEqual(MOD.last_pane_warp_ms(), 1786802984945)


class KittyHasHerdrTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._old = MOD.PROC_ROOT
        MOD.PROC_ROOT = Path(self.td.name)

    def tearDown(self):
        MOD.PROC_ROOT = self._old
        self.td.cleanup()

    def _proc(self, pid: int, comm: str, child_pids: list[int] | None = None, cmdline: str = "") -> None:
        proc = MOD.PROC_ROOT / str(pid)
        task = proc / "task" / str(pid)
        task.mkdir(parents=True)
        (proc / "comm").write_text(f"{comm}\n", encoding="utf-8")
        raw = cmdline.replace(" ", "\0") + "\0" if cmdline else f"{comm}\0"
        (proc / "cmdline").write_bytes(raw.encode())
        children = " ".join(str(c) for c in (child_pids or []))
        (task / "children").write_text(f"{children}\n" if children else "", encoding="utf-8")

    def test_finds_direct_herdr_child(self):
        self._proc(10, "kitty", [11])
        self._proc(11, "herdr")
        self.assertTrue(MOD.kitty_has_herdr(10))

    def test_ignores_plain_shell(self):
        self._proc(10, "kitty", [11])
        self._proc(11, "bash")
        self.assertFalse(MOD.kitty_has_herdr(10))

    def test_finds_nested_herdr(self):
        self._proc(10, "kitty", [11])
        self._proc(11, "bash", [12])
        self._proc(12, "herdr")
        self.assertTrue(MOD.kitty_has_herdr(10))


class WarpOnFocusScriptTest(unittest.TestCase):
    def test_disable_env_is_noop(self):
        script = Path(__file__).with_name("herdr-warp-on-focus")
        result = subprocess.run(
            [str(script)],
            env={**os.environ, "HERDR_WARP_ON_FOCUS": "0"},
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_finds_herdr_in_user_bin_when_path_is_minimal(self):
        script = Path(__file__).with_name("herdr-warp-on-focus")
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            user_bin = home / ".local" / "bin"
            user_bin.mkdir(parents=True)
            log = home / "herdr.log"
            (user_bin / "herdr").write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >>\"$HERDR_WARP_TEST_LOG\"\nexit 1\n",
                encoding="utf-8",
            )
            (user_bin / "herdr").chmod(0o755)
            result = subprocess.run(
                [str(script)],
                env={
                    "HOME": str(home),
                    "PATH": "/usr/bin:/bin",
                    "HERDR_WARP_ON_FOCUS": "1",
                    "HERDR_WARP_TEST_LOG": str(log),
                },
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(log.is_file())
            self.assertIn("pane layout --current", log.read_text(encoding="utf-8"))


class CursorNudgeTest(unittest.TestCase):
    def _run(self, x: int, y: int) -> tuple[int, str]:
        script = Path(__file__).with_name("herdr-warp-on-focus")
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            log = td / "sway.log"
            sway = td / "swaymsg"
            sway.write_text(
                '#!/bin/sh\nprintf \'%s\\n\' "$*" >>"$HERDR_WARP_TEST_LOG"\n',
                encoding="utf-8",
            )
            sway.chmod(0o755)
            result = subprocess.run(
                [str(script), "--cursor-only", str(x), str(y)],
                env={
                    "HOME": str(td),
                    "PATH": f"{td}:/usr/bin:/bin",
                    "HERDR_WARP_ON_FOCUS": "1",
                    "HERDR_WARP_TEST_LOG": str(log),
                },
                check=False,
            )
            text = log.read_text(encoding="utf-8") if log.is_file() else ""
            return result.returncode, text

    def test_sets_one_pixel_left_then_moves_right(self):
        code, log = self._run(100, 200)
        self.assertEqual(code, 0)
        self.assertIn("seat seat0 cursor set 99 200", log)
        self.assertIn("seat seat0 cursor move 1 0", log)
        self.assertNotIn("cursor set 100 200", log)

    def test_avoids_sway_zero_axis_then_nudges_vertically(self):
        code, log = self._run(1, 200)
        self.assertEqual(code, 0)
        self.assertIn("seat seat0 cursor set 1 200", log)
        self.assertIn("seat seat0 cursor move 0 1", log)
        self.assertNotIn("cursor set 0 ", log)


class OneShotWindowFocusTest(unittest.TestCase):
    def setUp(self):
        self._old_dir = MOD.WARP_DIR
        self._old_compute = MOD.compute_warp
        self._old_has_herdr = MOD.kitty_has_herdr
        self.td = tempfile.TemporaryDirectory()
        MOD.WARP_DIR = Path(self.td.name)
        self.computes: list[str] = []
        MOD.compute_warp = lambda token: self.computes.append(token)
        os.environ["HERDR_WARP_BINDING_WAIT_MS"] = "0"
        (MOD.WARP_DIR / "last-binding").write_text(
            str(int(__import__("time").time() * 1000)),
            encoding="utf-8",
        )

    def tearDown(self):
        MOD.WARP_DIR = self._old_dir
        MOD.compute_warp = self._old_compute
        MOD.kitty_has_herdr = self._old_has_herdr
        os.environ.pop("HERDR_WARP_FOCUSED_PID", None)
        os.environ.pop("HERDR_WARP_BINDING_WAIT_MS", None)
        self.td.cleanup()

    def test_cancel_is_noop(self):
        self.assertEqual(MOD.main(["--cancel"]), 0)
        self.assertFalse((MOD.WARP_DIR / "window-pending").exists())

    def test_stale_token_skips_compute(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "99"
        MOD.kitty_has_herdr = lambda pid: True
        token = MOD.bump_token()
        (MOD.WARP_DIR / "window-pending").write_text("other\n", encoding="utf-8")
        self.assertEqual(MOD.handle_focused_kitty(99, "herdr", token), "skip stale-token")
        self.assertEqual(self.computes, [])

    def test_skips_when_sway_focus_left_kitty(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "1"
        MOD.run_focus_in(99, "herdr")
        self.assertEqual(self.computes, [])
        self.assertIn("not-focused", (MOD.WARP_DIR / "last-run").read_text(encoding="utf-8"))

    def test_skips_when_hold_window_is_fresh(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "99"
        MOD.kitty_has_herdr = lambda pid: True
        (MOD.WARP_DIR / "hold-window").write_text(str(int(__import__("time").time() * 1000)), encoding="utf-8")
        MOD.run_focus_in(99, "herdr")
        self.assertEqual(self.computes, [])
        self.assertIn("hold-window", (MOD.WARP_DIR / "last-run").read_text(encoding="utf-8"))

    def test_skips_when_pane_just_warped(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "99"
        (MOD.WARP_DIR / "last-pane-warp").write_text(str(int(__import__("time").time() * 1000)), encoding="utf-8")
        MOD.run_focus_in(99, "herdr")
        self.assertEqual(self.computes, [])
        self.assertIn("recent-pane", (MOD.WARP_DIR / "last-run").read_text(encoding="utf-8"))

    def test_computes_when_sway_still_on_herdr_kitty(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "99"
        MOD.kitty_has_herdr = lambda pid: True
        MOD.run_focus_in(99, "title")
        self.assertEqual(len(self.computes), 1)

    def test_skips_when_no_keyboard_binding(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "99"
        MOD.kitty_has_herdr = lambda pid: True
        (MOD.WARP_DIR / "last-binding").unlink()
        MOD.run_focus_in(99, "herdr")
        self.assertEqual(self.computes, [])
        self.assertIn("no-keyboard", (MOD.WARP_DIR / "last-run").read_text(encoding="utf-8"))

    def test_skips_when_keyboard_binding_is_stale(self):
        os.environ["HERDR_WARP_FOCUSED_PID"] = "99"
        MOD.kitty_has_herdr = lambda pid: True
        (MOD.WARP_DIR / "last-binding").write_text("1\n", encoding="utf-8")
        MOD.run_focus_in(99, "herdr")
        self.assertEqual(self.computes, [])
        self.assertIn("no-keyboard", (MOD.WARP_DIR / "last-run").read_text(encoding="utf-8"))

    def test_with_user_bin_prepends_once(self):
        env = {"PATH": "/usr/bin:/bin"}
        home_bin = str(Path.home() / ".local/bin")
        out = MOD.with_user_bin(env)
        self.assertTrue(out["PATH"].startswith(f"{home_bin}:"))
        again = MOD.with_user_bin(out)
        self.assertEqual(again["PATH"].count(home_bin), 1)

    def test_disable_env_skips_cli(self):
        script = Path(__file__).with_name("herdr-warp-on-window-focus")
        result = subprocess.run(
            [str(script), "--pid", "1", "--title", "herdr"],
            env={**os.environ, "HERDR_WARP_ON_FOCUS": "0"},
            check=False,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
