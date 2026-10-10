# Additional event test: user report

The user selected a different event and reports winning the raid and reaching
the normal end. The user subsequently identified Sceptile as the event where
the healing cheer apparently failed, and reported a working healing cheer in
Pikachu. The exact round and client Pokémon remain unspecified.

Unresolved observations:

- Sceptile: healing cheer apparently did not restore HP. No controlled HP delta or
  packet evidence has yet established the cause.
- Pikachu: user reports that healing cheer worked. Do not generalize the
  Sceptile observation to all events.
- Host started roughly five seconds after entry, before the guest could choose
  a Pokémon or confirm Ready. The added Ready gate now requires the console's
  STATE_READY, and clears confirmation on selection/idle changes. Offline
  coverage is required; console validation remains pending.
- During terastalization the Pokémon briefly disappeared, then returned.
  The raid still completed. Do not assume the rendering symptom is harmless,
  or that it proves a battle-state failure, without further evidence.

The current changes restore the original PokéLDN game/tool order and executable
icon, correct calendar metadata, and gate battle start on Ready. They do not
claim a fix to healing or battle animation.
Keep the previously successful executable intact as a rollback checkpoint.
