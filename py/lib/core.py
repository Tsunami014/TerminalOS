from difflib import get_close_matches
from lib.API import App, Popup, StaticPos, RelativePos
import lib.widgets as wids
import os
import importlib
import requests
import re

__all__ = [
    'Help',
    'SoftwareManager',
]

PATH = os.path.abspath(os.path.join(os.getcwd(), __file__, '../', 'external'))

def loadExternals():
    if not os.path.exists(PATH):
        os.mkdir(PATH)
    for file in os.listdir(PATH):
        if file.endswith('.py'):
            ext = importlib.import_module('external.'+file[:-3])
            if hasattr(ext, 'load'):
                ext.load()
            else:
                Popup(wids.Text(StaticPos(0, 0), f"Couldn't load external {file[:-3]}\nDoes not have a load method."), duration=5)

class Help(App):
    NAME = 'Help'
    ADD_TO_LIST = True
    def __init__(self):
        super().__init__([
            wids.Text(RelativePos(0.5, 0), 'HELP'), 
            wids.Button(RelativePos(0.5, 0, force_y=1), 'Hello', lambda: Popup(wids.Text(StaticPos(0, 0), 'You pressed\nthe button!'))),
            wids.TextInput(RelativePos(0.5, 0, force_y=3), 50, 10)
        ])

class TerminalApp(App):
    NAME = 'Terminal App'
    cmd = ''
    def __init__(self):
        super().__init__([wids.Terminal(StaticPos(0, 0), self.cmd, 0, 0)])
    
    def onScreenUpdate(self):
        sze = self.Size()
        self.widgets[0].resize(sze[0]-2, sze[1]-2)
    
    def update(self, focus):
        return super().update(focus)

class Terminal(TerminalApp):
    NAME = 'Terminal'
    cmd = '/bin/sh'
    ADD_TO_LIST = True

class SoftwareManager(App):
    NAME = 'Software Manager'
    def init_widgets(self):
        return [
            wids.TextInput(RelativePos(0.5, -1, 0, 0), max_width=20, max_height=1, placeholder='Search...'),
            wids.Button(RelativePos(0.5, -1, 0, 3), 'SEARCH!', self.search),
            wids.Text(RelativePos(0.5, 0.3, 0, 1), 'Software Manager\nSearch above to find software to install!'),
        ]
    
    def main(self):
        self.widgets = self.init_widgets()
    
    def suggests(self, opts):
        maxSuggests = 5
        query = self.widgets[0].text.lower()
        suggests = [k for k in opts if k.startswith(query)]
        def order(suggests):
            seen = set()
            unique_list = []
            for item in suggests:
                if item not in seen:
                    unique_list.append(item)
                    seen.add(item)
            return unique_list
        if len(suggests) < maxSuggests:
            suggests.extend(get_close_matches(query, opts, n=maxSuggests, cutoff=0.4))
            suggests = order(suggests)
        if len(suggests) < maxSuggests:
            suggests.extend(filter(lambda k: query.startswith(k), opts))
            suggests = order(suggests)
        if len(suggests) < maxSuggests:
            suggests.extend(filter(lambda k: query in k, opts))
            suggests = order(suggests)
        return suggests[:maxSuggests]

    def install(self, name, fc):
        with open(f'{PATH}/{name}.py', 'w+') as f:
            f.write(fc)
        Popup(wids.Text(StaticPos(0, 0), 'Installed!'))
        self._info(name, fc)
    
    def remove(self, name, fc):
        os.remove(f'{PATH}/{name}.py')
        Popup(wids.Text(StaticPos(0, 0), 'Removed!'))
        self._info(name, fc)
    
    def _info(self, name, text):
        txt = text.lstrip()
        if txt.startswith('"""'):
            idx = txt.find('"""', 3)
            data = [i.split(': ') for i in txt[3:idx].split('\n') if i]
            fields = {i[0].strip(): ': '.join(i[1:]) for i in data if len(i) >= 2}
        else:
            fields = {}
        if 'Name' not in fields:
            fields['Name'] = name
        endFields = {}
        keys = (
            'Author', 'Email', 'Version', 'License'
        )
        for key in keys:
            if key not in fields:
                endFields[key] = 'N/A'
            else:
                endFields[key] = fields[key]
        self.widgets = self.widgets[:2]
        self.widgets.extend([
            wids.Button(StaticPos(0, 0), '<', self.search),
            wids.Text(RelativePos(0.5, -1, 0, 7), 
                        f'\033[1m{fields["Name"]}\033[0m\n\033[3m{fields["Description"] if 'Description' in fields else ""}\033[23m\n\n'+\
                        '\n'.join(f'{k}: {v}' for k, v in endFields.items())
            )
        ])

        if os.path.exists(f'{PATH}/{name}.py'):
            self.widgets.append(wids.Button(RelativePos(0.5, -1, 0, 12+len(keys)), 'Remove', lambda: self.remove(name, txt)))
        else:
            self.widgets.append(wids.Button(RelativePos(0.5, -1, 0, 12+len(keys)), 'Install', lambda: self.install(name, txt)))

    def info(self, name):
        try:
            request = requests.get(f'https://raw.githubusercontent.com/Tsunami014/TerminalOSApps/refs/heads/main/{name}.py')
        except ConnectionError as e:
            Popup(wids.Text(StaticPos(0, 0), f'{type(e).__qualname__}: failed to fetch data!\nReason: {str(e)}', max_width=40), duration=10)
            return
        if request.status_code == 200:
            self._info(name, request.text)
        else:
            Popup(wids.Text(StaticPos(0, 0), f'Failed to fetch data!\nStatus code: {request.status_code}\nReason: {request.reason}'), duration=10)
    
    def search(self):
        try:
            request = requests.get('https://raw.githubusercontent.com/Tsunami014/TerminalOSApps/refs/heads/main/README.md')
        except Exception as e:
            Popup(wids.Text(StaticPos(0, 0), f'{type(e).__qualname__}: failed to fetch data!\nReason: {str(e)}', max_width=40), duration=10)
            return
        if request.status_code == 200:
            txt = request.text
            idx = txt.find('\n# Apps list')+len('\n# Apps list\n')
            data = txt[idx:txt.find('##', idx)]
            names = re.findall(r'- \[([^[]+)]', data)
            lowerednms = [name.lower() for name in names]
            suggests = self.suggests(lowerednms)
            self.widgets = self.widgets[:2]
            self.widgets.append(wids.Button(StaticPos(0, 0), '<', self.main))
            if suggests:
                for idx, name in enumerate(suggests):
                    realname = names[lowerednms.index(name)]
                    self.widgets.append(wids.Button(RelativePos(0.5, -1, 0, 7+idx*3), realname, lambda name=realname: self.info(name)))
            else:
                Popup(wids.Text(StaticPos(0, 0), 'No results found!\nTry a different search term.'), duration=10)
        else:
            Popup(wids.Text(StaticPos(0, 0), f'Failed to fetch data!\nStatus code: {request.status_code}\nReason: {request.reason}'), duration=10)
            self.main()
