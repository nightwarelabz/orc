# Recursive workspaces

orc supplies a consistent Gecko engine for Blacksite and the systems inside
it. The launcher also supplies an explicit **workspace tree**: descend into
a child context, run it with its own browser state, and select its parent
again. This is useful when a recursive session needs an independent login,
permissions, storage, or experiment history.

The original default profile stays where it is. A child starts with orc's
profile seed, not a copy of its parent's cookies, passwords, or tabs.

## Use the tree

```sh
# Existing default workspace, unchanged
orc https://nosuchmachine.net/

# Open a branch, then a descendant with independent browser state
orc --orc-workspace blacksite https://nosuchmachine.net/
orc --orc-workspace blacksite --orc-child experiment https://nosuchmachine.net/

# Inspect without launching the engine or creating files
orc --orc-workspace blacksite/experiment --orc-workspace-info

# Select the parent (blacksite), or return to the default root (/)
orc --orc-workspace blacksite/experiment --orc-parent
orc --orc-workspace /
```

On macOS, invoke `/Applications/orc.app/Contents/MacOS/orc`; on Windows,
invoke the installed `orc.exe`. The options are identical on every OS.
`--orc-help` lists them. Engine arguments such as `--headless`,
`--new-window`, and URLs keep their original order and values.

Selectors apply left to right. `--orc-workspace` explicitly resets the
path; `--orc-child` adds exactly one level; `--orc-parent` removes one
level and stays at `/` if already there. The starting context is
`ORC_WORKSPACE` when set, otherwise `/`. orc exports the canonical name
and its computed `ORC_WORKSPACE_DEPTH` to the engine and its subprocesses.
An unrelated terminal does not inherit environment changes from orc;
pass `--orc-workspace` explicitly there.

```json
{"workspace":"blacksite/experiment","parent":"blacksite","depth":2,"max_depth":16,"profile":"…/orc/workspaces/blacksite/children/experiment/profile"}
```

## Identity and limits

- `/` is the existing default workspace. Its parent is `null`.
- Names contain ASCII letters or digits, followed by letters, digits,
  `-`, or `_`, up to 48 characters per segment. Names are folded to
  lowercase on all platforms.
- A path has at most 16 segments. Empty segments, traversal, dots,
  absolute filesystem paths, backslashes, and Windows device names
  are rejected on every OS.
- The full profile path must also fit the operating system's path limit;
  orc reports an error instead of truncating a long path.
- A branch's profile is under
  `<orc data directory>/workspaces/<name>/children/<name>/…/profile`.
  The `children` boundary ensures a descendant is never stored inside
  its ancestor's actual browser profile.
- Engine profile selectors (`-profile`, `-P`, `-ProfileManager`, and
  `-CreateProfile`, including their long forms) are reserved. Use the
  workspace options so all launches retain orc's profile boundary.

Named workspaces pass Gecko's `-no-remote` option, so a child launch
cannot send its URL to an already running parent or another browser.
Different branches can run simultaneously. **Close a branch before
opening that same branch again**: Gecko's profile lock prevents a second
concurrent instance. Selecting a parent opens that profile; it does not
focus an existing window or close any child windows.

The depth limit bounds workspace lineage, not the number of tabs,
processes, nested frames, or simultaneously open branches. Workspace
profiles separate browser state; they are not separate OS sandboxes.

## Web recursion

A workspace continues to use Gecko's normal origin and permission rules.
Blacksite can host its own browser/OS layers inside that context. orc
does not strip CSP, COOP, COEP, `X-Frame-Options`, or certificate checks
to make another layer load. Cross-origin isolation, SharedArrayBuffer,
workers, and framing still depend on the document's headers and the
capabilities of the bundled engine.

No changes to nosuchmachine.net are required by this feature. The
launcher does not claim to discover iframe ancestry or offer a tab-tree
sidebar. This layer supplies explicit context identity and storage;
page and tab orchestration can build on that boundary.

## Verification

Run `python -m unittest discover -s tests -v`. The suite compiles the real
launcher and a small native test engine, then checks exact argv,
workspace environment, default-profile compatibility, lineage, path
rejection, permissions, and profile preservation. No live browsing,
engine download, third-party Python package, or real user profile is
needed. The same checks run on Linux, macOS, and Windows in CI.

The Linux CI job also stages the checksum-verified, pinned engine and runs
`python tests/browser_recursion.py <staged launcher>`. Two simultaneous
workspaces each load four nested documents. Every level must execute Wasm
and exchange shared memory with a worker while staying cross-origin
isolated; cookies and local storage must stay within the selected
workspace. A forbidden iframe must remain blocked. The release workflow
repeats this check against the extracted Linux artifact. The fixture only
binds to loopback and uses temporary profiles.
