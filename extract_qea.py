from __future__ import annotations

import json
import re
import sqlite3
import sys
import logging
from collections import deque
from pathlib import Path
from sqlite3 import Cursor, Connection

from rdflib import URIRef, Graph, Namespace, RDF, SKOS, OWL, RDFS, Literal, XSD, Variable

import queries

FT = Namespace('https://w3id.org/ksa/feature-types/')
HAS_PROPERTY = URIRef('http://www.opengis.net/def/metamodel/featuretypes/hasProperty')
DATATYPE_TYPES = {
    'Boolean': XSD.boolean,
    'Date': XSD.date,
    'DateTime': XSD.dateTime,
    'DateType': XSD.date,
    'Decimal': XSD.decimal,
    'Real': XSD.double,
    'Integer': XSD.integer,
    'PT_FreeText': XSD.string,
}
INVALID_RANGES_QUERY = '''
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
SELECT DISTINCT ?r WHERE {
  ?s rdfs:range ?r
  FILTER(STRSTARTS(STR(?r), 'https://w3id.org/ksa/feature-types/'))
  FILTER NOT EXISTS {?r ?p ?o}
}
'''

logger = logging.getLogger('extract')


def add_codelists(cur: Cursor, pkg_id: int, g: Graph, concept_scheme: URIRef):
    broader = None
    for row in cur.execute(queries.CODELISTS_QUERY.replace('$PKG_ID$', str(pkg_id))):
        if not broader:
            broader = URIRef(f"{concept_scheme}/codeLists")
            g.add((broader, RDF.type, SKOS.Concept))
            g.add((broader, RDF.type, OWL.Class))
            g.add((broader, SKOS.inScheme, concept_scheme))
            g.add((broader, RDFS.label, Literal(f"{g.value(concept_scheme, RDFS.label)} code list or type", 'en')))

        cl_id = FT[row['name']]
        g.add((cl_id, RDF.type, SKOS.Concept))
        g.add((cl_id, RDF.type, OWL.Class))
        g.add((cl_id, SKOS.inScheme, concept_scheme))
        g.add((cl_id, SKOS.broader, broader))
        g.add((cl_id, RDFS.label, Literal(row['label'], 'en')))
        if row['description']:
            g.add((cl_id, SKOS.definition, Literal(row['description'].strip().replace('\r', ''), 'en')))


def add_attributes(cur: Cursor, object_id, g: Graph, concept_scheme: URIRef, ft: URIRef):
    att_broader = None

    def create_att_broader():
        if not att_broader:
            ab = URIRef(f"{concept_scheme}/attribute")
            g.add((ab, RDF.type, SKOS.Concept))
            g.add((ab, RDF.type, OWL.Class))
            g.add((ab, SKOS.inScheme, concept_scheme))
            g.add((ab, RDFS.label, Literal(f"{g.value(concept_scheme, RDFS.label)} attribute", 'en')))
            return ab
        return att_broader

    for row in cur.execute(queries.ASSOC_QUERY.replace('$OBJ_ID$', str(object_id))):
        obj_id = FT[row['obj_name']]
        g.add((obj_id, RDF.type, SKOS.Concept))
        g.add((obj_id, RDF.type, OWL.Class))
        g.add((obj_id, RDFS.label, Literal(row['obj_label'], 'en')))
        if row['obj_notes']:
            g.add((obj_id, SKOS.definition, Literal(row['obj_notes'].strip().replace('\r', ''), 'en')))

        if row['obj_role']:
            att_broader = create_att_broader()
            att_id = URIRef(f"{att_broader}/{re.sub(r'[^a-zA-Z0-9_-]+', '', row['obj_role'])}")
            g.add((att_id, RDF.type, SKOS.Concept))
            g.add((att_id, RDFS.subClassOf, att_broader))
            g.add((att_id, SKOS.broader, att_broader))
            g.add((att_id, RDF.type, OWL.ObjectProperty))
            g.add((att_id, RDFS.label, Literal(row['obj_role'])))
            g.add((att_id, RDFS.domain, ft))
            g.add((att_id, RDFS.range, obj_id))

    for row in cur.execute(queries.ATTR_QUERY.replace('$OBJ_ID$', str(object_id))):
        att_broader = create_att_broader()
        att_id = URIRef(f"{att_broader}/{re.sub(r'[^a-zA-Z0-9_-]+', '', row['Name'])}")
        g.add((att_id, RDF.type, SKOS.Concept))
        if row['Type'] in DATATYPE_TYPES:
            g.add((att_id, RDF.type, OWL.DatatypeProperty))
            g.add((att_id, RDFS.range, DATATYPE_TYPES[row['Type']]))
        else:
            g.add((att_id, RDF.type, OWL.ObjectProperty))
            if row['Type'] not in ('URI',):
                g.add((att_id, RDFS.range, FT[row['Type']]))
        g.add((att_id, SKOS.inScheme, concept_scheme))
        g.add((att_id, RDFS.label, Literal(row['Name'], 'en')))
        g.add((att_id, RDFS.subClassOf, att_broader))
        g.add((att_id, SKOS.broader, att_broader))
        g.add((att_id, RDFS.domain, ft))
        g.add((ft, HAS_PROPERTY, att_id))
        if row['Notes']:
            g.add((att_id, SKOS.definition, Literal(row['Notes'].strip().replace('\r', ''), 'en')))


