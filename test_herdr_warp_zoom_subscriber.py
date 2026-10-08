#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path


def load_mod():
    path = Path(__file__).with_name("herdr-warp-zoom-subscriber")
    loader = SourceFileLoader("herdr_warp_zoom_subscriber", str(path))
    spec = spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = __import__("importlib.util", fromlist=["module_from_spec"])
    mod = mod.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


MOD = load_mod()


class DecideZoomWarpTest(unittest.TestCase):
    def test_unknown_current_skips(self):
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", False), None), "skip")
        self.assertEqual(MOD.decide_zoom_warp(None, None), "skip")

    def test_first_observation_only_updates(self):
        self.assertEqual(MOD.decide_zoom_warp(None, ("w1:t1", False)), "update")
        self.assertEqual(MOD.decide_zoom_warp(None, ("w1:t1", True)), "update")

    def test_tab_switch_only_updates(self):
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", True), ("w1:t2", False)), "update")
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", False), ("w2:t1", True)), "update")

    def test_same_tab_flip_warps(self):
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", False), ("w1:t1", True)), "warp")
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", True), ("w1:t1", False)), "warp")

    def test_same_tab_no_flip_skips(self):
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", False), ("w1:t1", False)), "skip")
        self.assertEqual(MOD.decide_zoom_warp(("w1:t1", True), ("w1:t1", True)), "skip")


class PerTabStateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.environ["HERDR_WARP_DIR"] = tmp.name
        self.addCleanup(os.environ.pop, "HERDR_WARP_DIR", None)

    def test_roundtrip_per_tab(self):
        self.assertIsNone(MOD.read_state("w8P:t1"))
        MOD.write_state(("w8P:t1", True))
        self.assertEqual(MOD.read_state("w8P:t1"), ("w8P:t1", True))
        self.assertIsNone(MOD.read_state("w8P:t2"))
        MOD.write_state(("w8P:t1", False))
        self.assertEqual(MOD.read_state("w8P:t1"), ("w8P:t1", False))

    def test_malformed_state_is_none(self):
        path = MOD.state_path("w1:t1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("garbage\n", encoding="utf-8")
        self.assertIsNone(MOD.read_state("w1:t1"))


class EnabledTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("HERDR_WARP_ON_FOCUS")
        self.addCleanup(self._restore)

    def _restore(self):
        if self._saved is None:
            os.environ.pop("HERDR_WARP_ON_FOCUS", None)
        else:
            os.environ["HERDR_WARP_ON_FOCUS"] = self._saved

    def test_enabled_by_default(self):
        os.environ.pop("HERDR_WARP_ON_FOCUS", None)
        self.assertTrue(MOD.enabled())

    def test_disabled_values(self):
        for value in ("0", "false", "no", "off"):
            os.environ["HERDR_WARP_ON_FOCUS"] = value
            self.assertFalse(MOD.enabled(), value)


if __name__ == "__main__":
    unittest.main()