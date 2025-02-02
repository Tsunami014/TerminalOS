from difflib import get_close_matches
from threading import Thread
from API import App, FullscreenApp, Popup, StaticPos, RelativePos
import widgets as wids
import os
import importlib
import requests
import re

__all__ = [
    'Help',
    'Test',
    'SoftwareManager',
]

def loadExternals():
    path = os.path.abspath(os.path.join(os.getcwd(), __file__, '../', 'external'))
    if not os.path.exists(path):
        os.mkdir(path)
    for file in os.listdir(path):
        if file.endswith('.py'):
            importlib.import_module(file[:-3], package='external')

class Help(App):
    def init_widgets(self):
        return [
            wids.Text(StaticPos(0, 0), 'HI!')
        ]

class Test(App):
    def init_widgets(self):
        return [
            wids.Text(StaticPos(0, 0), 'Hello, World!'), 
            wids.Button(StaticPos(0, 1), 'Click me!', lambda: Popup(wids.Text(StaticPos(0, 0), 'This is a popup!\nHi!'))),
            wids.TextInput(RelativePos(1, 0, len('Hello, World! '), 0), placeholder='Type here: ')
        ]

class SoftwareManager(FullscreenApp):
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
    
    def startSearch(self):
        t = Thread(target=self.search, daemon=True)
        t.start()
    
    def search(self):
        request = requests.get('https://tsunami014.github.io/TerminalOSApps/')
        if request.status_code == 200:
            txt = request.text
            idx = txt.find('Apps list')+len('Apps list</h1>\n<ul>\n')
            data = txt[idx:txt.find('</ul>', idx)]
            names = re.findall(r'<li><a href=[^>]+>([^<]+)', data)
            lowerednms = [name.lower() for name in names]
            suggests = self.suggests(lowerednms)
            self.widgets = self.widgets[:2]
            self.widgets.append(wids.Button(StaticPos(0, 0), '<', self.main))
            if suggests:
                for idx, name in enumerate(suggests):
                    realname = names[lowerednms.index(name)]
                    self.widgets.append(wids.Button(RelativePos(0.5, -1, 0, 7+idx), realname, lambda: Popup(wids.Text(StaticPos(0, 0), f'You clicked on {realname}!'))))
            else:
                Popup(wids.Text(StaticPos(0, 0), 'No results found!\nTry a different search term.'))
        else:
            Popup(wids.Text(StaticPos(0, 0), f'Failed to fetch data!\nStatus code: {request.status_code}\nReason: {request.reason}'))
            self.main()
