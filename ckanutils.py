# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab

"""
ckanutils
~~~~~~~~~

Provides methods for interacting with a CKAN instance

Examples:
    literal blocks::

        python example_google.py

Attributes:
    CKAN_KEYS (List[str]): available CKAN keyword arguments.
"""

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

import requests
import ckanapi
import itertools as it

from os import environ, path as p
from time import strptime
from operator import itemgetter
from pprint import pprint

from ckanapi import NotFound, NotAuthorized
from tabutils import process as tup, io as tio

__title__ = 'ckanutils'
__author__ = 'Reuben Cummings'
__description__ = 'Miscellaneous CKAN utility library'
__email__ = 'reubano@gmail.com'
__version__ = '0.10.0'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015 Reuben Cummings'

CKAN_KEYS = ['hash_table', 'remote', 'api_key', 'ua', 'force', 'quiet']
API_KEY_ENV = 'CKAN_API_KEY'
REMOTE_ENV = 'CKAN_REMOTE_URL'
UA_ENV = 'CKAN_USER_AGENT'
DEF_USER_AGENT = 'ckanutils/%s' % __version__
DEF_HASH_PACK = 'hash-table'
DEF_HASH_RES = 'hash-table.csv'
CHUNKSIZE_ROWS = 10 ** 3
CHUNKSIZE_BYTES = 2 ** 20