def add_feature_types(cur: Cursor, pkg_id: int, g: Graph, concept_scheme: URIRef):
    for row in cur.execute(queries.CLS_QUERY.replace('$PKG_ID$', str(pkg_id))):
        ft_localpart = re.sub(r'[^a-zA-Z0-9_-]+', '', row['name'])
        ft_id = FT[ft_localpart]
        g.add((ft_id, RDF.type, SKOS.Concept))
        g.add((ft_id, RDF.type, OWL.Class))
        g.add((ft_id, SKOS.inScheme, concept_scheme))
        g.add((ft_id, RDFS.label, Literal(row['label'], 'en')))
        if row['description']:
            g.add((ft_id, SKOS.definition, Literal(row['description'].strip().replace('\r', ''), 'en')))

        if row['super_name']:
            super_id = FT[re.sub(r'[^a-zA-Z0-9_-]+', '', row['super_name'])]
            g.add((ft_id, SKOS.broader, super_id))
            g.add((ft_id, RDFS.subClassOf, super_id))

        add_attributes(cur, row['object_id'], g, concept_scheme, ft_id)


def add_foundation_theme(row, con: Connection, theme_descriptions: dict | None) -> tuple[URIRef, Graph]:
    logger.info('Reading Foundation Theme %s (%s)', row['Package_ID'], row['Name'])
    g = Graph()
    g.bind('ksa-ft', FT)
    g.bind('ogc-ft', 'http://www.opengis.net/def/metamodel/featuretypes/')
    theme_localpart = re.sub('FoundationTheme$', '', re.sub(r'[^a-zA-Z0-9_-]+', '', row['Name']))
    theme_id = FT[theme_localpart]
    g.add((theme_id, RDF.type, SKOS.ConceptScheme))
    g.add((theme_id, RDF.type, OWL.Class))
    g.add((theme_id, RDFS.label, Literal(row['Name'], 'en')))
    description = theme_descriptions.get(theme_localpart)
    if description:
        g.add((theme_id, SKOS.definition, Literal(description, 'en')))

    cur = con.cursor()

    pending_pkgs = deque((row['Package_ID'],))
    while pending_pkgs:
        pkg_id = pending_pkgs.popleft()
        add_feature_types(cur, pkg_id, g, theme_id)
        add_codelists(cur, pkg_id, g, theme_id)
        pending_pkgs.extend(x['Package_ID']
                            for x in cur.execute(queries.THEME_CHILDREN_QUERY.replace('$ID$', str(pkg_id))))

    return theme_id, g


def _main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <FILE.qea>", file=sys.stderr)
        sys.exit(-1)

    theme_descriptions = {}
    if len(sys.argv) > 2:
        for json_fn in sys.argv[2:]:
            with open(json_fn) as f:
                j = json.load(f)
                theme_descriptions[j['id']] = j['definition']

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')

    uri = Path(sys.argv[1]).resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as con:
        out = Path('out')
        out.mkdir(parents=True, exist_ok=True)

        full_graph = Graph()

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        theme_graphs: dict[URIRef, Graph] = {}
        for row in cur.execute(queries.THEME_CHILDREN_QUERY.replace('$ID$', str(queries.ROOT_FTHEME_ID))):
            theme_id, g = add_foundation_theme(row, con, theme_descriptions)
            theme_graphs[theme_id] = g
            for t in g:
                full_graph.add(t)

        # Remove unknown ranges
        for b in full_graph.query(INVALID_RANGES_QUERY).bindings:
            r = b.get(Variable('r'))
            logger.info('Removing invalid range %s', str(r))
            for g in theme_graphs.values():
                g.remove((None, RDFS.range, r))

        for theme_id, g in theme_graphs.items():
            output_fn = out.joinpath(str(theme_id).replace(FT, '')).with_suffix('.ttl')
            g.serialize(output_fn)
            logger.info('Output file %s created', output_fn)


if __name__ == '__main__':
    _main()

