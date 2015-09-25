# Not found
# sub_national: True
# quality_confirmed: False

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab

""" CKAN Package management scripts """

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

import sys
import ckanutils as api
import itertools as it

from os import environ
from operator import itemgetter
from dateutil.parser import parse

from slugify import slugify
from manager import Manager
from ckanutils import CKAN

manager = Manager()

methodologies = {
    'census': 'Census',
    'registry': 'Registry',
    'survey': 'Sample Survey',
    'observed': 'Direct Observational Data/Anecdotal Data',
    'other': 'Other'
}


@manager.arg(
    'org_id', help='the organization id', nargs='?', default=sys.stdin)
@manager.arg('source', 's', help='Data source', default='Multiple sources')
@manager.arg('type', 'y', help='Package type', default='dataset')
@manager.arg('caveats', 'c', help='Package caveats')
@manager.arg('end', 'e', help='Data end date')
@manager.arg(
    'remote', 'r', help='the remote ckan url (uses `%s` ENV if available)' %
    api.REMOTE_ENV, default=environ.get(api.REMOTE_ENV))
@manager.arg(
    'api_key', 'k', help='the api key (uses `%s` ENV if available)' %
    api.API_KEY_ENV, default=environ.get(api.API_KEY_ENV))
@manager.arg(
    'ua', 'u', help='the user agent (uses `%s` ENV if available)' % api.UA_ENV,
    default=environ.get(api.UA_ENV, api.DEF_USER_AGENT))
@manager.arg('license_id', 'l', help='Data license')
@manager.arg('description', 'd', help='Dataset description')
@manager.arg(
    'methodology', 'm', help='Data collection methodology',
    default='Census', choices=methodologies.keys())
@manager.arg('title', 't', help='Package title', default='Untitled')
@manager.arg('tags', 'T', help='Comma separated list of tags')
@manager.arg('location', 'L', help='Location the data represents')
@manager.arg('start', 'S', help='Data start date')
@manager.arg(
    'quiet', 'q', help='suppress debug statements', type=bool, default=False)
@manager.command
def create(org_id, **kwargs):
    """Creates a package (aka dataset)"""
    verbose = not kwargs.get('quiet')
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}
    ckan = CKAN(**ckan_kwargs)

    licenses = it.imap(itemgetter('id'), ckan.license_list())
    organizations = it.imap(itemgetter('id'), ckan.organization_list())
    groups = it.imap(itemgetter('id'), ckan.group_list())

    title = kwargs.get('title')
    raw_tags = kwargs.get('tags')
    tags = [{'state': 'active', 'name': t} for t in raw_tags.split(',')]
    location = kwargs.get('location')
    methodology = kwargs.get('methodology')
    license_id = kwargs.get('license_id', 'cc-by-igo')
    raw_start = kwargs.get('start')
    raw_end = kwargs.get('end')

    if raw_start:
        start = parse(raw_start).strftime('%d/%m/%Y')
        end = parse(raw_end).strftime('%d/%m/%Y') if raw_end else ''

    extras = [
        {'methodology': methodologies[methodology]},
        {'methodology_other': 'Other' if methodology == 'other' else None},
        {'dataset_date': '%s-%s' % (start, end) if start else ''},
        {'dataset_source': kwargs.get('source')},
        {'caveats': kwargs.get('caveats')},
    ]

    if location and location not in list(groups):
        sys.exit('group name: %s not found!' % location)

    if org_id not in list(organizations):
        sys.exit('organization id: %s not found!' % org_id)

    if license_id not in list(licenses):
        sys.exit('license id: %s not found!' % license_id)

    package_kwargs = {
        'title': title,
        'name': kwargs.get('name', slugify(title)),
        'license_id': license_id,
        'owner_org': org_id,
        'dataset_source': kwargs.get('source'),
        'notes': kwargs.get('description'),
        'type': kwargs.get('type', 'dataset'),
        'tags': tags,
        'groups': [{'name': location}] if location else [],
        'extras': extras
    }

    if verbose:
        print('Submitting your package request.')

    print(ckan.package_create(**package_kwargs))


def update(source, resource_id=None, **kwargs):
    """Updates a package (aka dataset)"""
    pass


def delete(resource_id, **kwargs):
    """Deletes a package (aka dataset)"""
    pass


if __name__ == '__main__':
    manager.main()
