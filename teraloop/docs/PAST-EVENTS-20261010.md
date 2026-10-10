# TeraLoop: past events in PokéLDN

Scope: 148 numbered Project Pokémon events, represented by 152 delivery
packages and 161 scheduling choices. Event rounds, shared-delivery weekends
and corrected packages are separate choices, in actual historical date
order. Ordinary raids are not included. Scarlet/Violet 4.0.0, local/offline.

Open PokéLDN + TeraLoop, choose Scarlet & Violet, then **TeraLoop — Past
events**. Select the event and game version. An encounter selector covers
spotlight side encounters. The featured highest-star encounter is the default.
The suggested host Pokémon remains editable; the console chooses its own
Pokémon. The host waits for the console's Ready and leaves through host migration.
It does not execute a solo strategy in battle. The suggested date is optional.

The verified catalogue dates are in `distribution/event-calendar.json` with
individual Project Pokémon description links and cross-check sources. BCAT
Identifier.txt is preserved verbatim and is not used as a rerun's date.
The GitHub archive currently ends at #148. Project Pokémon's site additionally
lists #149–152 (Skeledirge, Quaquaval, Dragonite and Tyranitar reruns); their
download currently returns HTTP 403 here. They are not claimed bundled.

## Evidence and limits

- The measured Mewtwo handoff is preserved. Its boss generated from source
  also matches the measured encrypted PK9 byte for byte.
- Offline audit: 532 of 537 active encounters generate successfully. The five
  failures are the intentionally glitched first Scarlet Gimmighoul delivery,
  package 024-025, which lacks required reward tables. The corrected delivery
  is supported separately. Never silently fabricate its rewards.
- All 537 encounter recommendations pass build legality checks. This does
  not prove that each build wins, nor that each generated event works on a
  physical console. Representative console testing remains pending.
- Full game-equivalent NPC randomness and opaque RaidPoint context words are
  not claimed verified. No copied battle snapshots or extra synthetic players.

## Strategy provenance

64 archive defaults are recorded in distribution/strategy-defaults.tsv with
individual Discord message links. Matching is boss/form, stars and Tera type,
not just event title. Repeated rounds can reuse the same relevant build.
Missing-guide encounters receive an explicitly labelled TeraLoop suggestion,
not an invented Discord guide or guaranteed solo strategy. Suggestions rank
already legal builds by offensive coverage, resistance and sustain; they do
not simulate the full boss script. One default is offered per encounter.

Selected archive alternatives where legal helper generation failed: Florges
for Dialga/Palkia, Bellibolt for Blaziken, Corviknight for Hisuian Decidueye,
Dachsbun for Hisuian Typhlosion, Flutter Mane for Iron Bundle, Orthworm for
Zamazenta. Gimmighoul uses the archive's explicitly allowed Ursaring alternative
to Ursaluna, without illegal Headlong Rush. The Ursaluna image was inspected.
Kommo-o was chosen for Kingambit instead of giving Iron Hands Swords Dance.
Primarina uses the actual Vaporeon guide rather than the mislinked index item.

## Reproduction

Source launcher: `py -3.14 tools/teraloop_pokeldn.py --pkhex PATH_TO_HELPER`.
Install Flet 1.0.2 and upstream runtime dependencies first. The launcher uses
isolated settings under `%APPDATA%/TeraLoop-PokeLDN` and does not alter the
original PokéLDN settings or pinned source checkout.

Audit tools: audit_generated_events.py, audit_event_recommendations.py,
verify_strategy_builds.py. The corresponding dated JSON reports are under
artifacts. Source data hashes and source URLs accompany the catalogue.
Keys, ROMs, console saves and full private captures are not release assets.

Browser preview cannot return a local Windows path from its file chooser.
The setup dialogue instead accepts a local path, reports failure visibly and
confirms success. It never uploads key contents. Desktop supports Browse.

Upstream PokéLDN/LDN and the extension must retain applicable AGPL/GPL source
and notices when shared; preserve the exact upstream checkpoint manifest.
