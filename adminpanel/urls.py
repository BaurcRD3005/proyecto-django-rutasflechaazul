from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel, name='panel'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('login/', views.login_view, name='admin_login'),
    path('rutas/', views.rutas, name='admin_rutas'),
    path("paradas/", views.paradas, name="admin_paradas"),
    path("crear_parada/", views.crear_parada, name="crear_parada"),
    path("crear_ruta/", views.crear_ruta, name="crear_ruta"),
    path("horarios/", views.horarios_admin, name="admin_horarios"),
    path("crear_horario/", views.crear_horario),
    path("eliminar_horario/<int:id>/", views.eliminar_horario),
    path("eliminar_ruta/<int:id>/", views.eliminar_ruta, name="eliminar_ruta"),
    path("editar_ruta/<int:id>/", views.editar_ruta, name="editar_ruta"),
    path('eliminar_parada/', views.eliminar_parada, name='eliminar_parada'),
    path("editar_horario/<int:id>/", views.editar_horario),
]