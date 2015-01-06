import os
import time
import logging
import json
import requests
import jsonfield

from django.db import models
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.models import Site

from dateutil import parser

log = logging.getLogger(__name__)

PAGE_TOKEN = '__page'
LIMIT_TOKEN = '__page_size'
BORK_URL = 'http://api.zonza.tv:8080/v0/'
BORK_AUTH = {
    'Bork-Token': os.environ.get('BORK_TOKEN') or raise_invalid(),
    'Bork-Username': os.environ.get('BORK_USERNAME') or raise_invalid()
}

def GET(url, **kwargs):
    log.debug('HTTP Request to: ', url)
    return requests.get(url, **kwargs)


class DamAssetManager(models.Manager):

    def get_query_set(self):
        return BorkAssetQuerySet(model=self.model, using=None)


class ReportableModelMixin(models.Model):
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Asset(ReportableModelMixin):
    """A local cache record of an asset in Vidispine"""
    objects = models.Manager()
    vidispine_objects = DamAssetManager()
    deleted = models.DateTimeField(blank=True, null=True)
    vs_id = models.CharField(max_length=10)
    filename = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255)
    created = models.DateTimeField()
    sites = models.ManyToManyField('sites.Site')
    size = models.BigIntegerField()
    raw_metadata = jsonfield.JSONField()

    def __unicode__(self):
        return u'{} - {} ({})'.format(self.vs_id, self.filename, self.username)

    def update_size(self):
        original_shape_qs = self.shape_set.filter(shapetag='original')
        if self.size == 0 and original_shape_qs and original_shape_qs[0].size:
            self.size = original_shape_qs[0].size
            self.save()


class Download(ReportableModelMixin):
    """A record of each shape download"""
    item = models.ForeignKey('reporting.Asset')
    when = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=255)
    shape = models.ForeignKey('reporting.Shape')


class Shape(ReportableModelMixin):
    """A record of a Vidispine shape"""
    deleted = models.DateTimeField(blank=True, null=True)
    item = models.ForeignKey('reporting.Asset')
    vs_id = models.CharField(max_length=10)
    shapetag = models.CharField(max_length=255)
    timestamp = models.DateTimeField(blank=True, null=True)
    size = models.BigIntegerField()
    version = models.IntegerField()

    def __unicode__(self):
        return u'{} - {} (version {})'.format(self.vs_id, self.shapetag, self.version)


def raise_invalid():
    raise RuntimeError('Credentials not configured. Please set env variables BORK_TOKEN and BORK_USERNAME')


def get_item_asset(url):
    headers = {'content-type': 'application/json'}
    headers.update(BORK_AUTH)
    response = GET(url, headers=headers)
    json_response = json.loads(response.content)
    return json_response


def get_item_assets(vs_id):
    headers = {'content-type': 'application/json'}
    headers.update(BORK_AUTH)
    response = GET('{}item/{}/asset'.format(BORK_URL, vs_id), headers=headers)
    json_response = json.loads(response.content)
    return json_response


def perform_search(runas, filters = None):
    """Query Vidispine for items"""
    url = 'http://api.zonza.tv:8080/v0/'

    def raise_invalid():
        raise RuntimeError('Credentials not configured. Please set env variables BORK_TOKEN and BORK_USERNAME')

    auth = {'Bork-Token': os.environ.get('BORK_TOKEN') or raise_invalid(),
     'Bork-Username': os.environ.get('BORK_USERNAME') or raise_invalid()}
    headers = {'content-type': 'application/json'}
    headers.update(auth)
    params = {'zonza_site': 'deluxe.zonza.tv'}
    params.update(filters)
    response = GET('{}item'.format(url), params=params, headers=headers)
    json_response = json.loads(response.content)
    return json_response


def get_offsets(emitted, skip, precache):
    """Compute vidispine search offsets from our iterator state"""
    start_at = skip + emitted
    item = start_at % precache
    page = start_at / precache + 1
    return (item, page)


def retrieve_field_from_vidispine(field, model):
    """ Decide if we can and should sync this field

    :param field:
        A string denoting the field name
    :param model:
        The Asset model class

    :returns: :type:`!Boolean`
    """
    if field == 'id' or field.startswith('_'):
        return False
    if field not in model._meta.get_all_field_names():
        return False
    return True


def update_asset_metadata_from_vidispine(asset, item):
    """Populate the metadata fields defined on the asset with data
    from the corresponding fields in the Vidispine item

    :param asset:
        The Fido asset instance
    :param item:
    """
    for field, values in item.metadata.items():
        if retrieve_field_from_vidispine(field, asset):
            value = values[0]
            setattr(asset, field, value)

    asset._mirror_on_vidispine = False
    asset.save()


class AdvancedSearch(object):
    """Represent an advanced search query using Django style querying """

    def __init__(self, operator, *args, **kwargs):
        """"
        :param operator:
            Either 'AND' or 'OR' describing how to combine the restrictions
        :param **kwargs:
            Field/value combinations to restrict the search to
        """
        if operator not in ('AND', 'OR'):
            raise TypeError('Operator must be AND or OR')
        if args:
            raise TypeError('All fields must be specified as kwargs')
        self._dict = {'advanced_search': {'operator': operator,
                             'fields': Fields(**kwargs).serialise()}}

    def serialise(self):
        """Compile the search into a form understandable by Vidispine

        :returns:
            A dictionary that can be passed directly into Vidispine as JSON
        """
        return self._dict


