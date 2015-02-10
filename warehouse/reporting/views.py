from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template.context import RequestContext

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
    params = {'is_running': is_task_running()}

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
