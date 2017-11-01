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

recipes = OrderedDict()

page = requests.get(url)
tree = html.fromstring(page.content)
items = tree.findall(".//div[@class='blog_list_item_lists']")
for item in items:
    name = item.find(".//h3").text
    name = ' '.join([word.capitalize() for word in name.split()])
    body = item.find(".//div[@class='blog_text']")
    recipes[name] = {'unit': 'cL'}
    children = [c for c in body.iterchildren()]

    assert children[1].tag == 'p'
    recipes[name]['style'] = children[1].text

    assert children[2].tag == 'ul'
    recipes[name]['ingredients'] = OrderedDict()
    for ingredient in children[2].iterchildren():
        try:
            recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[2:]])] = float(ingredient.text.split()[0])
        except ValueError:
            recipes[name]['ingredients'][' '.join([w.lower() for w in ingredient.text.split()[2:]])] = ingredient.text.split()[0]

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

    print name





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

