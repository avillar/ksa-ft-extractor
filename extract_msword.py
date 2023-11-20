import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from openpyxl import Workbook

for fn in sys.argv[1:]:
    print(f"Processing {fn}... ", end='')

    with open(fn, 'r') as f:
        soup = BeautifulSoup(f, 'html.parser')

    cs_name = re.sub(r'\s*FTDS$', '', Path(fn).stem)
    cs_id = cs_name.replace(' ', '')
    cs_description = ''
    for h2 in soup.find_all('h2'):
        h2_title = re.sub(r'\s+', ' ', h2.get_text()).strip()
        title_match = re.match(r'([\d. ]+)(Foundation Theme Description)', h2_title, flags=re.IGNORECASE)
        if not title_match:
            continue
        for elem in h2.next_siblings:
            if not isinstance(elem, Tag):
                continue
            if elem.name in ('h2', 'h3'):
                break
            cs_description += '\n' + re.sub(r'\s+', ' ', elem.get_text())
    cs_description = cs_description.strip()
    concept_scheme = {
        'id': cs_id,
        'name': f"{cs_name} feature types",
        'definition': cs_description,
    }

    wb = Workbook()
    ws = wb.active
    ws.append(['id', 'label', 'definition', 'superclasses'])
    superclasses_found = False
    feature_types = []
    for h3 in soup.find_all('h3'):
        h3_title = re.sub(r'\s+', ' ', h3.get_text()).strip()
        title_match = re.match(r'([\d.]+)(Feature Type) (.*)', h3_title)
        if not title_match:
            continue

        feature_id = title_match.group(3)

        # feature_id = title[len('Feature Type '):]
        feature_type = {
            'id': feature_id,
            'name': re.sub(r'\s+', ' ', re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', feature_id))).strip(),
            'definition': '',
            'superclasses': [],
        }
        feature_types.append(feature_type)

        state = 'start'  # definition, superclasses, attributes
        for elem in h3.next_siblings:
            if not isinstance(elem, Tag):
                continue
            if elem.name == 'h4':
                if state == 'start':
                    state = 'definition'
                elif state == 'definition':
                    state = 'superclasses'
                elif state == 'superclasses':
                    state = 'attributes'
                else:
                    break
            elif elem.name == 'h3':
                break
            elif state == 'definition':
                feature_type['definition'] += '\n' + re.sub(r'\s+', ' ', elem.get_text())
            elif state == 'superclasses':
                if not re.sub(r'\s+', ' ', elem.get_text()).strip().lower().startswith('this feature type'):
                    feature_type['superclasses'].extend(x.strip() for x in elem.get_text().split('\n') if x.strip())

            feature_type['definition'] = feature_type['definition'].strip()

        if feature_type['superclasses']:
            superclasses_found = True

        ws.append([feature_id, feature_type['name'],
                   feature_type['definition'], '\n'.join(feature_type['superclasses'])])

    wb.save(Path(fn).with_suffix('.xlsx'))
    concept_scheme['concepts'] = feature_types
    with open(Path(fn).with_suffix('.json'), 'w') as outf:
        json.dump(concept_scheme, outf, indent=2)
    if not feature_types:
        print("NO FEATURE TYPES FOUND")
    elif not superclasses_found:
        print("NO SUPERCLASSES FOUND")
    else:
        print("ok")
