from django.conf.urls import include, url

urlpatterns = [
    url(r'^publisher/', include('publisher.views')),
]
