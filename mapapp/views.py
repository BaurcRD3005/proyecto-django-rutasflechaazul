import math
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings

from adminpanel.models import Ruta, RutaParada, HorarioRuta, Parada, TarifaRuta


# ==============================
# MAPA PRINCIPAL
# ==============================

def mapa(request):

    rutas = Ruta.objects.all()

    rutas_data = []

    for r in rutas:

        paradas = RutaParada.objects.filter(ruta=r).order_by("orden")

        horario = HorarioRuta.objects.filter(ruta=r).first()

        rutas_data.append({
            "id": r.id,
            "nombre": r.nombre,
            "color": r.color,
            "coordenadas": (
                    json.loads(r.coordenadas)
                    if isinstance(r.coordenadas, str)
                    else r.coordenadas
                    ) if r.coordenadas else [],

            "horario": f"{horario.primer_viaje.strftime('%I:%M %p')} - {horario.ultimo_viaje.strftime('%I:%M %p')}" if horario else None,
            "frecuencia": f"{horario.frecuencia} min" if horario else None,

            "paradas":[
                {
                    "nombre": p.parada.nombre,
                    "lat": p.parada.lat,
                    "lng": p.parada.lng
                }
                for p in paradas
            ]
        })

    return render(request,"mapapp/mapa.html",{
        "rutas": rutas_data,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })


# ==============================
# PAGINAS
# ==============================

def index(request):
    return render(request, "mapapp/index.html")


def resultado(request):
    return render(request, "mapapp/resultado.html")


# ==============================
# ZONAS
# ==============================
def zonas(request):
    paradas = Parada.objects.all()

    paradas_data = [
        {"nombre": p.nombre, "lat": float(p.lat), "lng": float(p.lng)}
        for p in paradas
    ]

    return render(request, "mapapp/zonas.html", {
        "paradas_json": json.dumps(paradas_data),
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })



# ==============================
# BUSCAR RUTAS POR UBICACION
# ==============================

def buscar_rutas(request):

    lat = float(request.GET.get("lat"))
    lng = float(request.GET.get("lng"))

    paradas = Parada.objects.all()

    parada_cercana = None
    distancia_min = 999

    for p in paradas:

        d = math.sqrt((p.lat - lat)**2 + (p.lng - lng)**2)

        if d < distancia_min:
            distancia_min = d
            parada_cercana = p

    if not parada_cercana:
        return JsonResponse({"error": "No parada cercana"})

    ruta_parada = RutaParada.objects.filter(parada=parada_cercana).first()

    if not ruta_parada:
        return JsonResponse({"error": "No hay ruta"})

    ruta = ruta_parada.ruta

    paradas_ruta = RutaParada.objects.filter(ruta=ruta).order_by("orden")

    return JsonResponse({
        "parada_cercana": {
            "nombre": parada_cercana.nombre,
            "lat": parada_cercana.lat,
            "lng": parada_cercana.lng
        },
        "ruta": {
            "nombre": ruta.nombre,
            "color": ruta.color,
             "coordenadas": ruta.coordenadas,
            "paradas": [
                {
                    "nombre": rp.parada.nombre,
                    "lat": rp.parada.lat,
                    "lng": rp.parada.lng
                }
                for rp in paradas_ruta
            ]
        }
    })

# ==============================
# BUSCAR ZONA
# ==============================
def buscar_zona(request):
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    zona = request.GET.get("zona")
    direccion = request.GET.get("direccion")  # NUEVO: origen/destino seleccionado

    if not zona:
        return JsonResponse({"error": "Destino requerido"})

    parada_destino = Parada.objects.filter(nombre__icontains=zona.strip()).first()
    if not parada_destino:
        return JsonResponse({"error": "Destino no encontrado"})

    # Filtrar rutas que tengan esta parada como parte de la ruta
    rutas_posibles = RutaParada.objects.filter(parada=parada_destino)
    if direccion:
        rutas_posibles = rutas_posibles.filter(ruta__destino__iexact=direccion.strip())

    ruta_parada_destino = rutas_posibles.first()
    if not ruta_parada_destino:
        return JsonResponse({"error": "Destino sin ruta para esa dirección"})

    ruta = ruta_parada_destino.ruta
    paradas_ruta = list(RutaParada.objects.filter(ruta=ruta).order_by("orden"))

    # Buscar parada origen más cercana
    parada_origen = None
    if lat and lng:
        lat, lng = float(lat), float(lng)
        distancia_min = float('inf')
        for p in paradas_ruta:
            d = math.sqrt((p.parada.lat - lat)**2 + (p.parada.lng - lng)**2)
            if d < distancia_min:
                distancia_min = d
                parada_origen = p

    if not parada_origen:
        parada_origen = ruta_parada_destino

    orden_origen = parada_origen.orden
    orden_destino = ruta_parada_destino.orden

    # Filtrar tramo según orden
    if orden_origen <= orden_destino:
        tramo = [p for p in paradas_ruta if orden_origen <= p.orden <= orden_destino]
    else:
        tramo = [p for p in paradas_ruta if orden_destino <= p.orden <= orden_origen]

    paradas = [
        {"nombre": p.parada.nombre, "lat": p.parada.lat, "lng": p.parada.lng}
        for p in tramo
    ]

    coordenadas = json.loads(ruta.coordenadas) if isinstance(ruta.coordenadas, str) else ruta.coordenadas or []

    return JsonResponse({
        "ruta": ruta.nombre,
        "color": ruta.color,
        "coordenadas": coordenadas,
        "paradas": paradas
    })
    
# ==============================
# HORARIOS + TARIFAS
# ==============================

def horarios(request):

    horarios = HorarioRuta.objects.select_related(
        "ruta",
        "origen",
        "destino"
    )

    tarifas = TarifaRuta.objects.select_related("ruta", "origen", "destino")

    # diccionario por ruta + origen + destino
    tarifas_dict = {
        (t.ruta_id, t.origen_id, t.destino_id): t
        for t in tarifas
    }

    datos = []

    for h in horarios:

        tarifa = tarifas_dict.get((h.ruta_id, h.origen_id, h.destino_id))

        datos.append({
            "ruta__nombre": h.ruta.nombre if h.ruta else "",
            "origen__nombre": h.origen.nombre,
            "destino__nombre": h.destino.nombre,
            "primer_viaje": str(h.primer_viaje),
            "ultimo_viaje": str(h.ultimo_viaje),
            "frecuencia": h.frecuencia,
            "tarifa": float(tarifa.tarifa) if tarifa else 0,
            "descuento": float(tarifa.descuento) if tarifa else 0,
        })

    return render(request, "mapapp/horarios.html", {
        "horarios_json": datos
    })
