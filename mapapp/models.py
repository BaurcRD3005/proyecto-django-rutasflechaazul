from django.db import models

# Create your models here.

class Ruta(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Parada(models.Model):
    nombre = models.CharField(max_length=100)
    latitud = models.FloatField()
    longitud = models.FloatField()
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="paradas")

    def __str__(self):
        return self.nombre
        