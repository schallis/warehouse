import sys
from optparse import make_option
from datetime import datetime
import json
import logging
import uuid

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

from django.db import transaction
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

from reporting.models import (Asset, Shape, get_asset, SyncRun,
                              get_shapes_for_asset, get_shape, item_iterator)


log = logging.getLogger(__name__)


def get_json(obj):
    try:
        return json.dumps(obj)
    except ValueError:
        log.error('Unable to parse JSON: %r' % obj)
        raise


def update_progress(current, total):
    progress = int(float(current) * 100 / total)
    complete = progress/10
    message = '\rProgress: [{0}] {1}% ({2}/{3})'
    bar = '#' * complete + ' ' * (10-complete)
    sys.stdout.write(message.format(bar, progress, current, total))
    sys.stdout.flush()


def delete_not_synced(model, sync_run):
    to_delete = model.objects.exclude(sync_runs=sync_run)
    delete_count = to_delete.count()
    if delete_count:
        msg = 'Deleting {0} {1} not found in this sync'
        log.debug(msg.format(delete_count, model))
        to_delete.delete()


def process_single_item(asset_data):
    try:
        asset_id = asset_data.get('id')
        log.debug('Processing item {0}'.format(asset_id))
        asset_url = asset_data.get('url')
        full_asset_data = get_asset(asset_url)  # TODO: SLOOOW, get from 1st call
        asset_fields = {
            'vs_id': asset_id,
            'raw_data': get_json(full_asset_data),
            'created': timezone.now().isoformat(),
            'username': full_asset_data.get('metadata').get('user'),
        }
    except AttributeError:
        log.error('Odd looking asset received: %r' % asset_data)
        raise

    # Create asset
    item, created = Asset.objects.update_or_create(vs_id=asset_id,
                            defaults=asset_fields)
    item.sync_runs.add(sync_run)

    # Link to sites
    sites = [full_asset_data.get('metadata').get('zonza_site', '')]
    for site in sites:
        with transaction.atomic():
            django_site, __ = Site.objects.get_or_create(name=site, domain=site)
            item.sites.add(django_site)

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
            'item': item,
            'vs_id': shape_id,
            'size': shape.get('size'),
            'raw_data': get_json(shape),
            'version': 0,
            'timestamp': None,
            'shapetag': shape_tag,
        }

        shape, created = Shape.objects.update_or_create(vs_id=shape_id,
                defaults=shape_fields)
        shape.sync_runs.add(sync_run)


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
            help='Skip this number of items'),
    )

    def handle(self, *args, **options):
        delay = options.get('delay')
        if delay == None:
            delay = 0
        delay = int(delay)
        skip = int(options.get('skip') or 0)
        sync_uuid = uuid.uuid4().hex
        global sync_run
        sync_run = SyncRun.objects.create(sync_uuid=sync_uuid)  # Nasty

        done = 0
        print "Started at {0}".format(timezone.now().isoformat())
        print "Sync UUID is {0}".format(sync_uuid)
        print "Syncing assets and shapes..."

        try:
            pool = ThreadPool(10) # Sets the pool size
            items = item_iterator()
            results = pool.map(process_single_item, items, 10)

            # Search all assets in API
            #for asset_data, count in item_iterator():

                #process_single_item(asset_data, sync_uuid)

                ## Check for assets that do not appear in API (i.e. have been deleted)
                ## Use some kind of flag in the db to delete anything not found in
                ## this run

                ## Report live progress
                #done += 1
                #update_progress(done, count)
        finally:
            pool.close()
            pool.join()
            sync_run.end_time=timezone.now()
            sync_run.save()
            pass

        # 'Delete' any reportable models not containing current sync_guid
        delete_not_synced(Asset, sync_run)
        delete_not_synced(Shape, sync_run)

        sync_run.completed=True
        sync_run.save()
        print "\n...Done!"
