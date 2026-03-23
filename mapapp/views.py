import math
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_GET

from adminpanel.models import Ruta, RutaParada, HorarioRuta, Parada, TarifaRuta


# ==============================
# UTILIDADES
# ==============================

def calcular_distancia(lat1, lng1, lat2, lng2):
    """Distancia en km (Haversine)"""
    R = 6371

    dLat = math.radians(lat2 - lat1)
    dLng = math.radians(lng2 - lng1)

    a = (
        math.sin(dLat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dLng / 2) ** 2
    )

    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parsear_coordenadas(coordenadas):
    if not coordenadas:
        return []
    if isinstance(coordenadas, str):
        return json.loads(coordenadas)
    return coordenadas


# ==============================
# VISTAS PRINCIPALES
# ==============================

def index(request):
    return render(request, "mapapp/index.html")


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
            "coordenadas": parsear_coordenadas(r.coordenadas),

            "horario": (
                f"{horario.primer_viaje.strftime('%I:%M %p')} - "
                f"{horario.ultimo_viaje.strftime('%I:%M %p')}"
                if horario else None
            ),
            "frecuencia": f"{horario.frecuencia} min" if horario else None,

            "paradas": [
                {
                    "nombre": p.parada.nombre,
                    "lat": float(p.parada.lat),
                    "lng": float(p.parada.lng),
                }
                for p in paradas
            ]
        })

    return render(request, "mapapp/mapa.html", {
        "rutas": rutas_data,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })


def zonas(request):
    # Usar modelos de adminpanel
    from adminpanel.models import Parada, HorarioRuta, TarifaRuta
    
    paradas = Parada.objects.all()
    horarios = HorarioRuta.objects.select_related("ruta", "origen", "destino")
    tarifas = TarifaRuta.objects.select_related("ruta", "origen", "destino")

    tarifas_dict = {
        (t.ruta_id, t.origen_id, t.destino_id): t
        for t in tarifas
    }

    data_horarios = []

    for h in horarios:
        tarifa = tarifas_dict.get((h.ruta_id, h.origen_id, h.destino_id))

        data_horarios.append({
            "ruta": h.ruta.nombre,
            "origen": h.origen.nombre,
            "destino": h.destino.nombre,
            "primer_viaje": str(h.primer_viaje),
            "ultimo_viaje": str(h.ultimo_viaje),
            "frecuencia": h.frecuencia,
            "tarifa": float(tarifa.tarifa) if tarifa else 0,
            "descuento": float(tarifa.descuento) if tarifa else 0,
        })

    data_paradas = [
        {
            "nombre": p.nombre,
            "lat": float(p.lat),
            "lng": float(p.lng),
            "sentido": p.sentido if p.sentido else "Sin sentido"
        }
        for p in paradas
    ]

    return render(request, "mapapp/zonas.html", {
        "paradas_json": data_paradas,
        "horarios_json": data_horarios,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })


def resultado(request):
    return render(request, "mapapp/resultado.html")


# ==============================
# API: BUSCAR RUTA
# ==============================

