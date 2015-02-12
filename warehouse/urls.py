from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()
import debug_toolbar

from reporting import urls as reporting_urls


admin.site.site_header = 'ZONZA Reporting'

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(reporting_urls)),
)
