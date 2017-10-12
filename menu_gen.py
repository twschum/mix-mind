#!/usr/bin/env python
"""
Turn recipes json into a readable menu
"""

import argparse
import json

def get_fraction(amount):
    import ipdb; ipdb.set_trace()
    return amount

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
            if unit == 'oz':
                amount_str = get_fraction(amount)
            else:
                amount_str = str(amount)

            lines.append("\t{} {} {}".format(amount_str, unit, ingredient))
        garnish = ingredients.get('garnish')
        if garnish:
            lines.append("{}, for garnish".format(garnish))

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
        convert_to_menu(json.load(fp))


if __name__ == "__main__":
    main()
