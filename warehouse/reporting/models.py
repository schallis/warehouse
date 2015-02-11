import os
import time
import logging
import requests
import jsonfield
import json

from retrying import retry

from django.db import models
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.models import _simple_domain_name_validator

from dateutil import parser


log = logging.getLogger(__name__)

PER_PAGE = 100
PAGE_TOKEN = '__page'
LIMIT_TOKEN = '__page_size'

def load_json(raw):
    """for debugging"""
    try:
        return json.loads(raw)
    except ValueError:
        log.error('Unable to load JSON: %r' % raw)
        raise


def dump_json(obj):
    try:
        return json.dumps(obj)
    except ValueError:
        log.error('Unable to dump JSON: %r' % obj)
        raise


@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
def GET(url, **kwargs):
    result = requests.get(url, **kwargs)
    log.debug('HTTP Request performed to: {0} [status: {1}]'.format(url, result.status_code))
    if int(result.status_code) == 500:
        log.debug('warning status {0}'.format(result.status_code))
        raise Exception('Unable to retrieve data')
    return result


class Site(models.Model):
    domain = models.CharField('domain name', max_length=100, unique=True,
            validators=[_simple_domain_name_validator])

    # Sales person?
    # Account person?
    # Company?
    # Contract terms?

    def __unicode__(self):
        return self.domain



class SyncRun(models.Model):
    """Track each sync"""
    start_time = models.DateTimeField(auto_now=True)
    end_time = models.DateTimeField(blank=True, null=True)
    sync_uuid = models.CharField(max_length=32)
    completed = models.BooleanField(default=False)
    site = models.ForeignKey('reporting.Site')

    def __unicode__(self):
        return self.sync_uuid


class DamAssetManager(models.Manager):

    def get_queryset(self):
        return BorkAssetQuerySet(model=self.model, using=None)


class ReportableModelMixin(models.Model):
    last_synced = models.DateTimeField(auto_now=True)
    last_sync = models.ForeignKey('reporting.SyncRun')

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
    sites = models.ManyToManyField('reporting.Site')
    raw_data = jsonfield.JSONField()

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
    asset = models.ForeignKey('reporting.Asset')
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
    json_response = load_json(response.content)
    return json_response


def get_shapes_for_asset(asset_id):
    """Retrieve individual transcodes"""
    headers = {'content-type': 'application/json'}
    headers.update(settings.BORK_AUTH)
    response = GET('{}item/{}/asset'.format(settings.BORK_URL, asset_id), headers=headers)
    json_response = load_json(response.content)
    return json_response.get('assets')


def get_shape(url):
    headers = {'content-type': 'application/json'}
    headers.update(settings.BORK_AUTH)
    response = GET('{}'.format(url), headers=headers)
    json_response = load_json(response.content)
    return json_response


def perform_search(runas, filters = None):
    """Query Vidispine for assets"""
    log.debug('ZONZA API search request {0}'.format(filters))
    headers = {'content-type': 'application/json'}
    headers.update(settings.BORK_AUTH)
    response = GET('{}item'.format(settings.BORK_URL), params=filters, headers=headers)
    json_response = load_json(response.content)
    return json_response


def get_offsets(emitted, skip, precache):
    """Compute vidispine search offsets from our iterator state"""
    start_at = skip + emitted
    asset = start_at % precache
    page = start_at / precache + 1
    return (asset, page)


def asset_iterator(zonza_site, skip):
    count = 0
    consumed = 0
    emitted = 0
    existing = 0
    msg = 'Synced {0}/{1} ({2} already existed)'
    skip = skip or 0
    sync_message = lambda : msg.format(emitted, skip, count, existing)
    per_page = PER_PAGE
    assets_skipped = skip/per_page * per_page
    filters = {
        'zonza_site': zonza_site,
        LIMIT_TOKEN: per_page,
        PAGE_TOKEN: 1
    }

    while True:
        asset_offset, page = get_offsets(emitted, skip, per_page)
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
        count = int(result.get('hits')) - skip
        for num, asset in enumerate(result.get('item')):
            consumed += 1
            if num >= asset_offset:
                asset_id = asset['id']
                vidi_ids = [{'id': asset_id}]
                try:
                    emitted += 1
                    yield (asset, count)  # single-threaded
                    #yield asset
                except Exception as exc:
                    error = 'Error when creating DamAsset: {0}'.format(exc)
                    raise

            hits = int(result.get('hits'))
            if skip:
                hits = hits - assets_skipped
            if consumed >= hits:
                raise StopIteration
