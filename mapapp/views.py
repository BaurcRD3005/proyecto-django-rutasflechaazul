import math
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings

from adminpanel.models import Ruta, RutaParada, HorarioRuta, Parada

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


def index(request):
    return render(request, "mapapp/index.html")


def resultado(request):
    return render(request, "mapapp/resultado.html")


def zonas(request):

    paradas = Parada.objects.all()

    datos_paradas = []

    for p in paradas:
        datos_paradas.append({
            "nombre": p.nombre,
            "lat": p.lat,
            "lng": p.lng
        })

    context = {
        "paradas_json": json.dumps(datos_paradas)
    }

    return render(request, "mapapp/zonas.html", context)


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



from django.http import JsonResponse

def buscar_zona(request):

    zona = request.GET.get("zona")

    # buscar la parada destino
    parada = Parada.objects.filter(nombre__icontains=zona).first()

    if not parada:
        return JsonResponse({"error": "No encontrado"})

    # buscar la ruta que pasa por esa parada
    ruta_parada = RutaParada.objects.filter(parada=parada).first()

    if not ruta_parada:
        return JsonResponse({"error": "Ruta no encontrada"})

    ruta = ruta_parada.ruta

    # obtener TODAS las paradas de la ruta
    paradas_ruta = RutaParada.objects.filter(ruta=ruta).order_by("orden")

    paradas = []

    for p in paradas_ruta:
        paradas.append({
            "nombre": p.parada.nombre,
            "lat": p.parada.lat,
            "lng": p.parada.lng
        })

    return JsonResponse({
        "ruta": ruta.nombre,
        "color": ruta.color,
        "paradas": paradas
    })


from adminpanel.models import HorarioRuta

def horarios(request):

    horarios_qs = HorarioRuta.objects.select_related(
        "origen",
        "destino",
        "ruta"
    ).values(
        "primer_viaje",
        "ultimo_viaje",
        "frecuencia",
        "tarifa",
        "descuento",
        "ruta__nombre",
        "origen__nombre",
        "destino__nombre"
    )

    horarios_list = list(horarios_qs)

    for h in horarios_list:
        if h["primer_viaje"]:
            h["primer_viaje"] = str(h["primer_viaje"])

        if h["ultimo_viaje"]:
            h["ultimo_viaje"] = str(h["ultimo_viaje"])

        if h["tarifa"]:
            h["tarifa"] = float(h["tarifa"])

        if h["descuento"]:
            h["descuento"] = float(h["descuento"])

    return render(request, "mapapp/horarios.html", {
        "horarios_json": horarios_list   # ⭐ NO usar json.dumps()
    })


