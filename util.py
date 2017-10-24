""" Miscallanious util funcitons for the mix-mind project
"""

from functools import wraps
import inspect

def default_initializer(func):
    """
    Automatically assigns the parameters.
    >>> class process:
    ...     @initializer
    ...     def __init__(self, cmd, reachable=False, user='root'):
    ...         pass
    >>> p = process('halt', True)
    >>> p.cmd, p.reachable, p.user
    ('halt', True, 'root')
    """
    names, varargs, keywords, defaults = inspect.getargspec(func)
    @wraps(func)
    def wrapper(self, *args, **kargs):
        for name, arg in zip(names[1:], args) + kargs.items():
            setattr(self, name, arg)
        func(self, *args, **kargs)
    return wrapper
