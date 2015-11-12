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
from tabutils import fntools as ft, process as pr

manager = Manager()

methods = {
    'census': 'Census',
    'registry': 'Registry',
    'survey': 'Sample Survey',
    'observed': 'Direct Observational Data/Anecdotal Data',
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
    'methodology', 'm', help='Data collection methodology', default='observed')
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
    kw = ft.Objectify(kwargs, type='dataset')
    verbose = not kw.quiet
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}
    ckan = CKAN(**ckan_kwargs)

    licenses = it.imap(itemgetter('id'), ckan.license_list())
    orgs = ckan.organization_list()
    org_ids = it.imap(itemgetter('id'), orgs)
    org_names = it.imap(itemgetter('name'), orgs)
    groups = ckan.group_list()
    name = kw.name or slugify(kw.title)

    raw_tags = filter(None, kw.tags.split(','))
    tags = [{'state': 'active', 'name': t} for t in raw_tags]

    if kw.start:
        start = parse(str(kw.start)).strftime('%m/%d/%Y')
    else:
        date = None

    if kw.start and kw.end:
        date = '%s-%s' % (start, parse(str(kw.end)).strftime('%m/%d/%Y'))
    elif kw.start:
        date = start

    if kw.location in set(groups):
        group_list = [{'name': kw.location}]
    elif kw.location:
        sys.exit('group name: %s not found!' % kw.location)
    else:
        group_list = []

    if org_id not in set(it.chain(org_ids, org_names)):
        sys.exit('organization id: %s not found!' % org_id)

    if kw.license_id not in set(licenses):
        sys.exit('license id: %s not found!' % kw.license_id)

    files = filter(None, kw.files.split(','))
    names = filter(None, kw.names.split(','))
    resource_list = list(it.starmap(make_rkwargs, zip(files, names))) or []

    package_kwargs = {
        'title': kw.title,
        'name': name,
        'license_id': kw.license_id,
        'owner_org': org_id,
        'dataset_source': kw.source,
        'notes': kw.description or kw.title,
        'type': kw.type,
        'tags': tags,
        'resources': resource_list,
        'package_creator': ckan.user['name'],
        'groups': group_list,
        'dataset_date': date,
        'caveats': kw.caveats,
        'methodology': methods.get(kw.methodology, 'Other'),
        'methodology_other': methods.get(kw.methodology) or kw.methodology,
    }

    if verbose:
        print('Submitting your package request.')
        pprint(package_kwargs)
        print('\n')

    try:
        package = ckan.package_create(**package_kwargs)
    except api.ValidationError as e:
        exit(e)

    if kw.private:
        org = package['organization']
        ckan.package_privatize(org_id=org['id'], datasets=[package['id']])

    if verbose:
        print('Your package response.')
        pprint(package)
        print('\n')

    print(package['id'])
    print('\n')


@manager.arg('pid', help='the package id', nargs='?', default=sys.stdin)
@manager.arg('license_id', 'l', help='Data license')
@manager.arg('source', 's', help='Data source')
@manager.arg('description', 'd', help='Dataset description')
@manager.arg('methodology', 'm', help='Data collection methodology')
@manager.arg('title', 't', help='Package title')
@manager.arg('tags', 'T', help='Comma separated list of tags')
@manager.arg('type', 'y', help='Package type')
@manager.arg('caveats', 'c', help='Package caveats')
@manager.arg('location', 'L', help='Location the data represents')
@manager.arg('start', 'S', help='Data start date')
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
def update(pid, **kwargs):
    """Updates a package (aka dataset)"""
    kw = ft.Objectify(kwargs, type='dataset')
    verbose = not kw.quiet
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}
    ckan = CKAN(**ckan_kwargs)

    licenses = it.imap(itemgetter('id'), ckan.license_list())
    groups = ckan.group_list()

    raw_tags = filter(None, kw.tags.split(',')) if kw.tags else []
    tags = [{'state': 'active', 'name': t} for t in raw_tags]

    if kw.start:
        start = parse(str(kw.start)).strftime('%m/%d/%Y')
    else:
        date = None

    if kw.start and kw.end:
        date = '%s-%s' % (start, parse(str(kw.end)).strftime('%m/%d/%Y'))
    elif kw.start:
        date = start

    if kw.location and kw.location in set(groups):
        group_list = [{'name': kw.location}]
    elif kw.location:
        sys.exit('group name: %s not found!' % kw.location)
    else:
        group_list = []

    if kw.license_id and kw.license_id not in set(licenses):
        sys.exit('license id: %s not found!' % kw.license_id)

    package_kwargs = {
        'title': kw.title,
        'name': kw.name,
        'license_id': kw.license_id,
        'dataset_source': kw.source,
        'notes': kw.description or kw.title,
        'type': kw.type,
        'tags': tags,
        'groups': group_list,
        'dataset_date': date,
        'caveats': kw.caveats,
        'methodology': methods.get(kw.methodology, 'Other'),
        'methodology_other': methods.get(kw.methodology) or kw.methodology,
    }

    try:
        old_package = ckan.package_show(id=pid)
    except api.ValidationError as e:
        exit(e)

    if any(package_kwargs.values()):
        # combine keys by returning the last non-empty result
        pred = lambda key: True
        last = lambda pair: filter(None, pair)[-1] if any(pair) else None
        records = [old_package, package_kwargs]
        new_kwargs = pr.merge(records, pred=pred, op=last)

        if verbose:
            print('Submitting your package request.')
            pprint(new_kwargs)
            print('\n')

        package = ckan.package_update(**new_kwargs)
    else:
        package = old_package

    if kw.private:
        org = package['organization']
        ckan.package_privatize(org_id=org['id'], datasets=[package['id']])

    print(package['id'])
    print('\n')


def delete(resource_id, **kwargs):
    """Deletes a package (aka dataset)"""
    pass


if __name__ == '__main__':
    manager.main()
