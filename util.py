""" Miscallanious util funcitons for the mix-mind project
"""

from functools import wraps
from fractions import Fraction
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
    fraction = Fraction.from_float(float(amount)).limit_denominator(99)
    if fraction.denominator == 1:
        return fraction.numerator
    whole = fraction.numerator / fraction.denominator
    numer = fraction.numerator % fraction.denominator
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, fraction.denominator)

def calculate_std_drinks(proof, amount, unit):
    """ Standard drink is 1.5 oz or 45 ml at 80 proof
    """
    adjusted_proof = proof / 80.0
    adjusted_amount = convert_units(amount, unit, 'oz')
    return adjusted_proof * adjusted_amount


# units, yo
ML_PER_OZ           =  29.5735
ML_PER_OZ_ROUNDED   =  30.0
ML_PER_TSP          =  4.92892
ML_PER_TSP_ROUNDED  =  5.0
ML_PER_DS           =  0.92
ML_PER_CL           =  10.0
ML_PER_DROP         =  0.12
OZ_PER_TSP          =  1.0/8.0
OZ_PER_DS           =  1.0/32.0
OZ_PER_DROP         =  1.0/240.0

def convert_units(amount, from_unit, to_unit, rounded=False):
    if from_unit == 'literal':
        return amount
    amount = float(amount)
    if from_unit == to_unit:
        return amount
    unit_conversions = {
            'ds': dash_to_volume,
            'tsp': tsp_to_volume,
            'mL': mL_to_volume,
            'cL': cL_to_volume,
            'oz': oz_to_volume,
            'drop': drop_to_volume,
            }
    convert = unit_conversions.get(from_unit, lambda x,y,z: no_conversion(from_unit, to_unit))
    return convert(amount, to_unit, rounded)

def no_conversion(from_unit, to_unit):
    raise NotImplementedError("conversion from {} to {}".format(from_unit, to_unit))

def dash_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    if unit == 'mL':
        return amount * ML_PER_DS
    elif unit == 'oz':
        return amount / mL_per_oz
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
    elif unit == 'drop':
        return amount / OZ_PER_DROP
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
    elif unit == 'drop':
        return amount / ML_PER_DROP
    else:
        no_conversion('mL', unit)

def drop_to_volume(amount, unit, rounded=False):
    if unit == 'oz':
        return amount * OZ_PER_DROP
    elif unit == 'mL':
        return amount * ML_PER_DROP
    else:
        no_conversion('drop', unit)

def cL_to_volume(amount, unit, rounded=False):
    try:
        return mL_to_volume(amount, unit, rounded) / ML_PER_CL
    except NotImplementedError:
        no_conversion('cL', unit)

