"""Local-only keys setup with a visible success/failure result.

Browser previews cannot obtain a Windows file path from FilePicker. Never
upload keys to work around that restriction; accept a local path instead.
"""
import os


def install(gui):
    import flet as ft
    from gui import theme as t
    from gui.app import keys_found

    def welcome(app):
        web = bool(os.environ.get('POKELDN_GUI_WEB'))
        path = t.field(value=app.settings.keys or '', mono=True,
                       hint='C:\\path\\to\\prod.keys')
        status = t.text('No keys selected yet.', 12, t.MUTED)

        def close(e):
            app.page.pop_dialog()

        def use(e=None):
            value = os.path.expanduser((path.value or '').strip().strip('"'))
            if not keys_found(value):
                status.value = 'File not found. Enter the full local path to your prod.keys.'
                status.update()
                return
            app.settings.keys = value
            app.settings.save()
            app.page.pop_dialog()
            app.page.show_dialog(ft.SnackBar(ft.Text('Switch keys selected successfully — stored locally.')))

        async def browse(e):
            files = await app.picker.pick_files(file_type=ft.FilePickerFileType.ANY)
            if not files:
                return
            value = files[0].path
            if not value:
                status.value = 'This preview cannot read a local file path. Paste the full path below; no upload is used.'
                status.update()
                return
            path.value = value
            path.update()
            use()

        app.page.show_dialog(t.dialog(
            modal=True, semantics_label='TeraLoop local keys setup',
            title=t.text('Select your Switch keys', 20),
            content=ft.Container(ft.Column([
                t.text('Keys stay on this computer and are never included in the release.', 13, t.MUTED),
                t.text('Browser preview: paste the full Windows path. File upload is intentionally disabled.'
                       if web else 'Choose your file, or enter its full local path.', 12, t.MUTED),
                path, status,
            ], tight=True, spacing=12), width=520),
            actions=[t.secondary_button('Set up later', close),
                     t.secondary_button('Browse…', browse, disabled=web),
                     t.button('Use this file', use)]))

    gui.welcome = welcome
