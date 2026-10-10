# PokéLDN + TeraLoop

Historical Scarlet/Violet event raids, through an ESP32-S3 radio and an unmodified
Switch. This is an additive community extension to Decryptu's PokéLDN, not an
Eden bridge. No extra synthetic participants are included in this release.

## Windows portable app

Download `PokeLDN-TeraLoop-windows-x64.zip` from this fork's Releases, extract all
files, and open `pokeldn.exe`. Keep `_internal` beside it. Python installation is
not required for the portable executable. Use the firmware installation flow
and your own `prod.keys` locally. Keys are not bundled or uploaded.

Choose **Scarlet & Violet → TeraLoop — Past events**, select an event, version
and editable host Pokémon. Choose your own Pokémon on the Switch and press
Ready. The host hands the raid over to the console; it does not follow a DPS
strategy or remain in battle. Event dates are optional recommendations.

148 event numbers / 152 packages / 161 scheduling windows are provided in
chronological order. Archive strategies have source links; missing-guide builds
are labelled suggestions, not guaranteed solo solutions. See
[event coverage](docs/PAST-EVENTS-20261010.md) and
[known observations](docs/USER-RAID-OBSERVATIONS-20261010.md).
Healing in Sceptile and temporary disappearances during terastalization remain
unresolved observations. The original glitched Gimmighoul delivery is rejected
when its reward tables are missing; its corrected delivery is separate.

## Source setup (Windows, Python 3.14, Git)

Run from the repository root in PowerShell:

```powershell
cd teraloop
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe tools\prepare_upstream.py --reference-release C:\path\to\official\pokeldn
Push-Location lab\upstream-pokeldn-92a5bd7
..\..\.venv\Scripts\python.exe -m pip install -r gui\requirements.txt
Pop-Location
.\.venv\Scripts\python.exe tools\teraloop_pokeldn.py --check-installation
.\.venv\Scripts\python.exe tools\teraloop_pokeldn.py
```

`--reference-release` refers to an extracted official Windows PokéLDN release
containing `_internal`. Only the PKHeX helper, Flet viewer and firmware are copied;
never its keys or user settings. Use an official release providing Flet 1.0.2.
The helper's source is in upstream `services/pkhex`; the viewer is Flet's standard
Windows client. The pinned checkout is ignored by Git and never edited. Settings
are isolated under `%APPDATA%/TeraLoop-PokeLDN`.

Build a new executable (not bit-for-bit reproducible across different dependency
environments):

```powershell
.\.venv\Scripts\python.exe tools\pack_teraloop_pokeldn.py --reference-release C:\path\to\official\pokeldn --standard-layout --name pokeldn
```

Output: `teraloop/artifacts/releases/pokeldn`. Dependencies are those from the
pinned upstream GUI requirements. The published executable uses Python 3.14.4;
do not mix its DLLs with the original Python 3.13 release.

Offline extension checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Additional audit scripts are in `tools/`. Their report paths must be fresh.
Tests and build do not require a connected console or open the radio.

## Source layout and provenance

- `past_raids/`: UI adapter, Ready gate, event selection/generation, suggestions.
- `distribution/`: hash-verified Project Pokémon events, dates, strategy defaults.
- `source-materials/mewtwo-event/`: public event reference.
- `lab/host-mew.pk9`: deliberately shared artificial host template, not a console save.
- `distribution/mewtwo-native-capsule.bin`: boss and RaidPoint only; no participants,
  trainer identities, network addresses or full captured traffic.
- `tools/`: launcher, offline audits, pinned-checkout preparation and packaging.

The fork root follows upstream; the extension pins the tested September/October
checkpoint explicitly. This avoids replacing recent upstream improvements or
silently changing the binary's tested behavior. To migrate to a newer checkpoint,
review and test it before changing the pin/manifest and rebuilding.

See [third-party notices](THIRD-PARTY-NOTICES.md). Repository license: AGPL-3.0.
Retain source and applicable dependency notices when redistributing.
