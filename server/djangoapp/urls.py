from django.urls import path
from . import views

app_name = 'djangoapp'
urlpatterns = [
    path('session', views.session_user),
    path('login', views.login_user),
    path('logout', views.logout_user),
    path('registration', views.register_user),
    path('get_dealers', views.dealers),
    path('get_dealers/<str:state>', views.dealers),
    path('get_dealer_details/<int:dealer_id>', views.dealer_details),
    path('get_dealer_reviews/<int:dealer_id>', views.dealer_reviews),
    path('get_cars', views.cars),
    path('analyze/<str:text>', views.analyze),
    path('add_review', views.add_review),
]
