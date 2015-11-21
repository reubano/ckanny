#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab

""" CKAN Filestore management scripts """

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

import sys
import ckanutils as api

from os import unlink, getcwd, environ, path as p
from tempfile import NamedTemporaryFile

from manager import Manager
from xattr import xattr
from ckanutils import CKAN
from tabutils import process as tup, io as tio

manager = Manager()


@manager.arg(
    'resource_id', help='the resource id', nargs='?', default=sys.stdin)
@manager.arg(
    'destination', 'd', help='the destination folder or file path',
    default=getcwd())
@manager.arg(
    'remote', 'r', help='the remote ckan url (uses `%s` ENV if available)' %
    api.REMOTE_ENV, default=environ.get(api.REMOTE_ENV))
@manager.arg(
    'api_key', 'k', help='the api key (uses `%s` ENV if available)' %
    api.API_KEY_ENV, default=environ.get(api.API_KEY_ENV))
@manager.arg(
    'ua', 'u', help='the user agent (uses `%s` ENV if available)' % api.UA_ENV,
    default=environ.get(api.UA_ENV))
@manager.arg(
    'chunksize_bytes', 'c', help='number of bytes to read/write at a time',
    type=int, default=api.CHUNKSIZE_BYTES)
@manager.arg(
    'name_from_id', 'n', help='Use resource id for filename', type=bool,
    default=False)
@manager.arg(
    'quiet', 'q', help='suppress debug statements', type=bool, default=False)
@manager.command
def fetch(resource_id, **kwargs):
    """Downloads a filestore resource"""
    verbose = not kwargs['quiet']
    filepath = kwargs['destination']
    name_from_id = kwargs.get('name_from_id')
    chunksize = kwargs.get('chunksize_bytes')
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}
    ckan = CKAN(**ckan_kwargs)

    try:
        r = ckan.fetch_resource(resource_id)
    except api.NotAuthorized as err:
        sys.exit('ERROR: %s\n' % str(err))
    else:
        fkwargs = {
            'headers': r.headers,
            'name_from_id': name_from_id,
            'resource_id': resource_id}

        filepath = tup.make_filepath(filepath, **fkwargs)
        tio.write(filepath, r.iter_content, chunksize=chunksize)

        # save encoding to extended attributes
        x = xattr(filepath)

        if verbose and r.encoding:
            print('saving encoding %s to extended attributes' % r.encoding)

        if r.encoding:
            x['com.ckanny.encoding'] = r.encoding

        print(filepath)


@manager.arg(
    'resource_id', help='the resource id', nargs='?', default=sys.stdin)
@manager.arg(
    'src_remote', 's', help=('the source remote ckan url (uses `%s` ENV'
    ' if available)') % api.REMOTE_ENV, default=environ.get(api.REMOTE_ENV))
@manager.arg(
    'dest_remote', 'd', help=('the destination remote ckan url (uses `%s` ENV'
    ' if available)') % api.REMOTE_ENV, default=environ.get(api.REMOTE_ENV))
@manager.arg(
    'api_key', 'k', help='the api key (uses `%s` ENV if available)' %
    api.API_KEY_ENV, default=environ.get(api.API_KEY_ENV))
@manager.arg(
    'ua', 'u', help='the user agent (uses `%s` ENV if available)' % api.UA_ENV,
    default=environ.get(api.UA_ENV))
@manager.arg(
    'chunksize_bytes', 'c', help='number of bytes to read/write at a time',
    type=int, default=api.CHUNKSIZE_BYTES)
@manager.arg(
    'quiet', 'q', help='suppress debug statements', type=bool, default=False)
@manager.command
def migrate(resource_id, **kwargs):
    """Copies a filestore resource from one ckan instance to another"""
    src_remote, dest_remote = kwargs['src_remote'], kwargs['dest_remote']

    if src_remote == dest_remote:
        msg = (
            'ERROR: `dest-remote` of %s is the same as `src-remote` of %s.\n'
            'The dest and src remotes must be different.\n' % (src_remote,
            dest_remote))

        sys.exit(msg)

    verbose = not kwargs['quiet']
    chunksize = kwargs['chunksize_bytes']
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}
    src_ckan = CKAN(remote=src_remote, **ckan_kwargs)
    dest_ckan = CKAN(remote=dest_remote, **ckan_kwargs)

    try:
        r = src_ckan.fetch_resource(resource_id)
        filepath = NamedTemporaryFile(delete=False).name
    except api.NotAuthorized as err:
        sys.exit('ERROR: %s\n' % str(err))
    except Exception as err:
        sys.exit('ERROR: %s\n' % str(err))
    else:
        tio.write(filepath, r.raw.read(), chunksize=chunksize)
        resource = dest_ckan.update_filestore(resource_id, filepath=filepath)

        if resource and verbose:
            print('Success! Resource %s updated.' % resource_id)
        elif not resource:
            sys.exit('Error uploading file!')
    finally:
        if verbose:
            print('Removing tempfile...')

        unlink(filepath)


@manager.arg(
    'source', help='the source file path', nargs='?', default=sys.stdin)
@manager.arg(
    'name', 'n', help='the resource name (used to create a new resource)')
@manager.arg(
    'resource_id', 'R', help=('the resource id (used to update an existing'
    ' resource, default: source file name if `package_id` not specified)'))
@manager.arg(
    'package_id', 'p', help='the package id (used to create a new resource)')
@manager.arg(
    'remote', 'r', help='the remote ckan url (uses `%s` ENV if available)' %
    api.REMOTE_ENV, default=environ.get(api.REMOTE_ENV))
@manager.arg(
    'api_key', 'k', help='the api key (uses `%s` ENV if available)' %
    api.API_KEY_ENV, default=environ.get(api.API_KEY_ENV))
@manager.arg(
    'ua', 'u', help='the user agent (uses `%s` ENV if available)' % api.UA_ENV,
    default=environ.get(api.UA_ENV))
@manager.arg(
    'quiet', 'q', help='suppress debug statements', type=bool, default=False)
@manager.command
def upload(source, resource_id=None, package_id=None, **kwargs):
    """Updates the filestore of an existing resource or creates a new one"""
    verbose = not kwargs['quiet']
    resource_id = resource_id or p.splitext(p.basename(source))[0]
    ckan_kwargs = {k: v for k, v in kwargs.items() if k in api.CKAN_KEYS}

    if package_id and verbose:
        print(
            'Creating filestore resource %s in dataset %s...' %
            (source, package_id))
    elif verbose:
        print(
            'Uploading %s to filestore resource %s...' % (source, resource_id))

    ckan = CKAN(**ckan_kwargs)

    resource_kwargs = {
        'url' if 'http' in source else 'filepath': source,
        'name': kwargs.get('name')
    }

    if package_id:
        resource = ckan.create_resource(package_id, **resource_kwargs)
    else:
        resource = ckan.update_filestore(resource_id, **resource_kwargs)

    if package_id and resource and verbose:
        infix = '%s ' % resource['id'] if resource.get('id') else ''
        print('Success! Resource %screated.' % infix)
    elif resource and verbose:
        print('Success! Resource %s updated.' % resource_id)
    elif not resource:
        sys.exit('Error uploading file!')


if __name__ == '__main__':
    manager.main()
