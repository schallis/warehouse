from django.conf.urls import patterns, include, url
from django.contrib import admin

from reporting import views


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^download/$', views.download_csv, name='download_csv'),
    url(r'^domain/(?P<domain>.+)/', views.domain, name='domain'),
)
