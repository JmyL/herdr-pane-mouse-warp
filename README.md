# Herdr Pane Mouse Warp

Herdr plugin for Linux/Sway that warps the pointer into the focused Herdr pane.

## Install

```bash
herdr plugin install JmyL/herdr-pane-mouse-warp --yes
```

## Behavior

- `pane.focused` event runs `herdr-warp-on-focus`.
- `warp` action runs the same warp with `--force`: it never suppresses.
- Mouse-click activation: the `pane.focused` hook fires for clicks too, and
  Herdr's event does not say what caused the focus. A startup watcher
  (`herdr-warp-mouse-watcher`) reads evdev directly and stamps the last
  mouse-button press (BTN_LEFT/RIGHT/MIDDLE) in the warp runtime dir;
  `herdr-warp-on-focus` skips the warp while that stamp is fresher than
  `HERDR_WARP_MOUSE_QUIET_MS` (default 250). The button press always
  precedes the focus event, so the ordering is safe. No stamp means warp,
  so a watcher that cannot read `/dev/input` degrades to the old behavior.
- Zoom in/out: a startup subscriber (`herdr-warp-zoom-subscriber`) connects to the Herdr
  socket API, subscribes to `layout.updated`, and runs the same warp when a tab's zoom
  state flips. Zoomed panes target the window center; unzoomed panes target the pane
  center. Splits, resizes, and background-tab zooms never warp.
- startup runs the Sway binding subscriber used by Kitty focus integration.
- `stamp-bindings` action starts the same subscriber manually; a lock prevents duplicate subscribers.

Herdr rejects `layout.updated` as a plugin manifest event name (unknown event warning,
hook never invoked), which is why zoom detection uses a socket subscriber instead of a
manifest event hook.

The scripts prefer host tools from `PATH`; when running inside a toolbox/container,
they can fall back to `flatpak-spawn --host`.
