#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


def load_mod():
    path = Path(__file__).with_name("herdr-warp-binding-stamp")
    loader = SourceFileLoader("herdr_warp_binding_stamp", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


MOD = load_mod()


class CommandChangesFocusTest(unittest.TestCase):
    def test_plain_focus(self):
        self.assertTrue(MOD.command_changes_focus("focus left"))
        self.assertTrue(MOD.command_changes_focus("workspace number 3"))
        self.assertTrue(MOD.command_changes_focus("scratchpad show"))

    def test_criteria_and_chain(self):
        self.assertTrue(MOD.command_changes_focus('[app_id="kitty"] focus'))
        self.assertTrue(MOD.command_changes_focus("exec foo; focus right"))

    def test_ignores_unrelated(self):
        self.assertFalse(MOD.command_changes_focus("exec ~/.local/bin/herdr-agent-focus"))
        self.assertFalse(MOD.command_changes_focus("kill"))
        self.assertFalse(MOD.command_changes_focus(""))


class ShouldStampTest(unittest.TestCase):
    def test_keyboard_focus_binding(self):
        self.assertTrue(
            MOD.should_stamp(
                {
                    "change": "run",
                    "binding": {"command": "focus left", "input_type": "keyboard"},
                }
            )
        )

    def test_defaults_input_type_to_keyboard(self):
        self.assertTrue(MOD.should_stamp({"binding": {"command": "workspace number 1"}}))

    def test_ignores_mouse_binding(self):
        self.assertFalse(
            MOD.should_stamp(
                {
                    "change": "run",
                    "binding": {"command": "focus left", "input_type": "mouse"},
                }
            )
        )

    def test_ignores_non_focus_keyboard(self):
        self.assertFalse(
            MOD.should_stamp(
                {
                    "change": "run",
                    "binding": {"command": "exec $term", "input_type": "keyboard"},
                }
            )
        )


class HandleLineTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.warp_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_writes_stamp_for_focus_binding(self):
        line = '{"change":"run","binding":{"command":"focus left","input_type":"keyboard"}}'
        self.assertTrue(MOD.handle_line(line, self.warp_dir))
        raw = (self.warp_dir / "last-binding").read_text(encoding="utf-8").strip()
        self.assertTrue(raw.isdigit())

    def test_ignores_hover_noise(self):
        self.assertFalse(MOD.handle_line("not-json", self.warp_dir))
        self.assertFalse(MOD.handle_line("", self.warp_dir))
        self.assertFalse(
            MOD.handle_line(
                '{"change":"run","binding":{"command":"nop","input_type":"keyboard"}}',
                self.warp_dir,
            )
        )
        self.assertFalse((self.warp_dir / "last-binding").exists())


class DisableEnvTest(unittest.TestCase):
    def test_disable_env_is_noop(self):
        self.assertEqual(
            __import__("subprocess").run(
                [str(Path(__file__).with_name("herdr-warp-binding-stamp"))],
                env={**os.environ, "HERDR_WARP_ON_FOCUS": "0"},
                check=False,
            ).returncode,
            0,
        )


if __name__ == "__main__":
    unittest.main()
