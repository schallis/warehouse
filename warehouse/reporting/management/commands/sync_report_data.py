import sys
from optparse import make_option
from datetime import datetime

from django.core.management.base import BaseCommand

from reporting.models import Asset


def update_progress(current, total):
    progress = int(float(current) * 100 / total)
    complete = progress/10
    message = '\rProgress: [{0}] {1}% ({2}/{3})'
    bar = '#' * complete + ' ' * (10-complete)
    sys.stdout.write(message.format(bar, progress, current, total))
    sys.stdout.flush()


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

        objects = Asset.vidispine_objects.all()
        objects = objects.skip(skip)
        count = objects.count()
        done = 0

        print "Started at {0}".format(datetime.now().isoformat())
        print "Syncing assets and shapes..."
        for item in objects:
            done += 1
            update_progress(done, count)

        print "\n...Done!"
