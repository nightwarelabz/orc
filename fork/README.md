# orc — direct Gecko source-build scaffold

This directory records the path from the current pinned-engine distribution to
a complete source build.

The future build should:

1. fetch a pinned Mozilla Gecko source revision;
2. apply orc's policy and functionality patches;
3. copy the canonical assets into `browser/branding/orc`;
4. build with `fork/mozconfig`;
5. publish source and binary checksums with each release; and
6. run the same branding and recursive-workspace audits as the current
   packages.

The source build is deliberately not the v1 release gate. A browser build
requires substantial storage, memory, runner time, platform-specific signing,
and reproducible patch management. The current distribution proves the
launcher, policy, workspace, and branding contracts while that infrastructure
is prepared.

The name and icon rules do not change between architectures: the displayed
product is always lowercase `orc`, and every supported visual surface uses
the pixel orc face from `../branding/`.
