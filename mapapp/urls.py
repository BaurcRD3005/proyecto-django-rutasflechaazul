from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("mapa/", views.mapa, name="mapa"),
    path("resultado/", views.resultado, name="resultado"),
    path("horarios/", views.horarios, name="horarios"),
    path("zonas/", views.zonas, name="zonas"),
    path('buscar_zona/', views.buscar_zona, name='buscar_zona'),
]