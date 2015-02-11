import sys
from optparse import make_option
from datetime import datetime
import logging
import uuid

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.management.base import BaseCommand

from reporting.models import (Asset, Shape, get_asset, SyncRun, Site, dump_json,
                              get_shapes_for_asset, get_shape, asset_iterator)

from threading import Lock
import time

log = logging.getLogger(__name__)


def update_progress(current, total):
    progress = int(float(current) * 100 / total)
    complete = progress/10
    message = '\rProgress: [{0}] {1}% ({2}/{3})'
    bar = '#' * complete + ' ' * (10-complete)
    sys.stdout.write(message.format(bar, progress, current, total))
    sys.stdout.flush()


def delete_not_synced(model, sync_run):
    """Set delete time of any assets/shapes not found in this sync

    (but were found in a previous one *for the same site*)

    Exclude: model.sites or model.asset.sites != sync_run.site
    """
    not_found = model.objects.exclude(last_sync=sync_run)
    if hasattr(model, 'sites'):  # Asset
        to_delete = not_found.filter(sites=sync_run.site)
    elif hasattr(model, 'asset'):  # Shape
        to_delete = not_found.filter(asset__sites=sync_run.site)
    else:
        raise Exception('Wierdness deleting invalid model')

    delete_count = to_delete.count()
    if delete_count:
        msg = 'Setting delete time for {0} {1} not found in this sync'
        log.debug(msg.format(delete_count, model))
        to_delete.update(deleted=timezone.now())
    else:
        msg = '{} items not found but none missing for current sync site'
        log.debug(msg.format(not_found.count()))


def process_single_asset(asset_data):
    try:
        asset_id = asset_data.get('id')
        asset_url = asset_data.get('url')
        full_asset_data = get_asset(asset_url)  # TODO: SLOOOW, get from 1st call
        username = full_asset_data.get('metadata').get('user')
        raw_data = dump_json(full_asset_data)
        log.debug('Processing asset {0}'.format(asset_id))
    except AttributeError:
        log.error('Odd looking asset received: {0}'.format(asset_data))
        raise

    asset_fields = {
        'vs_id': asset_id,
        'raw_data': raw_data,
        'created': timezone.now().isoformat(),
        'deleted': None,  # In case assets were undeleted
        'username': username,
        'last_sync': sync_run,
    }

    # Create asset
    asset, created = Asset.objects.update_or_create(vs_id=asset_id,
                            defaults=asset_fields)

    # Link to sites
    sites = [full_asset_data.get('metadata').get('zonza_site', '')]
    for site in sites:
        # Get_or_create NOT threadsafe!!
        try:
            django_site = Site.objects.get(domain=site)
        except Site.DoesNotExist:
            try:
                with transaction.atomic():
                    django_site = Site.objects.create(domain=site)
            except IntegrityError:
                django_site = Site.objects.get(domain=site)

        asset.sites.add(django_site)

    # Pull shapes out of each asset
    shapes = get_shapes_for_asset(asset_id)
    if hasattr(shapes, 'keys'):
        shapes = (shapes,)

    for shape_data in shapes:
        shape_tag = shape_data.get('tag')
        shape_url = shape_data.get('asset')
        shape = get_shape(shape_url)
        shape_id = shape.get('id')

        shape_fields = {
            'asset': asset,
            'vs_id': shape_id,
            'size': shape.get('size'),
            'raw_data': dump_json(shape),
            'version': 0,
            'timestamp': None,
            'shapetag': shape_tag,
            'last_sync': sync_run,
            'deleted': None,  # In case shape was undeleted
        }

        shape, created = Shape.objects.update_or_create(vs_id=shape_id,
                defaults=shape_fields)


class Command(BaseCommand):
    args = ''
    help = 'Builds a local cache of asset and shape data from Vidispine'

    option_list = BaseCommand.option_list + (
        make_option(
            '-d',
            '--delay',
            dest='delay',
            help='Delay each Vidispine search call by this '
                 'number of seconds. Default is 2'),
        make_option(
            '-s',
            '--skip',
            dest='skip',
            help='Skip this number of assets'),
    )

    def handle(self, *args, **options):
        delay = options.get('delay')
        if delay == None:
            delay = 0
        delay = int(delay)
        skip = int(options.get('skip') or 0)
        sync_uuid = uuid.uuid4().hex
        global sync_run
        ZONZA_SITES = ['trials', '230pas', 'zonzacompany']
        zonza_site = '230pas.zonza.tv'
        current_site, created = Site.objects.get_or_create(domain=zonza_site)
        sync_run = SyncRun.objects.create(sync_uuid=sync_uuid, site=current_site)

        done = 0
        print "Started at {0}".format(timezone.now().isoformat())
        print "Sync UUID is {0}".format(sync_uuid)
        print "Syncing assets and shapes..."

        try:
            pool = ThreadPool(10) # Sets the pool size
            assets = asset_iterator(zonza_site)
            #results = pool.map(process_single_asset, assets, 2)

            # Search all assets in API
            for asset_data, count in assets:

                process_single_asset(asset_data)

                ## Check for assets that do not appear in API (i.e. have been deleted)
                ## Use some kind of flag in the db to delete anything not found in
                ## this run

                ## Report live progress
                done += 1
                update_progress(done, count)
        finally:
            #pool.close()
            #pool.join()
            sync_run.end_time=timezone.now()
            sync_run.save()
            pass

        # 'Delete' any reportable models not containing current sync_guid
        delete_not_synced(Asset, sync_run)
        delete_not_synced(Shape, sync_run)

        sync_run.completed=True
        sync_run.save()
        print "\n...Done!"
