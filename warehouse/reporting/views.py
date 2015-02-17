from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template.context import RequestContext
from django.db.models import Count, Sum, Max
from django.contrib import admin

from reporting.models import Asset, SyncRun, Site


def domain(request, domain):
    sync_runs = SyncRun.objects.filter(site__domain=domain).order_by('-start_time')
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
    size_by_site = all_sites.values('domain') \
            .annotate(
                transcodes=Count('asset__shape'),
                size=Sum('asset__shape__size'),
                count=Count('asset', distinct=True),
                uploaders=Count('asset__username', distinct=True)) \
            .order_by('-size')
    sizes = all_sites.aggregate(
                count=Count('asset', distinct=True),
                transcodes=Count('asset__shape'),
                size=Sum('asset__shape__size'),
                uploaders=Count('asset__username', distinct=True))
    top_uploaders = all_sites.values('domain', 'asset__username') \
            .annotate(count=Count('asset')).order_by('-count')[:20]

    params = {
        'site_header': admin.site.site_header,
        'last_sync': last_sync,
        'last_syncs': sync_runs[:5],
        'sizes': sizes,
        'size_by_site': size_by_site,
        'top_uploaders': top_uploaders,
    }

    return render(request, 'reporting/dashboard.html', params,
                  context_instance=RequestContext(request))
