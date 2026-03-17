from django.contrib import admin
from .models import Ruta, Parada, RutaParada, HorarioRuta, ActividadReciente

admin.site.register(Ruta)
admin.site.register(Parada)
admin.site.register(RutaParada)
admin.site.register(HorarioRuta)
admin.site.register(ActividadReciente)