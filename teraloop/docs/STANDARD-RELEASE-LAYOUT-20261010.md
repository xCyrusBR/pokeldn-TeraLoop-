# PokéLDN + TeraLoop: standard portable layout

Release folder: artifacts/releases/pokeldn. Open pokeldn.exe. Keep the whole
folder, including _internal; do not copy only the executable.

Original-style resource paths now live directly under _internal:
bin, config, docs, gui, pokeldn, services and vendor. The pinned upstream
snapshot is flattened during packaging, not edited in the research checkout.
CHECKPOINT.json retains the original source revision and file hashes.

Additional TeraLoop resources: past_raids, tools, distribution,
source-materials and lab/host-mew.pk9. The remaining lab is a single host
Pokémon asset, not the research lab or a second nested upstream checkout.

Kept: past-event tab, editable suggested Pokémon, Chronos, sourced calendar,
Ready gate, key-path dialog correction, original game ordering and icons.
Battle generator and native Mewtwo capsule remain unchanged.

Settings remain isolated under %APPDATA%/TeraLoop-PokeLDN, shared with the
previous TeraLoop release. Original PokéLDN settings are not overwritten.
Do not mix DLLs or _internal directories with the Python 3.13 original:
this build uses Python 3.14.4. Keys and console saves are not packaged.

Preserved recovery release: artifacts/releases/PokeLDN-TeraLoop-ui-fix.
Live raid success from that release does not automatically validate every
function in this newly arranged portable build. Packaging and child-process
checks are performed without opening a radio or modifying firmware/saves.

Verification: 644 tests passed. Frozen executable installation check and both
original/custom child-script --help paths passed. Frozen Mewtwo dry-run passed
with the hash-pinned boss/point and no radio opened. Ready gate, calendar,
event generator, key-dialog fix and Mewtwo capsule match the user-confirmed
ui-fix release byte-for-byte. No new physical raid was started for packaging.

Rebuild with tools/pack_teraloop_pokeldn.py --standard-layout --name pokeldn
--reference-release PATH_TO_ORIGINAL_RELEASE. Retain AGPL/GPL notices and
corresponding source when redistributing.
