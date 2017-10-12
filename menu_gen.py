#!/usr/bin/env python
"""
Turn recipes json into a readable menu
"""

import argparse
import json
from collections import OrderedDict

def get_fraction(amount):
    numer, denom = float(amount).as_integer_ratio()
    if denom == 1:
        return numer
    whole = numer / denom
    numer = numer % denom
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, denom)

def convert_to_menu(recipes):
    """
    """

    drinks_text = []
    for drink_name, ingredients in recipes.iteritems():
        lines = []
        lines.append(drink_name)
        unit = ingredients.get('unit', 'oz')
        for ingredient, amount in ingredients.iteritems():
            if ingredient == "garnish":
                continue
            elif ingredient == "optional":
                continue
            elif ingredient == "unit":
                continue

            if isinstance(amount, basestring):
                amount_str = amount
            elif unit == 'oz':
                amount_str = get_fraction(amount)
            else:
                amount_str = str(amount)

            lines.append("\t{} {} {}".format(amount_str, unit, ingredient))

        garnish = ingredients.get('garnish')
        if garnish:
            lines.append("\t{}, for garnish".format(garnish))

        print '\n'.join(lines)



def get_parser():
    p = argparse.ArgumentParser(description="""
Example usage:
    ./program -v -d
""", formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('-v', dest='verbose', action='store_true')

    return p

def main():

    args = get_parser().parse_args()

    with open('recipes.json') as fp:
        convert_to_menu(json.load(fp, object_pairs_hook=OrderedDict))


if __name__ == "__main__":
    main()