@require_GET
def buscar_zona(request):
    destino_input = request.GET.get("zona")
    origen_input = request.GET.get("origen")
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")

    if not destino_input:
        return JsonResponse({"error": "Destino requerido"}, status=400)

    destino_limpio = destino_input.strip().lower()
    
    # Variable para almacenar todas las rutas posibles
    rutas_encontradas = []
    
    rutas = Ruta.objects.all()

    for ruta in rutas:
        paradas_ruta = list(
            RutaParada.objects.filter(ruta=ruta).order_by("orden")
        )
        
        # Buscar coincidencias de destino
        destinos = [
            p for p in paradas_ruta
            if destino_limpio in p.parada.nombre.lower()
        ]
        
        if not destinos:
            continue
        
        # Buscar origen
        origenes = []
        
        # CASO 1: ubicación actual
        if lat and lng:
            lat_f, lng_f = float(lat), float(lng)
            parada_cercana = min(
                paradas_ruta,
                key=lambda p: calcular_distancia(
                    lat_f, lng_f,
                    float(p.parada.lat),
                    float(p.parada.lng)
                )
            )
            origenes = [parada_cercana]
        
        # CASO 2: origen escrito
        elif origen_input:
            origen_limpio = origen_input.strip().lower()
            origenes = [
                p for p in paradas_ruta
                if origen_limpio in p.parada.nombre.lower()
            ]
        
        # CASO 3: fallback
        else:
            origenes = [paradas_ruta[0]]
        
        # Buscar combinaciones válidas
        for o in origenes:
            for d in destinos:
                idx_origen = paradas_ruta.index(o)
                idx_destino = paradas_ruta.index(d)
                
                # Permitir ambos sentidos de la ruta
                if idx_origen != idx_destino:  # No son la misma parada
                    rutas_encontradas.append({
                        "ruta": ruta,
                        "paradas": paradas_ruta,
                        "origen": o,
                        "destino": d,
                        "idx_origen": idx_origen,
                        "idx_destino": idx_destino,
                        "sentido": "ida" if idx_origen < idx_destino else "vuelta"
                    })
    
    if not rutas_encontradas:
        return JsonResponse({
            "error": f"No se encontró una ruta entre '{origen_input}' y '{destino_input}'. Verifica que ambas paradas pertenezcan a la misma ruta."
        }, status=404)
    
    # Ordenar por proximidad (priorizar rutas con origen antes que destino)
    rutas_encontradas.sort(key=lambda x: (
        0 if x["sentido"] == "ida" else 1,  # Priorizar ida
        abs(x["idx_destino"] - x["idx_origen"])  # Menor distancia entre paradas
    ))
    
    mejor = rutas_encontradas[0]
    
    # Obtener los vértices personalizados de la ruta (si existen)
    vertices = parsear_coordenadas(mejor["ruta"].coordenadas)
    
    # Si el origen está después del destino, invertir la lista de paradas
    if mejor["idx_origen"] > mejor["idx_destino"]:
        paradas_recortadas = mejor["paradas"][mejor["idx_destino"]:mejor["idx_origen"] + 1]
        paradas_recortadas.reverse()
        # Para el JSON, usamos el orden correcto
        paradas_para_json = [{
            "nombre": p.parada.nombre,
            "lat": float(p.parada.lat),
            "lng": float(p.parada.lng)
        } for p in paradas_recortadas]
        
        # Si hay vértices, también los invertimos para mantener el orden correcto
        if vertices:
            vertices = list(reversed(vertices))
    else:
        paradas_para_json = [{
            "nombre": p.parada.nombre,
            "lat": float(p.parada.lat),
            "lng": float(p.parada.lng)
        } for p in mejor["paradas"][mejor["idx_origen"]:mejor["idx_destino"] + 1]]
    
    # Preparar la respuesta
    response_data = {
        "ruta": mejor["ruta"].nombre,
        "color": mejor["ruta"].color,
        "paradas": [{
            "nombre": p.parada.nombre,
            "lat": float(p.parada.lat),
            "lng": float(p.parada.lng)
        } for p in mejor["paradas"]],
        "origen": mejor["origen"].parada.nombre,
        "destino": mejor["destino"].parada.nombre,
        "sentido": mejor["sentido"]
    }
    
    # Añadir vértices si existen (igual que en mapa.html)
    if vertices:
        response_data["vertices"] = [{
            "lat": float(v["lat"]),
            "lng": float(v["lng"])
        } for v in vertices]
    
    return JsonResponse(response_data)
    
# ==============================
# HORARIOS + TARIFAS
# ==============================

def horarios(request):

    horarios = HorarioRuta.objects.select_related(
        "ruta", "origen", "destino"
    )

    tarifas = TarifaRuta.objects.select_related(
        "ruta", "origen", "destino"
    )

    tarifas_dict = {
        (t.ruta_id, t.origen_id, t.destino_id): t
        for t in tarifas
    }

    data = []

    for h in horarios:
        tarifa = tarifas_dict.get(
            (h.ruta_id, h.origen_id, h.destino_id)
        )

        data.append({
            "ruta": h.ruta.nombre,
            "origen": h.origen.nombre,
            "destino": h.destino.nombre,
            "primer_viaje": str(h.primer_viaje),
            "ultimo_viaje": str(h.ultimo_viaje),
            "frecuencia": h.frecuencia,
            "tarifa": float(tarifa.tarifa) if tarifa else 0,
            "descuento": float(tarifa.descuento) if tarifa else 0,
        })

    return render(request, "mapapp/horarios.html", {
        "horarios": horarios, 
        "horarios_json": data
    })