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

def to_fraction(amount):
    numer, denom = float(amount).as_integer_ratio()
    if denom == 1:
        return numer
    whole = numer / denom
    numer = numer % denom
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, denom)

# units, yo
ML_PER_OZ           =  29.5735
ML_PER_OZ_ROUNDED   =  30.0
ML_PER_TSP          =  4.92892
ML_PER_TSP_ROUNDED  =  5.0
ML_PER_DS           =  0.92
ML_PER_CL           =  10.0
OZ_PER_TSP          =  0.125    # 1/8 oz
OZ_PER_DS           =  0.03125  # 1/32 oz

def convert_units(amount, from_unit, to_unit, rounded=False):
    amount = float(amount)
    if from_unit == to_unit:
        return amount
    if to_unit in ['ds', 'dash', 'dashes']:
        to_unit = 'ds'
    unit_conversions = {
            'ds': dash_to_volume,
            'tsp': tsp_to_volume,
            'mL': mL_to_volume,
            'cL': cL_to_volume,
            'oz': oz_to_volume,
            }
    convert = unit_conversions.get(from_unit, lambda x,y,z: no_conversion(from_unit, to_unit))
    return convert(amount, to_unit, rounded)

def no_conversion(from_unit, to_unit):
    raise NotImplementedError("conversion from {} to {}".format(from_unit, to_unit))

def dash_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    if unit == 'mL':
        return ds * ML_PER_DS
    elif unit == 'oz':
        return ds / mL_per_oz
    else:
        no_conversion('dash', unit)

def tsp_to_volume(amount, unit, rounded=False):
    mL_per_tsp = ML_PER_TSP if not rounded else ML_PER_TSP_ROUNDED
    if unit == 'oz':
        return amount * OZ_PER_TSP
    elif unit == 'mL':
        return amount * mL_per_tsp
    elif unit == 'cL':
        return amount * mL_per_tsp / ML_PER_CL
    else:
        no_conversion('tsp', unit)

def oz_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    if unit == 'mL':
        return amount * mL_per_oz
    elif unit == 'cL':
        return amount * mL_per_oz / ML_PER_CL
    elif unit == 'tsp':
        return amount / OZ_PER_TSP
    elif unit == 'ds':
        return amount / OZ_PER_DS
    else:
        no_conversion('oz', unit)

def mL_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    mL_per_tsp = ML_PER_TSP if not rounded else ML_PER_TSP_ROUNDED
    if unit == 'oz':
        return amount / mL_per_oz
    elif unit == 'cL':
        return amount / ML_PER_CL
    elif unit == 'ds':
        return amount / ML_PER_DS
    elif unit == 'tsp':
        return amount / mL_per_tsp
    else:
        no_conversion('mL', unit)

def cL_to_volume(amount, unit, rounded=False):
    try:
        return mL_to_volume(amount, unit, rounded) / ML_PER_CL
    except NotImplementedError:
        no_conversion('cL', unit)

