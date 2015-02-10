import logging

#from celery.task import PeriodicTask
#from celery.schedules import crontab
#from celery.registry import tasks

from django.utils import timezone

from reporting.models import Asset

log = logging.getLogger(__name__)

PERCENTILES = 100


#class SyncReportDataTask(PeriodicTask):
    #"""Called asynchronously by CeleryBeat Scheduler"""

    #name = "reporting.tasks.SyncReportDataTask"
    #routing_key = "celery"
    #run_every = crontab(hour="4")

    #def run(self, hours=24, **kwargs):

        #log.debug('SyncReportDataTask: Started at {0}'.format(
                #timezone.now().isoformat()))

        #objects = Asset.vidispine_objects.all()
        #count = objects.count()
        #done = 0

        #for item in objects:
            #done += 1
            #self.update_progress(done, count)

    #def update_progress(self, done, count):
        #percentiles = [int(count * percentile / PERCENTILES)
                       #for percentile in range(0, PERCENTILES + 1)]
        #if done in percentiles:
            #log.debug('SyncReportDataTask: {0}% ({1}/{2})'.format(
                    #int(PERCENTILES * done / count), done, count))

#tasks.register(SyncReportDataTask)
