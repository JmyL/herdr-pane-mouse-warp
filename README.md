# Herdr Pane Mouse Warp

Herdr plugin for Linux/Sway that warps the pointer into the focused Herdr pane.

## Install

```bash
herdr plugin install JmyL/herdr-pane-mouse-warp --yes
```

## Behavior

- `pane.focused` event runs `herdr-warp-on-focus`.
- `warp` action runs the same one-shot warp manually.
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
