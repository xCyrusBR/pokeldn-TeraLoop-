## Download / baixar

Windows x64: download **PokeLDN-TeraLoop-windows-x64.zip**, extract the entire
folder and launch `pokeldn.exe`. Keep `_internal` beside it. `SHA256SUMS.txt`
provides the archive checksum. Source is included in this repository under
`teraloop/`; GitHub's automatic source archives contain the build instructions.

Scarlet & Violet → **TeraLoop — Past events** adds 148 numbered event raids,
152 delivery packages and 161 chronological scheduling choices. Suggested host
Pokémon are editable; the console chooses its own Pokémon. Chronos waits for
Ready, then leaves through host migration so the console continues locally.

Included: historical date/round corrections, original game order/icons,
local-key setup dialog, Ready gate, strategies with provenance and labelled
fallback suggestions. No PR2/PR3 participants; no claim of an autonomous
in-battle strategy engine or a complete Eden bridge in this build.

Use your own ESP32-S3 and console keys. No keys, ROMs, console saves or private
captures are bundled. This is unofficial, based on Decryptu's PokéLDN;
upstream credits/licenses are retained.

### Preview limits

- Only representative raids have been tested on a physical console, not all 148.
- Sceptile healing cheer and temporary ally disappearance during terastalization
  remain observations to investigate. Pikachu healing was reported working.
- Original glitched Gimmighoul package is rejected when reward tables are missing;
  its corrected delivery is separate. 532/537 active encounters pass offline
  generation audits; legality does not guarantee a solo victory.
- Project Pokémon website events #149–152 were not in the pinned Git archive and
  are not bundled. Do not confuse these with the 152 delivery packages.
- The portable layout has offline verification; its previous UI-fixed build had
  console confirmation. A new console test of this repackaged layout is pending.

### Corresponding source

Extension: `teraloop/past_raids`, `teraloop/tools`, `teraloop/distribution`.
Build: `teraloop/README.md`. Exact upstream runtime checkpoint:
`92a5bd72445bed3cf260d9f7e6ff9149afe1adf2`.
The fork root remains on the newer upstream base; the build script fetches the
tested checkpoint separately. Public Mewtwo data contains boss/RaidPoint only,
not captured participants. The artificial Mew template is deliberately shared.

Português: extraia o ZIP inteiro; abra `pokeldn.exe`. O código-fonte e as
instruções estão no repositório. Cada usuário fornece suas próprias chaves.
Esta é uma prévia comunitária, não uma versão oficial do Decryptu.
