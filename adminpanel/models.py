from django.db import models
from django.utils import timezone

# Create your models here.

class Ruta(models.Model):
    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default="#ff0000")
    coordenadas = models.JSONField(default=list)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    paradas = models.ManyToManyField(
        "Parada",
        through="RutaParada"
    )

    def __str__(self):
        return self.nombre


class Parada(models.Model):
    nombre = models.CharField(max_length=150)
    lat = models.FloatField()
    lng = models.FloatField()

    def __str__(self):
        return self.nombre


class RutaParada(models.Model):
    ruta = models.ForeignKey(
    Ruta,
    on_delete=models.CASCADE,
    related_name="ruta_paradas"
    )
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    orden = models.IntegerField()

    class Meta:
        ordering = ["orden"]

from django.db import models

class HorarioRuta(models.Model):

    ruta = models.ForeignKey(
        "Ruta",
        on_delete=models.CASCADE,
        related_name="horarios",
        null=True,
        blank=True
    )

    origen = models.ForeignKey(
        "Parada",
        on_delete=models.CASCADE,
        related_name="origen_ruta"
    )

    destino = models.ForeignKey(
        "Parada",
        on_delete=models.CASCADE,
        related_name="destino_ruta"
    )

    primer_viaje = models.TimeField()
    ultimo_viaje = models.TimeField()

    frecuencia = models.CharField(max_length=50)

    tarifa = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    descuento = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"{self.ruta.nombre if self.ruta else 'Sin ruta'} | {self.origen.nombre} → {self.destino.nombre}"
    

from django.db import models
from django.contrib.auth.models import User

class ActividadReciente(models.Model):
    ACCIONES = [
        ('add_parada', 'Agregar Parada'),
        ('edit_parada', 'Editar Parada'),
        ('delete_parada', 'Eliminar Parada'),
        ('add_ruta', 'Agregar Ruta'),
        ('edit_ruta', 'Editar Ruta'),
        ('delete_ruta', 'Eliminar Ruta'),
        ('edit_horario', 'Modificar Horario'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    accion = models.CharField(max_length=50, choices=ACCIONES)
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)

    descripcion = models.TextField(blank=True)  # opcional, para detalle extra

    class Meta:
        ordering = ['-fecha', '-hora']

    def __str__(self):
        return f"{self.usuario} - {self.get_accion_display()} ({self.fecha} {self.hora})"
    
