from django.contrib import admin
from django.urls import include, path
from djangoapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('djangoapp/', include('djangoapp.urls')),
    path('about', views.info_page, {'filename': 'About.html'}),
    path('contact', views.info_page, {'filename': 'Contact.html'}),
    path('', views.frontend),
    path('dealers', views.frontend),
    path('login', views.frontend),
    path('register', views.frontend),
    path('dealer/<int:dealer_id>', views.frontend),
    path('dealer/<int:dealer_id>/review', views.frontend),
]
