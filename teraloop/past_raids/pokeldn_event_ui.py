"""TeraLoop past-event tool inside PokéLDN's Scarlet & Violet game page.

An additive runtime extension; the pinned host implementation is never edited.
"""
from dataclasses import replace
from pathlib import Path
import threading

from .event_selector import ROOT, catalog, selections, select, event_options
from .event_recommendation import choose, candidates
from .strategy_builder import build

TOOL_KEY = 'sv-teraloop-host'


def install(pkhex):
    import flet as ft
    from pokeldn import pokemon, gen9
    from pokeldn.sv import raid_encounter
    from pokeldn.app import catalog as app_catalog, paths, runner
    Field, Tool = app_catalog.Field, app_catalog.Tool
    options = event_options()
    script = str(ROOT/'tools/sv_upstream_handoff.py')
    tool = Tool(TOOL_KEY, 'TeraLoop — Past events', script,
        'Host a past Poké Portal event; the console continues after host migration. '
        'Mewtwo checkpoint verified; other deliveries use experimental source generation.',
        ('Keep Scarlet/Violet 4.0.0 in local/offline mode.',
         'Search by the four-digit code shown here, then choose any Pokémon on your console.',
         'Choose your Pokémon, then confirm Ready. The host waits for your confirmation and leaves during battle handoff.'),
        fields=(Field('--event-key', 'Past event', 'choice', choices=options, default='029-031',
                      required=True, help='Chronological Project Pokémon catalogue; events only.'),
                Field('--version', 'Game version', 'choice', default='violet',
                      choices=(('violet', 'Violet'), ('scarlet', 'Scarlet'))),
                Field('--pokemon', 'Suggested host Pokémon — editable', 'pokemon', required=True,
                      help='One default per encounter. Import or build a different legal Pokémon if preferred.'),
                Field('--code', 'Local raid code (4 digits)', default='9274', required=True),
                Field('--experimental-generated', 'Enable generated past events', 'switch', default=True,
                      help='Offline audited, not individually verified on console. '
                           'The validated Mewtwo capsule is preserved.'),
                Field('--seconds', 'Session limit (seconds)', 'number', default='420', hidden=True)),
        fixed=('--pkhex', str(Path(pkhex).resolve()), '--port', 'auto',
               '--capture', str(paths.SESSION/'captures/teraloop-{stamp}.jsonl'),
               '--stop-file', str(paths.SESSION/'captures/teraloop-{stamp}.stop')),
        doc='sv_raid.md')
    # Add the tool without reordering games or the original tools. In
    # particular, Scarlet & Violet keeps its place between PLA and ZA.
    app_catalog.GAMES = tuple(
        replace(g, tools=(*g.tools, tool)) if g.key == 'sv' else g for g in app_catalog.GAMES)
    from gui import theme as t
    from gui.views import games
    games.GAMES = app_catalog.GAMES
    original_cards, original_set, original_select = (
        games.GamesView.basic_cards, games.GamesView.set_value, games.GamesView.select)

    def refresh(view):
        view.render_body()
        if view.visible:
            view.cards.update()
            view.session.refresh()

    def request(view, *, force=False):
        if view.tool.key != TOOL_KEY:
            return
        key = view.values.get('--event-key', '029-031')
        version = view.values.get('--version', 'violet')
        index = view.values.get('--encounter')
        identity = (key, version, index)
        # Keep user edits when returning to the tab. Event changes select a new default.
        keep_offer = not force and view.stored().get('default_for') == list(identity) and view.values.get('--pokemon')
        if keep_offer and getattr(view, '_teraloop_rows', ()):
            return
        token = object()
        view._teraloop_request = token
        view._teraloop_note = 'Loading event and checking the suggested build…'
        captured_offer = view.values.get('--pokemon')
        def work():
            try:
                names = {r['id']: r['name'] for r in pokemon.SERVICE.species('sv')}
                selected = select(key, gen9, names, version=version, index=index)
                if key == '024-025':
                    raise ValueError('This original Gimmighoul delivery has corrupted reward tables. '
                                     'Select the separately listed corrected Gimmighoul delivery instead.')
                guide, provenance = choose(selected, pokemon.SERVICE)
                trainer = dict(view.app.settings.trainer('sv'), ot='Chronos')
                result = dict(keep_offer) if keep_offer else build(guide, pokemon.SERVICE, gen9, raid_encounter, trainer,
                    version=version, seed_file=ROOT/'lab/host-mew.pk9' if guide.pokemon == 'Mew' else None)
                result['summary'] = result.get('summary', '') if keep_offer else pokemon.summary(result)
                result['species_name'] = result.get('species_name', result['species'])
                result['species'] = result['species_id']
                if not keep_offer:
                    result['options'] = pokemon.SERVICE.paste('sv', guide.showdown(), trainer,
                        version='VL' if version == 'violet' else 'SL')[0]['options']
                result['recommendation'] = provenance
                note = (f"{selected.label}\nRecommended date: {selected.catalog['start']} (optional).\n"
                        + provenance['note'] + '\nSource guide: ' + provenance['source'] + '\n' + guide.showdown())
                result_rows = selections(key, gen9, names)
                error = None
            except Exception as failure:
                result, result_rows, note, error = None, (), str(failure), failure
            def done():
                if view.tool.key != TOOL_KEY or getattr(view, '_teraloop_request', None) is not token:
                    return
                if identity != (view.values.get('--event-key', '029-031'),
                    view.values.get('--version', 'violet'), view.values.get('--encounter')):
                    return
                view._teraloop_note, view._teraloop_rows = note, result_rows
                if result is not None and (force or view.values.get('--pokemon') == captured_offer):
                    view.values['--pokemon'] = result
                    view.stored()['default_for'] = list(identity)
                elif error:
                    # Never quietly retain the previous event's recommendation.
                    if view.values.get('--pokemon') == captured_offer:
                        view.values.pop('--pokemon', None)
                view.app.settings.save()
                refresh(view)
            view.app.ui(done)
        threading.Thread(target=work, daemon=True).start()

    def cards(view):
        out = original_cards(view)
        if view.tool.key != TOOL_KEY:
            return out
        rows = getattr(view, '_teraloop_rows', ())
        def changed(e):
            value = int(e.control.value)
            view.values['--encounter'] = value
            view.extra['--encounter'] = str(value)
            view.app.settings.save()
            request(view, force=True)
            refresh(view)
        compatible = [r for r in rows if r.rule['RomVer'] in (
            0, 1 if view.values.get('--version', 'violet') == 'scarlet' else 2)]
        if compatible:
            selected_index = view.values.get('--encounter')
            if selected_index is None:
                selected_index = max(compatible, key=lambda r: (r.rule['Difficulty'], -r.index)).index
            out.insert(2, t.card('Event encounter', t.dropdown(
                [(str(r.index), r.label) for r in compatible], str(selected_index), on_select=changed),
                'The featured highest-star boss is selected by default; side encounters belong to this event.'))
        out.append(t.card('Recommendation and strategy', ft.Column([
            t.secondary_button('Restore suggested build', lambda e: (request(view, force=True), refresh(view))),
            t.text(getattr(view, '_teraloop_note', 'Choose an event to load its recommendation.'),
                   12, t.MUTED, selectable=True),
        ], spacing=8), 'The build is a default, not scripted host AI. The host leaves the battle.'))
        return out

    def set_value(view, field, value, rebuild=False):
        original_set(view, field, value, rebuild)
        if view.tool.key == TOOL_KEY and field.key in ('--event-key', '--version'):
            view.values.pop('--encounter', None)
            view.extra.pop('--encounter', None)
            view._teraloop_rows = ()
            request(view, force=True)
            refresh(view)

    def selected(view, game, chosen, update=True):
        if chosen.key == TOOL_KEY:
            stored = view.app.settings.tool_values.get(TOOL_KEY, {}).get('values', {})
            offer = stored.get('--pokemon')
            if isinstance(offer, dict) and isinstance(offer.get('species'), str) and offer.get('species_id'):
                offer['species_name'], offer['species'] = offer['species'], offer['species_id']
        original_select(view, game, chosen, update)
        request(view)

    games.GamesView.basic_cards, games.GamesView.set_value, games.GamesView.select = cards, set_value, selected
    return tool
