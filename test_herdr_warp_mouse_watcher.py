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
    path = Path(__file__).with_name("herdr-warp-mouse-watcher")
    loader = SourceFileLoader("herdr_warp_mouse_watcher", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


MOD = load_mod()

EV_KEY = 0x01
EV_REL = 0x02
BTN_LEFT, BTN_RIGHT, BTN_MIDDLE = 0x110, 0x111, 0x112
KEY_A = 30


def ev(type_: int, code: int, value: int) -> bytes:
    return MOD.EVENT_STRUCT.pack(0, 0, type_, code, value)


class HasButtonBitTest(unittest.TestCase):
    def test_mouse_bitmap_words(self):
        # MX Master 4 caps as printed by /sys: unpadded 64-bit words, high-to-low.
        self.assertTrue(MOD.has_button_bit("7f0000 0 0 0 0"))

    def test_touchpad_bitmap_words(self):
        self.assertTrue(MOD.has_button_bit("e520 10000 0 0 0 0"))

    def test_non_pointer_bitmaps(self):
        self.assertFalse(MOD.has_button_bit("0"))
        self.assertFalse(MOD.has_button_bit("4000 0 0"))  # sleep button
        self.assertFalse(MOD.has_button_bit("8000 10000000000000 0"))  # power button

    def test_junk(self):
        self.assertFalse(MOD.has_button_bit(""))
        self.assertFalse(MOD.has_button_bit("zz 0"))


class BufferHasButtonPressTest(unittest.TestCase):
    def test_button_press(self):
        self.assertTrue(MOD.buffer_has_button_press(ev(EV_KEY, BTN_LEFT, 1)))
        self.assertTrue(MOD.buffer_has_button_press(ev(EV_KEY, BTN_RIGHT, 1)))
        self.assertTrue(MOD.buffer_has_button_press(ev(EV_KEY, BTN_MIDDLE, 1)))

    def test_release_repeat_motion_and_keys(self):
        self.assertFalse(MOD.buffer_has_button_press(ev(EV_KEY, BTN_LEFT, 0)))
        self.assertFalse(MOD.buffer_has_button_press(ev(EV_KEY, BTN_LEFT, 2)))
        self.assertFalse(MOD.buffer_has_button_press(ev(EV_REL, 0, 5)))
        self.assertFalse(MOD.buffer_has_button_press(ev(EV_KEY, KEY_A, 1)))

    def test_multi_record_buffer(self):
        data = ev(EV_KEY, KEY_A, 1) + ev(EV_KEY, BTN_LEFT, 1) + ev(EV_KEY, BTN_LEFT, 0)
        self.assertTrue(MOD.buffer_has_button_press(data))

    def test_short_buffer(self):
        self.assertFalse(MOD.buffer_has_button_press(b"\x00"))


class WriteStampTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_writes_millis(self):
        MOD.write_stamp(self.dir, 12345)
        self.assertEqual((self.dir / "last-mouse").read_text(encoding="utf-8").strip(), "12345")

    def test_creates_dir(self):
        nested = self.dir / "herdr-warp"
        MOD.write_stamp(nested, 7)
        self.assertEqual((nested / "last-mouse").read_text(encoding="utf-8").strip(), "7")


class PointerDevicePathsTest(unittest.TestCase):
    def test_selects_button_devices(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, caps in (
                ("event0", "7f0000 0 0 0 0"),
                ("event1", "0"),
                ("event2", "4000 0 0"),
            ):
                cap_dir = root / name / "device" / "capabilities"
                cap_dir.mkdir(parents=True)
                (cap_dir / "key").write_text(caps, encoding="utf-8")
            paths = MOD.pointer_device_paths(sysfs_root=str(root))
            self.assertEqual([p.name for p in paths], ["event0"])


class DisableEnvTest(unittest.TestCase):
    def test_disable_env_is_noop(self):
        self.assertEqual(
            subprocess.run(
                [str(Path(__file__).with_name("herdr-warp-mouse-watcher"))],
                env={**os.environ, "HERDR_WARP_ON_FOCUS": "0"},
                check=False,
            ).returncode,
            0,
        )


if __name__ == "__main__":
    unittest.main()
