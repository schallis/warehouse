from cStringIO import StringIO
import json

from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template.context import RequestContext
from django.db import connection
from django.db.models import Count, Sum, Max, F
from django.contrib import admin
from django.core.urlresolvers import reverse

from reporting.models import Asset, SyncRun, Site


def domain(request, domain):
    sync_runs = SyncRun.objects.filter(site__domain__contains=domain).order_by('-start_time')
    try:
        last_sync = sync_runs.filter(completed=True)[0]
    except IndexError:
        last_sync = None

    all_sites = Site.objects.filter(domain=domain)
    size_by_site = all_sites.values('domain') \
            .annotate(
                transcodes=Count('asset__shape'),
                size=Sum('asset__shape__size'),
                count=Count('asset', distinct=True),
                uploaders=Count('asset__username', distinct=True)) \
            .order_by('-size')
    top_uploaders = all_sites.values('domain', 'asset__username') \
            .annotate(count=Count('asset')).order_by('-count')[:20]

    params = {
        'domain': domain,
        'site_header': admin.site.site_header + " for " + domain,
        'last_sync': last_sync,
        'last_syncs': sync_runs[:5],
        'size_by_site': size_by_site,
        'top_uploaders': top_uploaders,
    }


    return render(request, 'reporting/domain.html', params,
                  context_instance=RequestContext(request))


def download_csv(domain):
    csv_file = StringIO()

    # Postgres generates CSV for us, we just serve it directly to the user
    raw_sql = """COPY
    (SELECT
        id,
        raw_data::json->'metadata'->>'zonza_site' as "Sites",
        raw_data::json->'metadata'->>'trials_category' as "Category"
    FROM reporting_asset)
    TO STDOUT CSV HEADER;"""
    cursor = connection.cursor()
    cursor.copy_expert(raw_sql, csv_file)

    filename = 'zonza-asset-report.csv'
    response = HttpResponse(csv_file.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    return response


#@staff_member_required
def dashboard(request):
    """Give a snapshot of the status of the reporting app"""
    sync_runs = SyncRun.objects.all().order_by('-start_time')
    try:
        last_sync = sync_runs.filter(completed=True)[0]
    except IndexError:
        last_sync = None

    all_sites = Site.objects.all()
    #num_assets_by_site = all_sites.values('domain') \
            #.annotate(count=Count('asset')).order_by('-count')
    #num_uploaders_by_site = all_sites.values('domain') \
            #.annotate(uploaders=Count('asset__username', distinct=True))
    # TODO: add days since last since per site
    size_by_site = all_sites.values('domain') \
            .annotate(
                transcodes=Count('asset__shape'),
                size=Sum('asset__shape__size'),
                count=Count('asset', distinct=True),
                uploaders=Count('asset__username', distinct=True)) \
            .order_by('-count')[:10]
    sizes = all_sites.aggregate(
                count=Count('asset', distinct=True),
                transcodes=Count('asset__shape'),
                size=Sum('asset__shape__size'),
                uploaders=Count('asset__username', distinct=True))
    top_uploaders = all_sites.values('domain', 'asset__username') \
            .annotate(count=Count('asset')).order_by('-count')[:10]
    x = [x for x in all_sites.values('domain')
            .annotate(size=Count('asset', distinct=True))
            .annotate(total=Sum('asset__shape__size'))
            .order_by('-size')  # TODO: Figure out why sorting by total is buggy
            .values_list('domain', 'size')]
    graph_assets_data = x[:5]
    graph_assets_data = [[x,y,reverse('reporting.views.domain', args=(x,))]
                         for x, y in graph_assets_data]
    # [["teamhills.zonza.tv", null], ["deluxe.zonza.tv", null], ["trials.zonza.tv", 243497942962], ["grey.zonza.tv", 135888998176], ["230pas.zonza.tv", 48393166596], ["zonzacompany.zonza.tv", 5456789214], ["trg-deluxe.zonza.tv", 2953964488], ["gmi-deluxe.zonza.tv", 2182796439]]'

    params = {
        'site_header': admin.site.site_header,
        'last_sync': last_sync,
        'last_syncs': sync_runs[:5],
        'sizes': sizes,
        'sizes_json': json.dumps(sizes),
        'size_by_site': size_by_site,
        'top_uploaders': top_uploaders,
        'graph_assets_data': json.dumps(graph_assets_data)
    }

    return render(request, 'reporting/dashboard.html', params,
                  context_instance=RequestContext(request))
