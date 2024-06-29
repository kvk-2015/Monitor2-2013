from django.conf.urls import patterns, include, url
from django.views.decorators.cache import cache_control
from ups_statistics.views import UPSStatisticsPageView

urlpatterns = patterns('',
    url(r'(?:^$|^(?P<year>20\d{2})-(?P<month>(?:0?[1-9]|1[0-2]))-(?P<day>(?:0?[1-9]|[12]\d|3[01]))/(?:(?P<hour>(?:[01]?\d|2[0-3]))/)?)$',
        UPSStatisticsPageView.as_view()),
    url(r'^(?P<hour_group>\d+)/$', cache_control(max_age=345600)(UPSStatisticsPageView.as_view()), name='ups_statistics_on_hour_group'),
)