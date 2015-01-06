import csv
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from collections import OrderedDict

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from django.db.models import F, Max
from django.contrib.sites.models import Site

from reporting import models, utils


class CSVReport(object):
    """An abstract csv serialisable report"""

    columns = {}
    extra_columns = {}

    def __init__(self, start=None, end=None, site=None):
        self.file = NamedTemporaryFile(delete=False)
        self.writer = csv.writer(self.file, dialect=csv.excel)
        if not end:
            end = datetime.now()
        if not start:
            start = end - timedelta(100)
        self.start = start
        self.end = end
        self.site = site and Site.objects.get(name=site) or None

    def write_headings(self):
        self.writer.writerow(self.columns.keys() + self.extra_columns.keys())

    def serialise(self):
        """Write report data to `self.file` before returning it

        :returns:
            A temporary file handle containing CSV data
        """
        raise NotImplementedError


class UsageReport(CSVReport):
    """Report each shape for every item ingested in the period

    Also computes a usage metric for the time each shape has been on
    the system (within the period)
    """

    columns = OrderedDict([
        (_('Created'), 'item__created'),
        (_('Item ID'), 'item__vs_id'),
        (_('Shape ID'), 'vs_id'),
        (_('Shape Tag'), 'shapetag'),
        (_('Shape Size'), 'size'),
        (_('Version'), 'version'),
        (_('Filename'), 'item__filename'),
        (_('Username'), 'item__username'),
        (_('Sites'), 'item__sites__name'),
        (_('Deleted On'), 'deleted'),
    ])

    extra_columns = OrderedDict([
        (_('Usage (GB days, to the nearest KB)'), utils.get_usage),
    ])

    def queryset(self):
        shapes = models.Shape.objects.filter(item__created__range=(self.start, self.end))
        if self.site:
            return shapes.filter(item__sites=self.site)
        return shapes

    def serialise(self):
        self.write_headings()

        for row in self.queryset().values(*self.columns.values()):
            orig_row = row.copy()
            row['size'] = utils.filesizeformat(row['size'])
            new_row = [row[c] for c in self.columns.values()]

            # Add extra computed columns
            for key, func in self.extra_columns.items():
                new_row.append(func(orig_row, self.start, self.end))

            self.writer.writerow(new_row)

        print self.file.name

        self.file.flush()
        self.file.close()
        return self.file


class IngestShapeReport(CSVReport):
    """Report all shapes ingested

    NOTE: This will miss ingests that have no shapes
    """

    columns = OrderedDict([
        (_('Ingested'), 'item__created'),
        (_('User'), 'item__username'),
        (_('Item ID'), 'item__vs_id'),
        (_('Shape ID'), 'vs_id'),
        (_('Version'), 'version'),
        (_('Sites'), 'item__sites__name'),
        (_('Filename'), 'item__filename'),
        (_('Size'), 'item__size'),
    ])

    def queryset(self):
        items = models.Shape.objects.filter(item__created__range=(self.start, self.end))
        if self.site:
            return items.filter(item__sites=self.site)
        return items

    def serialise(self):
        self.write_headings()

        for row in self.queryset().values(*self.columns.values()):
            new_row = [row[c] for c in self.columns.values()]

            self.writer.writerow(new_row)

        print self.file.name

        self.file.flush()
        self.file.close()
        return self.file


class IngestReport(CSVReport):
    """Report all items ingested, excluding versions
    """

    columns = OrderedDict([
        (_('Ingested'), 'created'),
        (_('User'), 'username'),
        (_('Item ID'), 'vs_id'),
        (_('Versions'), 'versions'),
        (_('Sites'), 'sites__name'),
        (_('Filename'), 'filename'),
        (_('Size'), 'size'),
    ])

    def queryset(self):
        items = models.Asset.objects.filter(created__range=(self.start, self.end))
        items = items.order_by('created')
        items = items.annotate(versions=Max('shape__version'))
        if self.site:
            return items.filter(sites=self.site)
        return items

    def serialise(self):
        self.write_headings()

        for row in self.queryset().values(*self.columns.values()):
            row['size'] = utils.filesizeformat(row['size'])
            new_row = [row[c] for c in self.columns.values()]
            self.writer.writerow(new_row)

        print self.file.name

        self.file.flush()
        self.file.close()
        return self.file


class DownloadReport(CSVReport):

    columns = OrderedDict([
        (_('When'), 'when'),
        (_('User'), 'username'),
        (_('Item ID'), 'item__vs_id'),
        (_('Shape ID'), 'shape__vs_id'),
        (_('Shape Tag'), 'shape__shapetag'),
        (_('Version'), 'shape__version'),
        (_('Sites'), 'item__sites__name'),
        (_('Size'), 'shape__size'),
        (_('Filename'), 'item__filename'),
    ])

    def queryset(self):
        downloads = models.Download.objects.filter(when__range=(self.start, self.end))
        if self.site:
            return downloads.filter(item__sites=self.site)
        return downloads

    def serialise(self):
        self.write_headings()

        for row in self.queryset().values(*self.columns.values()):
            row['shape__size'] = utils.filesizeformat(row['shape__size'])
            new_row = [row[c] for c in self.columns.values()]
            self.writer.writerow(new_row)

        print self.file.name

        self.file.flush()
        self.file.close()
        return self.file
