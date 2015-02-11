from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template.context import RequestContext
from django.db.models import Count, Sum, Max

from reporting.models import Asset, SyncRun, Site

#from reporting.tasks import SyncReportDataTask


def is_task_running():
    """Checks whether a reporting.tasks.SyncReportDataTask is running"""
    #active = inspect().active()
    #if active:
        #for host in active.values():
            #for task in host:
                #if (task.get(u'name', u'') ==
                    #u'reporting.tasks.SyncReportDataTask'):
                    #return True
    return False


@staff_member_required
def dashboard(request):
    """Give a snapshot of the status of the reporting app"""
    sync_runs = SyncRun.objects.all().order_by('-start_time')
    try:
        last_sync = sync_runs.filter(completed=True)[0]
    except IndexError:
        last_sync = None

    all_sites = Site.objects.all()
    num_assets_by_site = all_sites.values('domain') \
            .annotate(count=Count('asset')).order_by('-count')
    size_by_site = all_sites.values('domain') \
            .annotate(size=Sum('asset__shape__size')).annotate(count=Count('asset')).order_by('-size')
    top_uploaders = all_sites.values('domain', 'asset__username') \
            .annotate(count=Count('asset')).order_by('-count')[:20]

    params = {
        'last_sync': last_sync,
        'last_syncs': sync_runs[:5],
        'is_running': is_task_running(),
        'num_assets_by_site': num_assets_by_site,
        'size_by_site': size_by_site,
        'top_uploaders': top_uploaders,
    }

    return render(request,
                  'reporting/dashboard.html',
                  params,
                  context_instance=RequestContext(request))


@staff_member_required
def run_task(request):
    """Activate the task"""
    #if is_task_running():
        #messages.error(request, "Task is already running!")
    #else:
        #task = SyncReportDataTask()
        #task.delay()
        #messages.success(request, "Task started!")

    return redirect('dashboard')