class CKAN(object):
    """Interacts with a CKAN instance.

    Attributes:
        force (bool): Force.
        verbose (bool): Print debug statements.
        quiet (bool): Suppress debug statements.
        address (str): CKAN url.
        hash_table (str): The hash table package id.
        keys (List[str]):
    """

    def __init__(self, **kwargs):
        """Initialization method.

        Args:
            **kwargs: Keyword arguments.

        Kwargs:
            hash_table (str): The hash table package id.
            remote (str): The remote ckan url.
            api_key (str): The ckan api key.
            ua (str): The user agent.
            force (bool): Force (default: True).
            quiet (bool): Suppress debug statements (default: False).

        Returns:
            New instance of :class:`CKAN`

        Examples:
            >>> CKAN()  #doctest: +ELLIPSIS
            <ckanny.api.CKAN object at 0x...>
        """
        default_ua = environ.get(UA_ENV, DEF_USER_AGENT)
        def_remote = environ.get(REMOTE_ENV)
        def_api_key = environ.get(API_KEY_ENV)
        remote = kwargs.get('remote', def_remote)

        self.api_key = kwargs.get('api_key', def_api_key)
        self.force = kwargs.get('force', True)
        self.quiet = kwargs.get('quiet')
        self.user_agent = kwargs.get('ua', default_ua)
        self.verbose = not self.quiet
        self.hash_table = kwargs.get('hash_table', DEF_HASH_PACK)

        ckan_kwargs = {'apikey': self.api_key, 'user_agent': self.user_agent}
        attr = 'RemoteCKAN' if remote else 'LocalCKAN'
        ckan = getattr(ckanapi, attr)(remote, **ckan_kwargs)

        self.address = ckan.address
        self.package_show = ckan.action.package_show

        try:
            self.hash_table_pack = self.package_show(id=self.hash_table)
        except NotFound:
            self.hash_table_pack = None

        try:
            self.hash_table_id = self.hash_table_pack['resources'][0]['id']
        except (IndexError, TypeError):
            self.hash_table_id = None

        # shortcuts
        self.datastore_search = ckan.action.datastore_search
        self.datastore_create = ckan.action.datastore_create
        self.datastore_delete = ckan.action.datastore_delete
        self.datastore_upsert = ckan.action.datastore_upsert
        self.datastore_search = ckan.action.datastore_search
        self.resource_show = ckan.action.resource_show
        self.resource_create = ckan.action.resource_create
        self.package_create = ckan.action.package_create
        self.revision_show = ckan.action.revision_show
        self.organization_list = ckan.action.organization_list_for_user
        self.organization_show = ckan.action.organization_show

    def create_table(self, resource_id, fields, **kwargs):
        """Creates a datastore table for an existing filestore resource.

        Args:
            resource_id (str): The filestore resource id.
            fields (List[dict]): fields/columns and their extra metadata.
            **kwargs: Keyword arguments that are passed to datastore_create.

        Kwargs:
            force (bool): Create resource even if read-only.
            aliases (List[str]): name(s) for read only alias(es) of the
                resource.
            primary_key (List[str]): field(s) that represent a unique key.
            indexes (List[str]): index(es) on table.

        Returns:
            dict: The newly created data object.

        Raises:
            ValidationError: If unable to validate user on ckan site.
            NotFound: If unable to find resource.

        Examples:
        >>> CKAN(quiet=True).create_table('rid', fields=[{'id': 'field', \
'type': 'text'}])
        Traceback (most recent call last):
        NotFound: Resource `rid` was not found in filestore.
        """
        kwargs.setdefault('force', self.force)
        kwargs['resource_id'] = resource_id
        kwargs['fields'] = fields

        if self.verbose:
            print('Creating table `%s` in datastore...' % resource_id)

        try:
            return self.datastore_create(**kwargs)
        except ckanapi.ValidationError as err:
            if err.error_dict.get('resource_id') == [u'Not found: Resource']:
                raise NotFound(
                    'Resource `%s` was not found in filestore.' % resource_id)
            else:
                raise

    def delete_table(self, resource_id, **kwargs):
        """Deletes a datastore table.

        Args:
            resource_id (str): The datastore resource id.
            **kwargs: Keyword arguments that are passed to datastore_create.

        Kwargs:
            force (bool): Delete resource even if read-only.
            filters (dict): Filters to apply before deleting, e.g.,
                {"name": "fred"}. If missing delete whole table and all
                dependent views.

        Returns:
            dict: Original filters sent if table was found, `None` otherwise.

        Raises:
            ValidationError: If unable to validate user on ckan site.

        Examples:
            >>> CKAN(quiet=True).delete_table('rid')
        """
        kwargs.setdefault('force', self.force)
        kwargs['resource_id'] = resource_id

        if self.verbose:
            print('Deleting table `%s` from datastore...' % resource_id)

        try:
            result = self.datastore_delete(**kwargs)
        except NotFound:
            result = None

            if self.verbose:
                print(
                    "Can't delete. Table `%s` was not found in datastore." %
                    resource_id)
        except ckanapi.ValidationError as err:
            if 'read-only' in err.error_dict:
                print(
                    "Can't delete. Datastore table is read only. Set "
                    "'force' to True and try again.")

                result = None

        return result

    def insert_records(self, resource_id, records, **kwargs):
        """Inserts records into a datastore table.

        Args:
            resource_id (str): The datastore resource id.
            records (List[dict]): The records to insert.
            **kwargs: Keyword arguments that are passed to datastore_create.

        Kwargs:
            method (str): Insert method. One of ['update, 'insert', 'upsert']
                (default: 'insert').
            force (bool): Create resource even if read-only.
            start (int): Row number to start from (zero indexed).
            stop (int): Row number to stop at (zero indexed).
            chunksize (int): Number of rows to write at a time.

        Returns:
            int: Number of records inserted.

        Raises:
            NotFound: If unable to find the resource.

        Examples:
            >>> CKAN(quiet=True).insert_records('rid', [{'field': 'value'}])
            Traceback (most recent call last):
            NotFound: Resource `rid` was not found in filestore.
        """
        chunksize = kwargs.pop('chunksize', 0)
        start = kwargs.pop('start', 0)
        stop = kwargs.pop('stop', None)

        kwargs.setdefault('force', self.force)
        kwargs.setdefault('method', 'insert')
        kwargs['resource_id'] = resource_id
        count = 1

        for chunk in tup.chunk(records, chunksize, start=start, stop=stop):
            length = len(chunk)

            if self.verbose:
                print(
                    'Adding records %i - %i to resource %s...' % (
                        count, count + length - 1, resource_id))

            kwargs['records'] = chunk

            try:
                self.datastore_upsert(**kwargs)
            except requests.exceptions.ConnectionError as err:
                if 'Broken pipe' in err.message[1]:
                    print('Chunksize too large. Try using a smaller chunksize.')
                    return 0
                else:
                    raise err
            except NotFound:
                # Keep exception message consistent with the others
                raise NotFound(
                    'Resource `%s` was not found in filestore.' % resource_id)

            count += length

        return count

    def get_hash(self, resource_id):
        """Gets the hash of a datastore table.

        Args:
            resource_id (str): The datastore resource id.

        Returns:
            str: The datastore resource hash.

        Raises:
            NotFound: If `hash_table_id` isn't set or not in datastore.
            NotAuthorized: If unable to authorize ckan user.

        Examples:
            >>> CKAN(hash_table='hash_jhb34rtj34t').get_hash('rid')
            Traceback (most recent call last):
            NotFound: {u'item': u'package', u'message': u'Package \
`hash_jhb34rtj34t` was not found!'}
        """
        if not self.hash_table_pack:
            message = 'Package `%s` was not found!' % self.hash_table
            raise NotFound({'message': message, 'item': 'package'})

        if not self.hash_table_id:
            message = 'No resources found in package `%s`!' % self.hash_table
            raise NotFound({'message': message, 'item': 'resource'})

        kwargs = {
            'resource_id': self.hash_table_id,
            'filters': {'datastore_id': resource_id},
            'fields': 'hash',
            'limit': 1
        }

        try:
            result = self.datastore_search(**kwargs)
            resource_hash = result['records'][0]['hash']
        except NotFound:
            message = (
                'Hash table `%s` was not found in datastore!' %
                self.hash_table_id)

            raise NotFound({'message': message, 'item': 'datastore'})
        except IndexError:
            if self.verbose:
                print(
                    'Resource `%s` was not found in hash table.' % resource_id)

            resource_hash = None

        if self.verbose:
            print('Resource `%s` hash is `%s`.' % (resource_id, resource_hash))

        return resource_hash

    def fetch_resource(self, resource_id, user_agent=None, stream=True):
        """Fetches a single resource from filestore.

        Args:
            resource_id (str): The filestore resource id.

        Kwargs:
            user_agent (str): The user agent.
            stream (bool): Stream content (default: True).

        Returns:
            obj: requests.Response object.

        Raises:
            NotFound: If unable to find the resource.
            NotAuthorized: If access to fetch resource is denied.

        Examples:
            >>> CKAN(quiet=True).fetch_resource('rid')
            Traceback (most recent call last):
            NotFound: Resource `rid` was not found in filestore.
        """
        user_agent = user_agent or self.user_agent

        try:
            resource = self.resource_show(id=resource_id)
        except NotFound:
            # Keep exception message consistent with the others
            raise NotFound(
                'Resource `%s` was not found in filestore.' % resource_id)

        url = resource.get('perma_link') or resource.get('url')

        if self.verbose:
            print('Downloading url %s...' % url)

        headers = {'User-Agent': user_agent}
        r = requests.get(url, stream=stream, headers=headers)

        if any('403' in h.headers.get('x-ckan-error', '') for h in r.history):
            raise NotAuthorized(
                'Access to fetch resource %s was denied.' % resource_id)
        else:
            return r

    def _update_filestore(self, resource, message, **kwargs):
        """Helps create or update a single resource on filestore.
        To create a resource, you must supply either `url`, `filepath`, or
        `fileobj`.

        Args:
            resource (dict): The resource passed to resource_create.
            **kwargs: Keyword arguments that are passed to resource_create.

        Kwargs:
            url (str): New file url (for file link).
            fileobj (obj): New file like object (for file upload).
            filepath (str): New file path (for file upload).
            post (bool): Post data using requests instead of ckanapi.
            name (str): The resource name.
            description (str): The resource description.
            hash (str): The resource hash.

        Returns:
            obj: requests.Response object if `post` option is specified,
                ckan resource object otherwise.

        Examples:
            >>> ckan = CKAN(quiet=True)
            >>> url = 'http://example.com/file'
            >>> resource = {'package_id': 'pid'}
            >>> message = 'Creating new resource...'
            >>> kwargs = {'name': 'name', 'url': 'http://example.com', \
'format': 'csv'}
            >>> ckan._update_filestore(resource, message, **kwargs)
            Package `pid` was not found.
            >>> resource.update({'resource_id': 'rid', 'name': 'name'})
            >>> resource.update({'description': 'description', 'hash': 'hash'})
            >>> message = 'Updating resource...'
            >>> ckan._update_filestore(resource, message, url=url)
            Resource `rid` was not found in filestore.
        """
        post = kwargs.pop('post', None)
        filepath = kwargs.pop('filepath', None)
        fileobj = kwargs.pop('fileobj', None)
        f = open(filepath, 'rb') if filepath else fileobj
        resource.update(kwargs)

        if self.verbose:
            print(message)

        if post:
            url = '%s/api/action/resource_create' % self.address
            hdrs = {
                'X-CKAN-API-Key': self.api_key, 'User-Agent': self.user_agent}

            data = {'data': resource, 'headers': hdrs}
            data.update({'files': {'upload': f}}) if f else None
        else:
            resource.update({'upload': f}) if f else None
            data = {
                k: v for k, v in resource.items() if not isinstance(v, dict)}

        try:
            if post:
                r = requests.post(url, **data)
            else:
                # resource_create is supposed to return the create resource,
                # but doesn't for whatever reason
                self.resource_create(**data)
                r = {'id': None}
        except NotFound:
            # Keep exception message consistent with the others
            if 'resource_id' in resource:
                print(
                    'Resource `%s` was not found in filestore.' %
                    resource['resource_id'])
            else:
                print('Package `%s` was not found.' % resource['package_id'])

            return None
        except requests.exceptions.ConnectionError as err:
            if 'Broken pipe' in err.message[1]:
                print('File size too large. Try uploading a smaller file.')
                r = None
            else:
                raise err
        else:
            return r
        finally:
            f.close() if f else None

    def create_resource(self, package_id, **kwargs):
        """Creates a single resource on filestore. You must supply either
        `url`, `filepath`, or `fileobj`.

        Args:
            package_id (str): The filestore package id.
            **kwargs: Keyword arguments that are passed to resource_create.

        Kwargs:
            url (str): New file url (for file link).
            filepath (str): New file path (for file upload).
            fileobj (obj): New file like object (for file upload).
            post (bool): Post data using requests instead of ckanapi.
            name (str): The resource name (defaults to the filename).
            description (str): The resource description.
            hash (str): The resource hash.

        Returns:
            obj: requests.Response object if `post` option is specified,
                ckan resource object otherwise.

        Raises:
            TypeError: If neither `url`, `filepath`, nor `fileobj` are supplied.

        Examples:
            >>> ckan = CKAN(quiet=True)
            >>> ckan.create_resource('pid')
            Traceback (most recent call last):
            TypeError: You must specify either a `url`, `filepath`, or `fileobj`
            >>> ckan.create_resource('pid', url='http://example.com/file')
            Package `pid` was not found.
        """
        if not any(map(kwargs.get, ['url', 'filepath', 'fileobj'])):
            raise TypeError(
                'You must specify either a `url`, `filepath`, or `fileobj`')

        path = filter(None, map(kwargs.get, ['url', 'filepath', 'fileobj']))[0]

        try:
            if 'docs.google.com' in path:
                def_name = path.split('gid=')[1].split('&')[0]
            else:
                def_name = p.basename(path)
        except AttributeError:
            def_name = None
            file_format = 'csv'
        else:
            # copy/pasted from utils... fix later
            if 'format=' in path:
                file_format = path.split('format=')[1]
            else:
                file_format = p.splitext(path)[1].lstrip('.')

        kwargs.setdefault('name', def_name)

        # Will get `ckan.logic.ValidationError` if url isn't set
        kwargs.setdefault('url', 'http://example.com')
        kwargs['format'] = file_format
        resource = {'package_id': package_id}
        message = 'Creating new resource in package %s...' % package_id
        return self._update_filestore(resource, message, **kwargs)

    def update_filestore(self, resource_id, **kwargs):
        """Updates a single resource on filestore.

        Args:
            resource_id (str): The filestore resource id.
            **kwargs: Keyword arguments that are passed to resource_create.

        Kwargs:
            url (str): New file url (for file link).
            filepath (str): New file path (for file upload).
            fileobj (obj): New file like object (for file upload).
            post (bool): Post data using requests instead of ckanapi.
            name (str): The resource name.
            description (str): The resource description.
            hash (str): The resource hash.

        Returns:
            obj: requests.Response object if `post` option is specified,
                ckan resource object otherwise.

        Examples:
            >>> CKAN(quiet=True).update_filestore('rid')
            Resource `rid` was not found in filestore.
        """
        try:
            resource = self.resource_show(id=resource_id)
        except NotFound:
            # Keep exception message consistent with the others
            print('Resource `%s` was not found in filestore.' % resource_id)
            return None
        else:
            resource['package_id'] = self.get_package_id(resource_id)
            message = 'Updating resource %s...' % resource_id
            return self._update_filestore(resource, message, **kwargs)

    def update_datastore(self, resource_id, filepath, **kwargs):
        verbose = not kwargs.get('quiet')
        chunk_rows = kwargs.get('chunksize_rows')
        primary_key = kwargs.get('primary_key')
        content_type = kwargs.get('content_type')
        type_cast = kwargs.get('type_cast')
        method = 'upsert' if primary_key else 'insert'
        keys = ['aliases', 'primary_key', 'indexes']

        try:
            extension = p.splitext(filepath)[1].split('.')[1]
        except IndexError:
            # no file extension given, e.g., a tempfile
            extension = tup.ctype2ext(content_type)

        switch = {'xls': 'read_xls', 'xlsx': 'read_xls', 'csv': 'read_csv'}

        try:
            parser = getattr(tio, switch[extension])
        except IndexError:
            print('Error: plugin for extension `%s` not found!' % extension)
            return False
        else:
            parser_kwargs = {
                'encoding': kwargs.get('encoding'),
                'sanitize': kwargs.get('sanitize'),
            }

            records = parser(filepath, **parser_kwargs)
            fields = list(tup.gen_fields(records.next().keys(), type_cast))

            if verbose:
                print('Parsed fields:')
                pprint(fields)

            if type_cast:
                casted_records = tup.gen_type_cast(records, fields)
            else:
                casted_records = records

            create_kwargs = {k: v for k, v in kwargs.items() if k in keys}

            if not primary_key:
                self.delete_table(resource_id)

            insert_kwargs = {'chunksize': chunk_rows, 'method': method}
            self.create_table(resource_id, fields, **create_kwargs)
            args = [resource_id, casted_records]
            return self.insert_records(*args, **insert_kwargs)

        def find_ids(self, packages, **kwargs):
            default = {'rid': '', 'pname': ''}
            kwargs.update({'method': self.query, 'default': default})
            return tup.find(packages, **kwargs)

    def get_package_id(self, resource_id):
        """Gets the package id of a single resource on filestore.

        Args:
            resource_id (str): The filestore resource id.

        Returns:
            str: The package id.

        Examples:
            >>> CKAN(quiet=True).get_package_id('rid')
            Resource `rid` was not found in filestore.
        """
        try:
            resource = self.resource_show(id=resource_id)
        except NotFound:
            # Keep exception message consistent with the others
            print('Resource `%s` was not found in filestore.' % resource_id)
            return None
        else:
            revision = self.revision_show(id=resource['revision_id'])
            return revision['packages'][0]

    def create_hash_table(self, verbose=False):
        kwargs = {
            'resource_id': self.hash_table_id,
            'fields': [
                {'id': 'datastore_id', 'type': 'text'},
                {'id': 'hash', 'type': 'text'}],
            'primary_key': 'datastore_id'
        }

        if verbose:
            print('Creating hash table...')

        self.create_table(**kwargs)

    def update_hash_table(self, resource_id, resource_hash, verbose=False):
        records = [{'datastore_id': resource_id, 'hash': resource_hash}]

        if verbose:
            print('Uodating hash table...')

        self.insert_records(self.hash_table_id, records, method='upsert')

    def get_update_date(self, item):
        timestamps = {
            'revision_timestamp': 'revision',
            'last_modified': 'resource',
            'metadata_modified': 'package'
        }

        for key, value in timestamps.items():
            if key in item:
                timestamp = item[key]
                item_type = value
                break
        else:
            keys = timestamps.keys()
            msg = 'None of the following keys found in item: %s' % keys
            raise TypeError(msg)

        if not timestamp and item_type == 'resource':
            # print('Resource timestamp is empty. Querying revision.')
            timestamp = self.revision_show(id=item['revision_id'])['timestamp']

        return strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')

    def filter(self, items, tagged=None, named=None, updated=None):
        for i in items:
            if i['state'] != 'active':
                continue

            if updated and updated(self.get_update_date(i)):
                yield i
                continue

            if named and named.lower() in i['name'].lower():
                yield i
                continue

            tags = it.imap(itemgetter('name'), i['tags'])
            is_tagged = tagged and 'tags' in i

            if is_tagged and any(it.ifilter(lambda t: t == tagged, tags)):
                yield i
                continue

            if not (named or tagged or updated):
                yield i

    def query(self, packages, **kwargs):
        pkwargs = {
            'named': kwargs.get('pnamed'),
            'tagged': kwargs.get('ptagged')}

        rkwargs = {
            'named': kwargs.get('rnamed'),
            'tagged': kwargs.get('rtagged')}

        skwargs = {'key': self.get_update_date, 'reverse': True}
        filtered_packages = self.filter(packages, **pkwargs)

        for p in sorted(filtered_packages, **skwargs):
            package = self.package_show(id=p['name'])
            resources = self.filter(package['resources'], **rkwargs)

            for resource in sorted(resources, **skwargs):
                yield {'rid': resource['id'], 'pname': package['name']}
