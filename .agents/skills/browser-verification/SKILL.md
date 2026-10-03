---
name: browser-verification
description: REQUIRES project Playwright tooling (opencode.jsonc MCP + npx playwright-cli) — browser automation for visual verification, screenshots, and UI regression checks against local dev servers or deployed pages. Triggers: screenshot, visual QA, browser check, open page, verify layout, dropdown/modal state, pixel comparison.
---

# Browser Verification

Two entry points, both pinned and smoke-tested on this system:

1. **`playwright-cli`** (primary — token-efficient CLI, stateful sessions).
   Run through npx without installing anything:
   ```bash
   npx -y @playwright/cli@0.1.22 open <url>
   ```
   Machine-global `~/.playwright/cli.config.json` (NOT committed,
   machine-local) sets `browser.launchOptions.executablePath` to the
   system `/usr/bin/chromium` and `browser.launchOptions.env` maps
   `XDG_CONFIG_HOME` into the browser process (both verified via
   `/proc/*/environ`) — no `--browser` flag and no shell env prefix
   needed. Without that config the default channel is `chrome`, which
   expects a branded Google Chrome install.

2. **Playwright MCP** (fallback, registered in `opencode.jsonc` as
   `mcp.playwright` with `@playwright/mcp@0.0.83`, the same env fix baked
   into `environment`). Tools surface as the first-class
   `playwright_browser_*` toolset (navigate / snapshot / click /
   take_screenshot / evaluate / ...).

The OMO builtin `playwright` skill stays disabled globally — do not
re-enable it; this project layer supersedes it.

## XDG quirk (this machine)

`/home/klinkovsky/.config` is a **read-only btrfs mount**. Chrome >= 128
needs `$XDG_CONFIG_HOME/chromium` to spawn its crashpad handler, and dies
with `chrome_crashpad_handler: --database is required` / SIGTRAP if it
can't write there (crbug 40259944). Redirection to
`/tmp/opencode/.chromium-mcp-config` (tmpfs, writable) fixes all
launches — system `/usr/bin/chromium` and the bundled Playwright
chromium both work under it. Delivery is automatic on both entry
points: the MCP carries the fix in its `environment` block
(opencode.jsonc), playwright-cli in `launchOptions.env`
(`~/.playwright/cli.config.json`). Only if a launch ever bypasses the
config, prefix `XDG_CONFIG_HOME=/tmp/opencode/.chromium-mcp-config` on
the command.

## playwright-cli flow

```bash
P="npx -y @playwright/cli@0.1.22"
$P open <url>                      # starts named session 'default'
$P snapshot                        # aria snapshot with eN refs
$P click e15                       # interact by ref (not CSS guesses)
$P screenshot [--filename=/tmp/opencode/x.png] [--hires]
$P close-all                       # always leave sessions closed
```

- Refs come from `snapshot` output, never guess selectors; re-snapshot
  after navigation or DOM-changing interactions.
- Local dev server: `http://localhost:3000` (CRA HashRouter →
  `http://localhost:3000/#/program` style URLs).
- Interactive states: capture rest / mid / settled frames when judging
  animations or dropdown-open states.
- Sessions persist in memory across calls within the same shell run;
  `close-all` when done (or `-s=<name> delete-data` for named ones).

## Verification discipline

Compare against the user's reference screenshot for layout/style, not
byte-identical pixels (antialiasing differs across builds). Save evidence
PNGs to `/tmp/opencode/` unless the user gave a path. Do NOT use this for
plain fetches or search — dedicated web tools are cheaper.
