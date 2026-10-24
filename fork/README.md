# orc — v2 true source fork (scaffold)

Road: LibreWolf's own build system (codeberg.org/librewolf/source).

```
git clone https://codeberg.org/librewolf/source.git
cd source
./fetch.sh        # pulls the pinned Firefox source tree
./patch.sh        # applies the LibreWolf patch set
# add orc on top:
#   - copy branding/orc into firefox-source/browser/branding/orc
#   - our extra patches go in assets/ alongside LibreWolf's, applied last
cd firefox-source
MOZCONFIG=../fork/mozconfig ./mach build
./mach package
```

Reality, from LibreWolf's build docs: 2–4 h per platform build, ≥8 GB RAM,
~30 GB disk. This belongs in CI (one runner per OS), never on a laptop as
the release path. Windows installers need code signing and macOS needs
notarization before strangers can install without warnings — budget for
both before announcing downloads.
