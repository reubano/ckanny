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

from collections import defaultdict
from os import environ
from operator import itemgetter
from dateutil.parser import parse
from datetime import datetime as dt
from os import path as p

from pprint import pprint
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


def make_rkwargs(path, name=None, **kwargs):
    if 'docs.google.com' in path:
        url, f = path, None
        name = name or path.split('gid=')[1].split('&')[0]
    elif 'http' in path:
        url, f = path, None
        name = name or p.basename(path)
    else:
        url = None

        try:
            f = open(path, 'rb')
        except TypeError:
            f = path
        else:
            name = name or p.basename(path)

    try:
        # copy/pasted from utils... fix later
        def_format = path.split('format=')[1].split('&')[0]
    except IndexError:
        def_format = None
    try:
        _format = def_format or p.splitext(path)[1].split('.')[1]
    except IndexError:
        # no file extension given, e.g., a tempfile
        _format = 'csv'

    # Will get `ckan.logic.ValidationError` if url isn't set
    defaults = {
        'url': url or 'http://example.com',
        'name': name,
        'format': _format,
    }

    resource = defaultdict(str, **defaults)
    resource.update(kwargs)

    if f:
        resource.update({'upload': f})
        f.close()

    return resource


@manager.arg(
    'org_id', help='the organization id', nargs='?', default=sys.stdin)
@manager.arg('license_id', 'l', help='Data license', default='cc-by-igo')
@manager.arg('source', 's', help='Data source', default='Multiple sources')
@manager.arg(
    'files', 'f', help='Comma separated list of file paths to add',
    default='')
@manager.arg(
    'names', 'n', help='Comma separated list of file names (requires `files`)',
    default='')
@manager.arg(
    'description', 'd', help='Dataset description (default: same as `title`)')
@manager.arg(
    'methodology', 'm', help='Data collection methodology',
    default='observed', choices=methodologies.keys())
@manager.arg(
    'title', 't', help='Package title', default='Untitled %s' % dt.utcnow())
@manager.arg('tags', 'T', help='Comma separated list of tags', default='')
@manager.arg('type', 'y', help='Package type', default='dataset')
@manager.arg('caveats', 'c', help='Package caveats')
@manager.arg(
    'location', 'L', help='Location the data represents', default='world')
@manager.arg(
    'start', 'S', help='Data start date',
    default=dt.utcnow().strftime('%m/%d/%Y'))
@manager.arg('end', 'e', help='Data end date')
@manager.arg(
    'remote', 'r', help='The remote ckan url (uses `%s` ENV if available)' %
    api.REMOTE_ENV, default=environ.get(api.REMOTE_ENV))
@manager.arg(
    'api_key', 'k', help='The api key (uses `%s` ENV if available)' %
    api.API_KEY_ENV, default=environ.get(api.API_KEY_ENV))
@manager.arg(
    'ua', 'u', help='The user agent (uses `%s` ENV if available)' % api.UA_ENV,
    default=environ.get(api.UA_ENV, api.DEF_USER_AGENT))
@manager.arg(
    'private', 'p', help='Make package private', type=bool, default=False)
@manager.arg(
    'quiet', 'q', help='Suppress debug statements', type=bool, default=False)
@manager.command
def create(org_id, **kwargs):
    """Creates a package (aka dataset)"""
    verbose = not kwargs.get('quiet')
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}
    ckan = CKAN(**ckan_kwargs)

    licenses = it.imap(itemgetter('id'), ckan.license_list())
    orgs = ckan.organization_list()
    org_ids = it.imap(itemgetter('id'), orgs)
    org_names = it.imap(itemgetter('name'), orgs)
    groups = ckan.group_list()

    title = (kwargs.get('title') or '').strip('"').strip("'")
    name = (kwargs.get('name') or '').strip('"').strip("'") or slugify(title)
    source = (kwargs.get('source') or '').strip('"').strip("'")
    description = (kwargs.get('description') or '').strip('"').strip("'")
    caveats = (kwargs.get('caveats') or '').strip('"').strip("'")
    _names = (kwargs.get('names') or '').strip('"').strip("'")
    _files = (kwargs.get('files') or '').strip('"').strip("'")

    raw_tags = filter(None, kwargs.get('tags').split(','))
    tags = [{'state': 'active', 'name': t} for t in raw_tags] or []
    location = kwargs.get('location')
    methodology = kwargs.get('methodology')
    license_id = kwargs.get('license_id')
    raw_start = kwargs.get('start')
    raw_end = kwargs.get('end')

    if raw_start:
        start = parse(str(raw_start)).strftime('%m/%d/%Y')
    else:
        date = None

    if raw_start and raw_end:
        date = '%s-%s' % (start, parse(str(raw_end)).strftime('%m/%d/%Y'))
    elif raw_start:
        date = start

    if location and location in set(groups):
        group_list = [{'name': location}]
    elif location:
        sys.exit('group name: %s not found!' % location)
    else:
        group_list = []

    if org_id not in set(it.chain(org_ids, org_names)):
        sys.exit('organization id: %s not found!' % org_id)

    if license_id not in set(licenses):
        sys.exit('license id: %s not found!' % license_id)

    files = filter(None, _files.split(','))
    names = filter(None, _names.split(','))
    resource_list = list(it.starmap(make_rkwargs, zip(files, names))) or []

    package_kwargs = {
        'title': title,
        'name': name,
        'license_id': license_id,
        'owner_org': org_id,
        'dataset_source': source,
        'notes': description or title,
        'type': kwargs.get('type', 'dataset'),
        'tags': tags,
        'resources': resource_list,
        'package_creator': ckan.user['name'],
        'groups': group_list,
        'dataset_date': date,
        'caveats': caveats,
        'methodology': methodologies[methodology],
        'methodology_other': 'Other' if methodology == 'other' else None,
    }

    if verbose:
        print('Submitting your package request.')
        pprint(package_kwargs)
        print('\n')

    try:
        package = ckan.package_create(**package_kwargs)
    except api.ValidationError as e:
        exit(e)

    if kwargs.get('private'):
        org = package['organization']
        ckan.package_privatize(org_id=org['id'], datasets=[package['id']])

    if verbose:
        print('Your package response.')
        pprint(package)
        print('\n')

    print(package['id'])
    print('\n')


def update(source, resource_id=None, **kwargs):
    """Updates a package (aka dataset)"""
    pass


def delete(resource_id, **kwargs):
    """Deletes a package (aka dataset)"""
    pass


if __name__ == '__main__':
    manager.main()
