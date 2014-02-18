
import re
import json
import os.path

import sublime
import sublime_plugin

try:
    from Utils.packages import find_all_packages
    from Utils.touch import add_event_handler_async
except ImportError:
    try:
        # Allow for repository name
        from sublime_utils.packages import find_all_packages
        from sublime_utils.touch import add_event_handler_async
    except ImportError:
        print('[ColorSchemes] Please install the sublime_utils plugin (Utils) also.')
        print('It can be found here: https://github.com/sligodave/sublime_utils/')
        find_all_packages = add_event_handler_async = None


COLOR_SCHEMES_INSTANCE = None


base_tmTheme = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>name</key><string>Color Schemes Theme</string>
<key>settings</key><array><dict><key>settings</key><dict><key>background</key>
<string>#ffffff</string><key>caret</key><string>#ffffff</string><key>foreground</key>
<string>#000000</string></dict></dict><dict><key>name</key><string>button</string>
<key>scope</key><string>button</string><key>settings</key><dict><key>background</key>
<string>#bbbbbb</string><key>foreground</key><string>#000000</string><key>caret</key>
<string>#bbbbbb</string></dict></dict>
<dict><key>name</key><string>horizontal_rule</string>
<key>scope</key><string>horizontal_rule</string><key>settings</key><dict><key>background</key>
<string>#cccccc</string><key>foreground</key><string>#cccccd</string><key>caret</key>
<string>#cccccc</string></dict></dict>%s</array><key>uuid</key>
<string>905FEC5A-2E43-934F-EC9C-A3982DFDED3F</string></dict></plist>"""

base_color = """<dict><key>name</key><string>%s</string><key>scope</key>
<string>%s</string><key>settings</key><dict><key>background</key>
<string>%s</string><key>foreground</key><string>%s</string>
<key>caret</key><string>%s</string></dict></dict>"""


class ColorSchemes:
    def __init__(self, window):
        global COLOR_SCHEMES_INSTANCE
        self.view = window.new_file()
        self.change_layout()
        self.get_color_scheme()
        self.update_view()
        COLOR_SCHEMES_INSTANCE = self

    def update_view(self):
        data = '\n Close and Revert Layout \n Restore Color Scheme \n\n'

        color_schemes = []
        regions = []
        package_and_file_names = []
        packages = find_all_packages(contents=True, extensions='.tmTheme')
        for package_name, package in packages.items():
            for file_name in package['files']:
                if not file_name.endswith('.tmTheme') or file_name == 'color_schemes.tmTheme':
                    continue

                content = package['contents'][file_name]
                start = re.search('<dict>\s*<key>settings</key>', content)
                if start:
                    start = start.start()
                    background_color = '#bbbbbb'
                    background = re.search(
                        '<key>background</key>\s*<string>([^<]+)</string>', content[start:])
                    if background:
                        background_color = background.group(1)
                        if background_color.lower() == '#ffffff':
                            background_color = '#fffffe'
                    foreground_color = '#000000'
                    foreground = re.search(
                        '<key>foreground</key>\s*<string>([^<]+)</string>', content[start:])
                    if foreground:
                        foreground_color = foreground.group(1)
                    caret_color = '#bbbbbb'
                    caret = re.search(
                        '<key>caret</key>\s*<string>([^<]+)</string>', content[start:])
                    if caret:
                        caret_color = caret.group(1)
                    color_schemes.append(
                        base_color % (
                            file_name[:-8],
                            file_name[:-8],
                            background_color,
                            foreground_color,
                            caret_color
                        )
                    )
                package_and_file_names.append([package_name, file_name])

        package_and_file_names.sort(key=lambda x: x[1][:-8].title())

        for package_name, file_name in package_and_file_names:
            def handler(package_name, file_name):
                def handler(view, region, point):
                    with open(self.user_prefs_path, 'r') as user_prefs_file:
                        user_prefs = json.load(user_prefs_file)
                    user_prefs['color_scheme'] = 'Packages/%s/%s' % (
                        package_name, file_name)
                    with open(self.user_prefs_path, 'w') as user_prefs_file:
                        json.dump(user_prefs, user_prefs_file, indent='\t')
                return handler
            handler = handler(package_name, file_name)

            text = ' %s \n' % (file_name[:-8].title())
            regions.append(
                [
                    text.strip(),
                    [sublime.Region(len(data), len(data) + len(text) - 1)],
                    file_name[:-8],
                    '',
                    sublime.DRAW_NO_OUTLINE,
                    handler,
                ]
            )
            data += text

        ######################################################
        # Set up view
        ######################################################

        color_scheme = base_tmTheme % ''.join(color_schemes)
        color_scheme_path = os.path.join(sublime.packages_path(), 'User', 'color_schemes.tmTheme')
        with open(color_scheme_path, 'w') as color_scheme_file:
            color_scheme_file.write(color_scheme)

        self.view.set_name('Color Schemes')
        self.view.set_read_only(True)
        self.view.set_scratch(True)
        settings = {
            'rulers': [],
            'highlight_line': False,
            'fade_fold_buttons': True,
            'caret_style': 'solid',
            'line_numbers': False,
            'draw_white_space': 'none',
            'gutter': False,
            'word_wrap': False,
            'indent_guide_options': [],
            'line_padding_top': 5,
            'line_padding_bottom': 5,
            'draw_centered': True,
            'color_scheme': 'Packages/User/color_schemes.tmTheme',
        }
        for name, value in settings.items():
            self.view.settings().set(name, value)
        self.view.run_command(
            'utils_edit_view',
            {
                'start': 0,
                'data': data
            }
        )
        for region in regions:
            self.view.add_regions(*region[:5])
            add_event_handler_async(self.view, region[1][0], region[5])
        region1 = sublime.Region(1, 26)
        region2 = sublime.Region(27, 49)
        add_event_handler_async(self.view, region1, lambda x, y, z: self.close())
        add_event_handler_async(self.view, region2, lambda x, y, z: self.restore_color_scheme())
        self.view.add_regions('buttons', [region1, region2], 'button', '', sublime.DRAW_OUTLINED)
        self.view.add_regions('test', [sublime.Region(0, self.view.size())])

    def close(self):
        global COLOR_SCHEMES_INSTANCE
        COLOR_SCHEMES_INSTANCE = None
        window = self.view.window()
        window.set_layout(self.orig_layout)
        for g, views in enumerate(self.views_in_groups):
            for view in views:
                window.focus_view(view)
                window.run_command('move_to_group', args={'group': g})
            window.focus_view(self.active_views[g])
        window.focus_view(self.view)
        window.run_command('close')
        window.focus_view(self.active_view)

    def change_layout(self):
        window = self.view.window()
        self.active_view = window.active_view()
        self.orig_layout = window.get_layout()
        self.active_views = []
        self.views_in_groups = []
        for group in range(window.num_groups()):
            self.views_in_groups.append(window.views_in_group(group))
            self.active_views.append(window.active_view_in_group(group))
        window.set_layout({
            "cols": [0.0, 0.8, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
            })

        window.run_command('move_to_group', args={'group': 1})

    def restore_color_scheme(self):
        if self.orig_color_scheme:
            with open(self.user_prefs_path, 'r') as user_prefs_file:
                user_prefs = json.load(user_prefs_file)
            user_prefs['color_scheme'] = self.orig_color_scheme
            with open(self.user_prefs_path, 'w') as user_prefs_file:
                json.dump(user_prefs, user_prefs_file, indent='\t')

    def get_color_scheme(self):
        self.user_prefs_path = os.path.join(
            sublime.packages_path(), 'User', 'Preferences.sublime-settings')
        if not os.path.exists(self.user_prefs_path):
            open(self.user_prefs_path, 'w').write('{}')
        self.orig_color_scheme = self.view.settings().get('color_scheme', None)


class BaseColorSchemesCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        if add_event_handler_async is None:
            return False
        return True

    is_visible = is_enabled


class ColorSchemesCloseCommand(BaseColorSchemesCommand):
    """
    window.run_command('color_schemes_close')
    """
    def run(self):
        if COLOR_SCHEMES_INSTANCE:
            COLOR_SCHEMES_INSTANCE.close()


class ColorSchemesOpenCommand(BaseColorSchemesCommand):
    """
    window.run_command('color_schemes_open')
    """
    def run(self):
        ColorSchemes(self.window)


class ColorSchemesToggleCommand(BaseColorSchemesCommand):
    """
    window.run_command('color_schemes_toggle')
    """
    def run(self):
        if COLOR_SCHEMES_INSTANCE:
            self.window.run_command('color_schemes_close')
        else:
            self.window.run_command('color_schemes_open')
