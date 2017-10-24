""" Miscallanious util funcitons for the mix-mind project
"""

from functools import wraps
import inspect

def default_initializer(func):
    names, varargs, keywords, defaults = inspect.getargspec(func)
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        for name, arg in list(zip(names[1:], args)) + list(kwargs.items()):
            setattr(self, name, arg)
        func(self, *args, **kwargs)
    return wrapper

def get_fraction(amount):
    numer, denom = float(amount).as_integer_ratio()
    if denom == 1:
        return numer
    whole = numer / denom
    numer = numer % denom
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, denom)
