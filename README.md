# Herdr Pane Mouse Warp

Herdr plugin for Linux/Sway that warps the pointer into the focused Herdr pane.

## Install

```bash
herdr plugin install JmyL/herdr-pane-mouse-warp --yes
```

## Behavior

- `pane.focused` event runs `herdr-warp-on-focus`.
- `warp` action runs the same one-shot warp manually.
- startup runs the Sway binding subscriber used by Kitty focus integration.
- `stamp-bindings` action starts the same subscriber manually; a lock prevents duplicate subscribers.

The scripts prefer host tools from `PATH`; when running inside a toolbox/container,
they can fall back to `flatpak-spawn --host`.
