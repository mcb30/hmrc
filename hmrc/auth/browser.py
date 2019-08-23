"""Interactive web browser authorization"""

import webbrowser

__all__ = [
    'browser_auth',
]


def browser_auth(uri, _state):
    """Obtain authorization token via browser

    The authorization code will be obtained by launching a web browser
    and waiting for the user to copy-paste the resulting authorization
    code into the terminal.
    """
    webbrowser.open(uri)
    code = input("Please enter the code obtained via the browser: ")
    return code
