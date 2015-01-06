from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from reporting import urls as reporting_urls

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'vidiwarehouse.views.home', name='home'),
    # url(r'^vidiwarehouse/', include('vidiwarehouse.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(reporting_urls)),
)