class Fields(object):
    """Represents a Vidispine field search dict"""

    def __init__(self, *args, **kwargs):
        self._set = []
        for key, value in sorted(kwargs.items()):
            self._set.append({'name': key,
             'value': value})

    def serialise(self):
        """Compile the search into a form understandable by Vidispine

        :returns:
            A list that can be passed into an advanced search dictionary
        """
        return self._set


class BorkAssetQuerySet(models.query.QuerySet):

    def __init__(self, model = None, query = None, using = None):
        self._result_cache = []
        self._precache_num = getattr(settings, 'VIDISPINE_PRECACHE_NUM', 15)
        self._runas = None
        self._iter = None
        self._prefetch_related_lookups = []
        self._prefetch_done = False
        self._count = None
        self._limit = None
        self._skip = 0
        self._options = {'create_mode': True}
        self.filters = {LIMIT_TOKEN: self._precache_num,
         PAGE_TOKEN: 1}
        super(BorkAssetQuerySet, self).__init__(model, query, using)

    def __contains__(self, val):
        raise NotImplementedError

    def __and__(self, other):
        raise NotImplementedError

    def __or__(self, other):
        raise NotImplementedError

    def aggregate(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def update(self, **kwargs):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        if args:
            raise TypeError('All fields must be specified as kwargs')
        filters = AdvancedSearch('AND', **kwargs).serialise()
        self.filters.update(filters)
        return self

    def __getitem__(self, k):
        """Retrieves an item or slice from the set of results"""
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert not isinstance(k, slice) and k >= 0 or isinstance(k, slice) and (k.start is None or k.start >= 0) and (k.stop is None or k.stop >= 0), 'Negative indexing is not supported.'
        if self._result_cache is not None:
            if self._iter is not None:
                if isinstance(k, slice):
                    if k.stop is not None:
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
            return self._result_cache[k]
        if isinstance(k, slice):
            query_set = self
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            if stop:
                query_set = query_set.limit(stop - (start or 0))
            if start:
                query_set = query_set.skip(start)
            return k.step and list(query_set)[::k.step] or query_set
        try:
            query_set = self
            query_set = query_set.limit(1)
            query_set = query_set.skip(k)
            return list(query_set)[0]
        except self.model.DoesNotExist as exc:
            raise IndexError(exc.args)

    def runas(self, username):
        """Set the user who the search is performed as"""
        if not isinstance(username, basestring):
            raise TypeError('runas must be a username string')
        self._runas = username
        return self

    def _adjusted_count(self):
        """Alter the raw _count param from Vidispine to take into
        account limits set in this QuerySet
        """
        max_skip = self._skip
        if self._count is not None:
            max_skip = min(max_skip, self._count)
        remainder = self._count - max_skip
        return self._limit and min(remainder, self._limit) or remainder

    def __len__(self):
        """Evaluate the entire QuerySet and return its length"""
        return len(list(self.__iter__()))

    def all(self):
        return self.__call__()

    def skip(self, num):
        """Ensure the queryset does not return the first `num` items"""
        self._skip = num
        return self

    def next(self):
        """Advance the result cache iterator by at least one"""
        if not self._iter:
            self._iter = self.iterator()
        return next(self._iter)

    def exists(self):
        """Return a boolean indicating the existence of results"""
        if self._result_cache is None:
            self.limit(1)
            exists = bool(self.next())
            return exists
        return bool(self._result_cache)

    def count(self):
        """Use cached information to calculate the count"""
        if not self._count:
            result = perform_search(self._runas, filters=self.filters)
            self._count = int(result.get('hits'))
        return self._adjusted_count()

    def _result_iter(self):
        """Iterate over the cache, populating it when necessary"""
        pos = 0
        while 1:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1

            if not self._iter:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._fill_cache()

    def _fill_cache(self, num = None):
        """Populate the cache with the next set of precached results"""
        if self._iter:
            try:
                for __ in range(num or self._precache_num):
                    self._result_cache.append(next(self._iter))
                    if self._limit_met(len(self._result_cache)):
                        raise StopIteration

            except StopIteration:
                self._iter = None

    def _limit_met(self, count):
        """Does the given count match or exceed the limit"""
        return bool(self._limit and count >= self._limit)

    def limit(self, num):
        """Cap the number of returned results to the specified limit"""
        self._limit = num
        return self

    def filter(self, *args, **kwargs):
        """Restrict the search to those whose field/value combinations
        match the kwargs
        """
        if args:
            raise TypeError('All fields must be specified as kwargs')
        return self.__call__(**kwargs)

    def order_by(self, *field_names):
        """ TODO: implement ordering
        Returns a new DamAssetQuerySet instance with the ordering changed.
        """
        assert self.query.can_filter(), 'Cannot reorder a query once a slice has been taken.'
        return self._clone()

    def options(self, *args, **kwargs):
        """Set non action options on the queryset"""
        if args:
            raise TypeError('All fields must be specified as kwargs')
        self._options.update(kwargs)
        return self

    def iterator(self):
        """Lazily retrieve Vidispine search results, emitting assets"""
        consumed = 0
        emitted = 0
        existing = 0
        msg = 'Synced {0}/{1} ({2} already existed)'
        sync_message = lambda : msg.format(emitted, self._count, existing)
        while True:
            item_offset, page = get_offsets(emitted, self._skip, self._precache_num)
            self.filters[PAGE_TOKEN] = page
            try:
                filters = self.filters
                filters.update({'__rich': 'true'})
                result = perform_search(self._runas, filters=filters)
            except Exception as exc:
                error = 'Error when searching for DamAsset: {0}'.format(exc)
                raise

            if not result.get('item'):
                raise StopIteration
            delay = int(getattr(settings, 'SYNC_CALL_DELAY', 0))
            time.sleep(delay)
            self._count = int(result.get('hits'))
            for num, item in enumerate(result.get('item')):
                consumed += 1
                if num >= item_offset:
                    item_id = item['id']
                    vidi_ids = [{'id': item_id}]
                    try:
                        if self._options.get('create_mode'):
                            try:
                                asset = self.model.objects.get(vs_id=item_id)
                                created = False
                            except self.model.DoesNotExist:
                                metadata = get_metadata_from_vidispine(self.model, item)
                                metadata['filename'] = item.get('id')
                                asset = self.model.objects.create(vs_id=item_id, raw_metadata=item, **metadata)
                                created = True

                            if not created:
                                existing += 1
                            create_sites_for_item(asset, item)
                            create_shapes_from_vidispine(asset, item)
                            asset.update_size()
                        else:
                            existing += 1
                            asset = self.model.objects.get(vs_id=item_id)
                        asset.json = item
                        emitted += 1
                        yield asset
                    except self.model.DoesNotExist:
                        msg = 'Asset {0} exists in Vidispine but not in here'
                        raise ImproperlyConfigured(msg.format(vidi_ids))
                    except Exception as exc:
                        error = 'Error when creating DamAsset: {0}'.format(exc)
                        raise

                hits = int(result.get('hits'))
                if self._skip:
                    hits = hits - self._skip
                if self._limit_met(emitted) or consumed >= hits:
                    raise StopIteration


ASSET_FIELD_MAPPINGS = {'filename': ('filename', '<no filename>'),
 'size': ('size', '0'),
 'username': ('user', '<no username>')}
ASSET_FIELD_MAPPINGS_EXCEPTIONS = ['deleted',
 'last_synced',
 'vs_id',
 'sites',
 'id',
 'raw_metadata']
DATA_TRANSFORMATIONS = [(models.fields.DateTimeField, parser.parse), (models.fields.IntegerField, int)]

def create_sites_for_item(asset, item):
    sites = [item.get('metadata').get('zonza_site', '')]
    for site in sites:
        django_site, __ = Site.objects.get_or_create(name=site, domain=site)
        asset.sites.add(django_site)


def mapped_field(field, item):
    """Take a django asset field name and return mapped data from the
    Vidispine item
    """
    fallback = (field, '<no value>')
    attribute, default = ASSET_FIELD_MAPPINGS.get(field) or fallback
    try:
        value = item.get(attribute, default)
        if not value:
            if attribute == 'created':
                shapes = item.get('shapes')
                return shapes[0].container_file()['timestamp']
            return default
    except KeyError as exc:
        log.warning('Error in mapped_field with arguments (%s, %s)' % (field, item))

    return value


def get_metadata_from_vidispine(asset_model, item):
    """Return a dictionary of values for each field on the asset
    containing the equivalent values from the Vidispine item
    """
    metadata = {}
    exceptions = ASSET_FIELD_MAPPINGS_EXCEPTIONS
    all_fields = asset_model._meta.get_all_field_names()
    for field in [ f for f in all_fields if f not in exceptions ]:
        raw_value = mapped_field(field, item.get('metadata'))
        try:
            field_model = asset_model._meta.get_field(field)
        except models.fields.FieldDoesNotExist:
            continue

        if field_model.empty_strings_allowed and not raw_value:
            msg = 'No data for required field {0}'.format(field)
            raise ImproperlyConfigured(msg)
        value = raw_value
        for field_type, function in DATA_TRANSFORMATIONS:
            if isinstance(field_model, field_type):
                try:
                    value = function(raw_value)
                except Exception:
                    log.warning('Data not conformant and default not good enough')

                break

        metadata[field] = value

    return metadata


def create_shapes_from_vidispine(asset, item):
    item_id = item.get('id')
    item_shapes = get_item_assets(item_id).get('assets')
    for shape in item_shapes:
        url = shape['asset']
        metadata = get_item_asset(url)
        defaults = {'size': metadata.get('size', 0),
         'version': 0,
         'timestamp': None,
         'shapetag': shape.get('tag', '<no shapetag>')}
        new_shape, created = Shape.objects.get_or_create(item=asset,
                vs_id=metadata.get('id'), defaults=defaults)
