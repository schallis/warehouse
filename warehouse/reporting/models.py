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

PER_PAGE = 100
PAGE_TOKEN = '__page'
LIMIT_TOKEN = '__page_size'
ZONZA_SITE='trials.zonza.tv'
BORK_URL = 'http://api.zonza.tv:8080/v0/'

def GET(url, **kwargs):
    log.debug('HTTP Request to: {0}'.format(url))
    return requests.get(url, **kwargs)


class SyncRun(models.Model):
    """Track each sync"""
    start_time = models.DateTimeField(auto_now=True)
    end_time = models.DateTimeField(blank=True, null=True)
    sync_uuid = models.CharField(max_length=32)
    completed = models.BooleanField(default=False)

    def __unicode__(self):
        return self.sync_uuid


class DamAssetManager(models.Manager):

    def get_queryset(self):
        return BorkAssetQuerySet(model=self.model, using=None)


class ReportableModelMixin(models.Model):
    last_synced = models.DateTimeField(auto_now=True)
    sync_runs = models.ManyToManyField('reporting.SyncRun')

    class Meta:
        abstract = True


class Asset(ReportableModelMixin):
    """A local cache record of an asset in Vidispine"""
    objects = models.Manager()
    vidispine_objects = DamAssetManager()
    deleted = models.DateTimeField(blank=True, null=True)
    vs_id = models.CharField(max_length=10, unique=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255)
    created = models.DateTimeField()
    sites = models.ManyToManyField('sites.Site')
    raw_data = jsonfield.JSONField()

    def __unicode__(self):
        return u'{} - {} ({})'.format(self.vs_id, self.filename, self.username)

    def update_size(self):
        original_shape_qs = self.shape_set.filter(shapetag='original')
        if self.size == 0 and original_shape_qs and original_shape_qs[0].size:
            self.size = original_shape_qs[0].size
            self.save()


METADATA_MAPPING = (
    ('title', 'StandardMetadata.title'),
    ('broadcast_ready', 'StandardMetadata.broadcast_ready'),
)


class StandardMetadata(ReportableModelMixin):
    """A record of standardized metadata on an asset"""
    item = models.ForeignKey('reporting.Asset')



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
    vs_id = models.CharField(max_length=10, unique=True)
    shapetag = models.CharField(max_length=255)
    timestamp = models.DateTimeField(blank=True, null=True)
    size = models.BigIntegerField()
    version = models.IntegerField()
    raw_data = jsonfield.JSONField()

    def __unicode__(self):
        return u'{} - {} (version {})'.format(self.vs_id, self.shapetag, self.version)


def get_asset(url):
    """Retrieve full information for specific asset"""
    headers = {'content-type': 'application/json'}
    headers.update(settings.BORK_AUTH)
    response = GET(url, headers=headers)
    json_response = json.loads(response.content)
    return json_response


def get_shapes_for_asset(asset_id):
    """Retrieve individual transcodes"""
    headers = {'content-type': 'application/json'}
    headers.update(settings.BORK_AUTH)
    response = GET('{}item/{}/asset'.format(BORK_URL, asset_id), headers=headers)
    json_response = json.loads(response.content)
    return json_response.get('assets')


def get_shape(url):
    headers = {'content-type': 'application/json'}
    headers.update(settings.BORK_AUTH)
    response = GET('{}'.format(url), headers=headers)
    json_response = json.loads(response.content)
    return json_response


def perform_search(runas, filters = None):
    """Query Vidispine for items"""
    def raise_invalid():
        raise RuntimeError('Credentials not configured. Please set env variables BORK_TOKEN and BORK_USERNAME')

    log.debug('ZONZA API search request {0}'.format(filters))
    auth = {'Bork-Token': os.environ.get('BORK_TOKEN') or raise_invalid(),
     'Bork-Username': os.environ.get('BORK_USERNAME') or raise_invalid()}
    headers = {'content-type': 'application/json'}
    headers.update(auth)
    params = {'zonza_site': ZONZA_SITE}
    params.update(filters or {})
    response = GET('{}item'.format(BORK_URL), params=params, headers=headers)
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


def item_iterator():
    count = 0
    consumed = 0
    emitted = 0
    existing = 0
    msg = 'Synced {0}/{1} ({2} already existed)'
    skip = 0
    sync_message = lambda : msg.format(emitted, skip, count, existing)
    per_page = PER_PAGE
    filters = {LIMIT_TOKEN: per_page, PAGE_TOKEN: 1}

    while True:
        item_offset, page = get_offsets(emitted, skip, per_page)
        filters[PAGE_TOKEN] = page
        try:
            filters = filters
            result = perform_search(runas=None, filters=filters)
        except Exception as exc:
            error = 'Error when searching for DamAsset: {0}'.format(exc)
            raise

        if not result.get('item'):
            raise StopIteration
        delay = int(getattr(settings, 'SYNC_CALL_DELAY', 0))
        time.sleep(delay)
        count = int(result.get('hits'))
        for num, item in enumerate(result.get('item')):
            consumed += 1
            if num >= item_offset:
                item_id = item['id']
                vidi_ids = [{'id': item_id}]
                try:
                    emitted += 1
                    #yield (item, count)  # single-threaded
                    yield item
                except Exception as exc:
                    error = 'Error when creating DamAsset: {0}'.format(exc)
                    raise

            hits = int(result.get('hits'))
            if skip:
                hits = hits - skip
            if consumed >= hits:
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
    # check for only single shape
    if hasattr(item_shapes, 'keys'):
        item_shapes = (item_shapes,)
    for shape in item_shapes:
        url = shape['asset']
        metadata = get_item_asset(url)
        defaults = {'size': metadata.get('size', 0),
         'version': 0,
         'timestamp': None,
         'shapetag': shape}
        new_shape, created = Shape.objects.get_or_create(item=asset,
                vs_id=metadata.get('id'), defaults=defaults)
