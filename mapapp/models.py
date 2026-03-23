from django.db import models

class Ruta(models.Model):
    nombre = models.CharField(max_length=100)
    origen = models.CharField(max_length=100, default="Tlaxcala")
    destino = models.CharField(max_length=100, default="Puebla")
    color = models.CharField(max_length=7, default="#2563eb")

    def __str__(self):
        return f"{self.nombre} ({self.origen} → {self.destino})"


class Parada(models.Model):
    nombre = models.CharField(max_length=100)
    lat = models.FloatField()
    lng = models.FloatField()
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="paradas")
    sentido = models.CharField(max_length=100, blank=True, null=True)  # Campo agregado
    
    def __str__(self):
        if self.sentido:
            return f"{self.nombre} (Hacia: {self.sentido})"
        return self.nombre