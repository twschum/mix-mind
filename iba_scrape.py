#! /usr/bin/env python

# scrape the IBA pages for cocktail lists

import sys

from lxml import html
import requests
from pprint import pprint
from collections import OrderedDict
import json

url = 'http://iba-world.com/iba-cocktails/'
jsonfile = 'IBA_unforgettables.json'


url = 'http://iba-world.com/contemporary-classics/'
jsonfile = 'IBA_contemporary_classics.json'

url = 'http://iba-world.com/new-era-drinks/'
jsonfile = 'IBA_new_era_drinks.json'

recipes = OrderedDict()

page = requests.get(url)
tree = html.fromstring(page.content)
items = tree.findall(".//div[@class='blog_list_item_lists']")
for item in items:
    name = item.find(".//h3").text
    name = ' '.join([word.capitalize() for word in name.split()])
    body = item.find(".//div[@class='blog_text']")
    recipes[name] = {'unit': 'cL'}
    print name
    children = [c for c in body.iterchildren()]

    assert children[1].tag == 'p'
    style = children[1].text
    if style is None:
        style = children[1].find('span').text
    recipes[name]['style'] = style

    recipes[name]['ingredients'] = OrderedDict()

    if not children[2].tag == 'ul':
        print "DO BY HAND: ", children[2].text

    else:
        for ingredient in children[2].iterchildren():
            if len(ingredient.text.split()) == 1:
                recipes[name]['ingredients'][ingredient.text.lower()] = ''
                continue
            unit = ingredient.text.split()[1].lower()
            if unit == 'cl':
                recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[2:]])] = float(ingredient.text.split()[0])
            elif unit == 'bar' or unit == 'to': # bar spoon
                recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[3:]])] = ' '.join(ingredient.text.split()[:3])
            elif unit == 'dashes' or unit == 'drops':
                recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[2:]])] = ' '.join(ingredient.text.split()[:2])
            elif unit == 'dash':
                recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[2:]])] = 'dash'
            else:
                print "using literal: ", ingredient.text
                literal = {'1': 'one', '2': 'two', 'A': 'one'}
                try:
                    recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[1:]])] = literal[ingredient.text.split()[0]]
                except:
                    recipes[name]['ingredients'][ingredient.text.lower()] = ''

    # Get full description from the link
    ref_url = item.find(".//a[@class='top_hover_image']").attrib.get('href')
    detail_page = requests.get(ref_url)
    detail_tree = html.fromstring(detail_page.content)
    use_next = False
    for child in detail_tree.find(".//div[@class='col-sm-9']").iterchildren():
        if use_next and child.tag == 'p':
            recipes[name]['IBA_description'] = child.text
            break
        if child.tag =='ul':
            use_next = True


with open(jsonfile, 'w') as fp:
    json.dump(recipes, fp, indent=4, separators=(',', ': '))
    print "Wrote out as {}".format(jsonfile)


sys.exit(0)
raw = sys.argv[1]
with open(raw) as fp:
    for line in fp.readlines():
        if line.lstrip().startswith(r'<h3>'):
            print line.lstrip()
        # super hax
        if line.startswith(r'<p>'):
            print line
        if line.startswith(r'<li>'):
            print line
        if not line.lstrip().startswith('<'):
            print line

