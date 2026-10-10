# UI, calendar and Ready correction

Original successful release is retained at artifacts/releases/PokeLDN-TeraLoop.
Updated release: artifacts/releases/PokeLDN-TeraLoop-ui-fix.

- Original game order restored: FRLG, LGPE, SwSh, BDSP, PLA, SV, ZA.
- Original icon embedded in the executable and assigned to the desktop window;
  SV game icon is byte-identical to pinned upstream.
- Calendar now uses sourced descriptions, not reused BCAT identifiers. Includes
  all 148 numbered events in the GitHub archive, 152 packages and 161 scheduling
  options. Charizard: #2 in 2022, #49 in 2024, #117 in 2026.
- Ready gate blocks start message 10 until the console sends STATE_READY.
  Selection or idle messages invalidate confirmation; battle handoff unchanged.
- 643 tests passed before the final label refinement; packaged installation
  check passed with no radio opened. Ready requires physical-console validation.
- Sceptile healing-cheer failure, Pikachu success and terastalization rendering
  symptom are saved in USER-RAID-OBSERVATIONS-20261010.md. No speculative fix to
  healing/battle state is included.
- Site lists newer #149–152, absent from the current GitHub archive. Direct
  download requests returned HTTP 403; these are not claimed bundled.

No keys, saves, firmware or pinned upstream source were changed.
