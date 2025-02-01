from API import BarElm, ClickBarElm
import os
import time

__all__ = [
    'BarApp'
]

class BarApp(ClickBarElm):
    BarNum = 7
    def __init__(self, app):
        self.callback = app
        self.appname = f'┤{app.__qualname__}├'
    
    def _draw(self):
        return self.appname

class BarCmd(BarElm):
    """
    Runs a command in the terminal periodically and displays the result.

    ## Sample commands:
     - `timedatectl | grep -P -o '(?<=Local time: )[a-zA-Z]+?[ \-0-9:]+'`: For telling the time
    
    ## BarNum
    The bar number to attach to.

    ```
     111 222 
    3       4
    3       4

    5       6
    5       6
     777 888 
    ```
    """
    def __init__(self, barnum, cmd, update_freq = None):
        self.BarNum = barnum
        self.cmd = cmd
        self.last_res = None
        self.update_freq = update_freq
        self.last_updated = time.time()
    
    def _draw(self):
        if self.last_res is None or self.update_freq is None or time.time()-self.last_updated > self.update_freq:
            self.last_res = os.popen(self.cmd).read().strip()
        return self.last_res
