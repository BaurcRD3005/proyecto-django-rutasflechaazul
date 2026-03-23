from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Ruta(models.Model):

    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default="#ff0000")
    coordenadas = models.JSONField(blank=True, null=True)

    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    paradas = models.ManyToManyField(
        "Parada",
        through="RutaParada"
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# models.py - Agregar campo sentido a Parada

class Parada(models.Model):
    nombre = models.CharField(max_length=150)
    lat = models.FloatField()
    lng = models.FloatField()
    sentido = models.CharField(max_length=100, blank=True, null=True)  # Campo abierto para el sentido
    
    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RutaParada(models.Model):

    ruta = models.ForeignKey(
        Ruta,
        on_delete=models.CASCADE,
        related_name="ruta_paradas"
    )

    parada = models.ForeignKey(
        Parada,
        on_delete=models.CASCADE,
        related_name="parada_rutas"
    )

    orden = models.IntegerField()

    class Meta:
        ordering = ["orden"]
        unique_together = ("ruta", "parada")

    def __str__(self):
        return f"{self.ruta.nombre} - {self.parada.nombre} ({self.orden})"


class HorarioRuta(models.Model):

    ruta = models.ForeignKey(
        Ruta,
        on_delete=models.CASCADE,
        related_name="horarios",
        null=True,
        blank=True
    )

    origen = models.ForeignKey(
        Parada,
        on_delete=models.CASCADE,
        related_name="horarios_origen"
    )

    destino = models.ForeignKey(
        Parada,
        on_delete=models.CASCADE,
        related_name="horarios_destino"
    )

    primer_viaje = models.TimeField()
    ultimo_viaje = models.TimeField()

    frecuencia = models.IntegerField(
        help_text="Frecuencia en minutos"
    )

    class Meta:
        ordering = ["ruta", "origen"]
        unique_together = ("ruta", "origen", "destino")

    def __str__(self):

        ruta_nombre = self.ruta.nombre if self.ruta else "Sin ruta"

        return f"{ruta_nombre} | {self.origen.nombre} → {self.destino.nombre}"


class TarifaRuta(models.Model):

    ruta = models.ForeignKey(
        Ruta,
        on_delete=models.CASCADE,
        related_name="tarifas"
    )

    origen = models.ForeignKey(
        Parada,
        on_delete=models.CASCADE,
        related_name="tarifas_origen"
    )

    destino = models.ForeignKey(
        Parada,
        on_delete=models.CASCADE,
        related_name="tarifas_destino"
    )

    tarifa = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    descuento = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ["ruta"]
        unique_together = ("ruta", "origen", "destino")

    def __str__(self):

        return f"{self.ruta.nombre} | {self.origen.nombre} → {self.destino.nombre} | ${self.tarifa}"


class ActividadReciente(models.Model):

    ACCIONES = [
        ('add_parada', 'Agregar Parada'),
        ('edit_parada', 'Editar Parada'),
        ('delete_parada', 'Eliminar Parada'),

        ('add_ruta', 'Agregar Ruta'),
        ('edit_ruta', 'Editar Ruta'),
        ('delete_ruta', 'Eliminar Ruta'),

        ('edit_horario', 'Modificar Horario'),

        ('add_tarifa', 'Agregar Tarifa'),
        ('edit_tarifa', 'Editar Tarifa'),
        ('delete_tarifa', 'Eliminar Tarifa'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    accion = models.CharField(
        max_length=50,
        choices=ACCIONES
    )

    descripcion = models.TextField(blank=True)

    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-hora']

    def __str__(self):

        return f"{self.usuario} - {self.get_accion_display()} ({self.fecha} {self.hora})"
    