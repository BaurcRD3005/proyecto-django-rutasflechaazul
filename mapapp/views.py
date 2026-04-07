import math
import json
import re

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_GET
from django.db.models import Q

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


def normalizar_nombre(nombre):
    """Normaliza el nombre para búsqueda flexible"""
    if not nombre:
        return ""
    # Convertir a minúsculas
    nombre = nombre.lower()
    # Eliminar texto entre paréntesis
    nombre = re.sub(r'\([^)]*\)', '', nombre)
    # Eliminar espacios extras
    nombre = ' '.join(nombre.split())
    return nombre.strip()


def buscar_parada_flexible(nombre_busqueda):
    """Busca parada con coincidencia flexible - VERSIÓN MEJORADA"""
    if not nombre_busqueda:
        return None
    
    nombre_busqueda = nombre_busqueda.strip()
    print(f"🔍 Buscando parada: '{nombre_busqueda}'")
    
    # 1. Búsqueda exacta (case insensitive)
    parada = Parada.objects.filter(nombre__iexact=nombre_busqueda).first()
    if parada:
        print(f"  ✅ Encontrada por coincidencia exacta: {parada.nombre}")
        return parada
    
    # 2. Búsqueda que contenga el texto (contiene)
    paradas = Parada.objects.filter(nombre__icontains=nombre_busqueda)
    if paradas.exists():
        print(f"  ✅ Encontradas {paradas.count()} por coincidencia parcial")
        # Si hay varias, elegir la más parecida
        if paradas.count() == 1:
            return paradas.first()
        else:
            # Buscar la que tenga el nombre más similar
            mejor_parada = None
            mejor_ratio = 0
            for p in paradas:
                # Calcular similitud (ratio de caracteres comunes)
                nombre_limpio = re.sub(r'[^\w\s]', '', p.nombre.lower())
                busqueda_limpia = re.sub(r'[^\w\s]', '', nombre_busqueda.lower())
                coincidencias = len(set(nombre_limpio) & set(busqueda_limpia))
                ratio = coincidencias / max(len(busqueda_limpia), 1)
                if ratio > mejor_ratio:
                    mejor_ratio = ratio
                    mejor_parada = p
            print(f"  ✅ Mejor coincidencia: {mejor_parada.nombre} (ratio: {mejor_ratio:.2f})")
            return mejor_parada
    
    # 3. Búsqueda eliminando palabras comunes ("La", "El", "Los", "Las")
    palabras_quitar = ['la', 'el', 'los', 'las', 'de', 'del', 'y', 'a', 'ante', 'bajo']
    nombre_simplificado = nombre_busqueda.lower()
    for palabra in palabras_quitar:
        nombre_simplificado = nombre_simplificado.replace(f" {palabra} ", " ")
        if nombre_simplificado.startswith(f"{palabra} "):
            nombre_simplificado = nombre_simplificado[len(palabra)+1:]
        if nombre_simplificado.endswith(f" {palabra}"):
            nombre_simplificado = nombre_simplificado[:-len(palabra)-1]
    
    if nombre_simplificado != nombre_busqueda.lower():
        print(f"  🔄 Buscando sin palabras comunes: '{nombre_simplificado}'")
        paradas = Parada.objects.filter(
            Q(nombre__icontains=nombre_simplificado) |
            Q(nombre__icontains=nombre_simplificado.replace(" ", ""))
        )
        if paradas.exists():
            print(f"  ✅ Encontrada por búsqueda simplificada: {paradas.first().nombre}")
            return paradas.first()
    
    # 4. Búsqueda por palabras clave (split)
    palabras = nombre_busqueda.lower().split()
    if len(palabras) > 1:
        for palabra in palabras:
            if len(palabra) > 3:  # Ignorar palabras muy cortas
                paradas = Parada.objects.filter(nombre__icontains=palabra)
                if paradas.exists():
                    print(f"  ✅ Encontrada por palabra clave '{palabra}': {paradas.first().nombre}")
                    return paradas.first()
    
    print(f"  ❌ No se encontró ninguna parada para '{nombre_busqueda}'")
    return None


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
                    "sentido": p.parada.sentido if p.parada.sentido else "Sin sentido"
                }
                for p in paradas
            ]
        })

    return render(request, "mapapp/mapa.html", {
        "rutas": rutas_data,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })


def zonas(request):
    from adminpanel.models import Parada, HorarioRuta, TarifaRuta, Ruta
    
    paradas = Parada.objects.all()
    horarios = HorarioRuta.objects.select_related("ruta", "origen", "destino")
    tarifas = TarifaRuta.objects.select_related("ruta", "origen", "destino")
    rutas = Ruta.objects.all()

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
            "id": p.id,  # 🔥 ¡AGREGA ESTA LÍNEA!
            "nombre": p.nombre,
            "lat": float(p.lat),
            "lng": float(p.lng),
            "sentido": p.sentido if p.sentido else "Sin sentido"
        }
        for p in paradas
    ]

    data_rutas = [
        {
            "nombre": r.nombre,
            "color": r.color,
            "coordenadas": parsear_coordenadas(r.coordenadas),
            "paradas": [
                {
                    "nombre": rp.parada.nombre,
                    "lat": float(rp.parada.lat),
                    "lng": float(rp.parada.lng),
                    "orden": rp.orden,
                    "sentido": rp.parada.sentido if rp.parada.sentido else "Sin sentido"
                }
                for rp in RutaParada.objects.filter(ruta=r).order_by("orden")
            ]
        }
        for r in rutas
    ]

    return render(request, "mapapp/zonas.html", {
        "paradas_json": data_paradas,
        "horarios_json": data_horarios,
        "rutas_json": data_rutas,
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
    destino_sentido = request.GET.get("destino_sentido")
    destino_id = request.GET.get("zona_id")
    origen_id = request.GET.get("origen_id")

    print(f"\n{'='*60}")
    print(f"BUSCAR RUTA")
    print(f"{'='*60}")
    print(f"Destino ID: {destino_id}, Nombre: {destino_input}, Sentido: {destino_sentido}")
    print(f"Origen ID: {origen_id}, Nombre: {origen_input}")
    print(f"Ubicación: {lat}, {lng}")

    # 🔥 CORREGIDO: No requerir destino_input si tenemos ID
    if not destino_input and not destino_id:
        return JsonResponse({"error": "Destino requerido"}, status=400)
    
    # 🔥 DIAGNÓSTICO: Mostrar todas las paradas disponibles
    print(f"\n📋 PARADAS DISPONIBLES EN BD:")
    todas_paradas = Parada.objects.all()
    for p in todas_paradas[:10]:
        print(f"  - {p.nombre} (ID: {p.id}, sentido: {p.sentido})")
    print(f"  Total: {todas_paradas.count()} paradas")

    # 🔥 CORREGIDO: Buscar parada destino PRIORIZANDO ID
    parada_destino = None
    
    # 1. Buscar por ID (más preciso)
    if destino_id:
        try:
            parada_destino = Parada.objects.filter(id=int(destino_id)).first()
            if parada_destino:
                print(f"✅ Destino encontrado por ID {destino_id}: {parada_destino.nombre} (sentido: {parada_destino.sentido})")
        except (ValueError, TypeError):
            print(f"⚠️ ID inválido: {destino_id}")
    
    # 2. Si no, buscar por nombre + sentido
    if not parada_destino and destino_input:
        # Buscar por nombre exacto Y sentido
        if destino_sentido and destino_sentido != "Sin sentido":
            parada_destino = Parada.objects.filter(
                nombre__iexact=destino_input,
                sentido=destino_sentido
            ).first()
            if parada_destino:
                print(f"✅ Destino encontrado por nombre+sentido: {parada_destino.nombre}")
        
        # 3. Si aún no, buscar solo por nombre flexible
        if not parada_destino:
            parada_destino = buscar_parada_flexible(destino_input)
            if parada_destino:
                print(f"✅ Destino encontrado por nombre flexible: {parada_destino.nombre}")
    
    if not parada_destino:
        return JsonResponse({
            "error": f"No se encontró la parada destino"
        }, status=404)
    
    print(f"✅ Destino final: {parada_destino.nombre} (ID: {parada_destino.id}, sentido: {parada_destino.sentido})")
    
    # Determinar sentido a usar (priorizar el del frontend)
    sentido_destino = destino_sentido if destino_sentido and destino_sentido != "Sin sentido" else (parada_destino.sentido or "Sin sentido")
    
    # 🔥 CORREGIDO: Buscar origen PRIORIZANDO ID
    parada_origen = None
    usar_ubicacion = False
    parada_origen_buscada = None
    
    # 1. Buscar origen por ID
    if origen_id:
        try:
            parada_origen_buscada = Parada.objects.filter(id=int(origen_id)).first()
            if parada_origen_buscada:
                print(f"✅ Origen encontrado por ID {origen_id}: {parada_origen_buscada.nombre}")
        except (ValueError, TypeError):
            print(f"⚠️ ID de origen inválido: {origen_id}")
    
    # 2. Si no, buscar por nombre
    if not parada_origen_buscada and origen_input and origen_input != "📍 Mi ubicación actual":
        parada_origen_buscada = buscar_parada_flexible(origen_input)
        if parada_origen_buscada:
            print(f"✅ Origen encontrado por nombre: {parada_origen_buscada.nombre}")
    
    # 🔥 Encontrar TODAS las rutas que contienen el destino
    rutas_con_destino = []
    
    for ruta in Ruta.objects.all():
        paradas_ruta = list(RutaParada.objects.filter(ruta=ruta).select_related('parada').order_by("orden"))
        
        # Buscar destino en esta ruta
        idx_destino = -1
        for i, rp in enumerate(paradas_ruta):
            if rp.parada.id == parada_destino.id:
                idx_destino = i
                break
        
        if idx_destino != -1:
            rutas_con_destino.append({
                "ruta": ruta,
                "paradas": paradas_ruta,
                "idx_destino": idx_destino
            })
            print(f"Ruta {ruta.nombre} contiene destino en posición {idx_destino}")
    
    if not rutas_con_destino:
        return JsonResponse({"error": f"El destino '{parada_destino.nombre}' no está en ninguna ruta"}, status=404)
    
    # 🔥 Si usamos ubicación, buscar la MEJOR parada origen en CADA ruta
    if lat and lng and not parada_origen_buscada:
        usar_ubicacion = True
        lat_f, lng_f = float(lat), float(lng)
        
        mejores_opciones = []
        
        for ruta_info in rutas_con_destino:
            ruta = ruta_info["ruta"]
            paradas_ruta = ruta_info["paradas"]
            idx_destino = ruta_info["idx_destino"]
            
            # Buscar la parada más cercana que esté ANTES del destino en ESTA ruta
            mejor_distancia = float('inf')
            mejor_parada = None
            mejor_idx = -1
            
            for i in range(idx_destino):  # Solo antes del destino
                rp = paradas_ruta[i]
                dist = calcular_distancia(
                    lat_f, lng_f,
                    float(rp.parada.lat),
                    float(rp.parada.lng)
                )
                
                if dist < mejor_distancia:
                    mejor_distancia = dist
                    mejor_parada = rp.parada
                    mejor_idx = i
            
            if mejor_parada:
                mejores_opciones.append({
                    "ruta": ruta,
                    "parada_origen": mejor_parada,
                    "idx_origen": mejor_idx,
                    "idx_destino": idx_destino,
                    "distancia": mejor_distancia,
                    "paradas_ruta": paradas_ruta
                })
                print(f"  Ruta {ruta.nombre}: mejor origen {mejor_parada.nombre} a {mejor_distancia:.3f}km")
        
        if not mejores_opciones:
            return JsonResponse({"error": "No se encontraron paradas antes del destino en ninguna ruta"}, status=404)
        
        # Ordenar por distancia y elegir la mejor
        mejores_opciones.sort(key=lambda x: x["distancia"])
        opcion_elegida = mejores_opciones[0]
        
        parada_origen = opcion_elegida["parada_origen"]
        ruta_elegida = opcion_elegida["ruta"]
        idx_origen = opcion_elegida["idx_origen"]
        idx_destino = opcion_elegida["idx_destino"]
        paradas_ruta = opcion_elegida["paradas_ruta"]
        
        print(f"\n✅ MEJOR OPCIÓN ENCONTRADA:")
        print(f"  Ruta: {ruta_elegida.nombre}")
        print(f"  Origen: {parada_origen.nombre} (ID: {parada_origen.id}, pos {idx_origen})")
        print(f"  Destino: {parada_destino.nombre} (ID: {parada_destino.id}, pos {idx_destino})")
        print(f"  Distancia a pie: {opcion_elegida['distancia']:.3f}km")
        
    elif parada_origen_buscada:
        # Buscar origen manual - encontrar ruta que contenga AMBAS
        ruta_encontrada = None
        idx_origen = -1
        idx_destino = -1
        paradas_ruta = None
        
        for ruta_info in rutas_con_destino:
            ruta = ruta_info["ruta"]
            paradas = ruta_info["paradas"]
            dest_idx = ruta_info["idx_destino"]
            
            # Buscar origen en esta ruta
            for i, rp in enumerate(paradas):
                if rp.parada.id == parada_origen_buscada.id:
                    if i < dest_idx:  # Origen debe estar ANTES
                        ruta_encontrada = ruta
                        idx_origen = i
                        idx_destino = dest_idx
                        paradas_ruta = paradas
                        print(f"✅ Encontrada ruta {ruta.nombre}: {parada_origen_buscada.nombre} (pos {i}) → {parada_destino.nombre} (pos {dest_idx})")
                        break
            if ruta_encontrada:
                break
        
        if not ruta_encontrada:
            return JsonResponse({
                "error": f"No hay ruta donde '{parada_origen_buscada.nombre}' esté antes que '{parada_destino.nombre}'"
            }, status=404)
        
        parada_origen = parada_origen_buscada
        ruta_elegida = ruta_encontrada
        
    else:
        return JsonResponse({"error": "Debes especificar origen o usar ubicación"}, status=400)
    
    # 🔥 CONSTRUIR RESPUESTA
    # Obtener paradas desde origen hasta destino
    paradas_recorridas = []
    for i in range(idx_origen, idx_destino + 1):
        rp = paradas_ruta[i]
        paradas_recorridas.append({
            "nombre": rp.parada.nombre,
            "lat": float(rp.parada.lat),
            "lng": float(rp.parada.lng),
            "sentido": rp.parada.sentido or "Sin sentido"
        })
    
    # Obtener coordenadas de la ruta
    coordenadas_ruta = parsear_coordenadas(ruta_elegida.coordenadas)
    coordenadas_formateadas = []
    if coordenadas_ruta:
        for v in coordenadas_ruta:
            if isinstance(v, dict) and 'lat' in v and 'lng' in v:
                coordenadas_formateadas.append({
                    "lat": float(v['lat']),
                    "lng": float(v['lng'])
                })
    
    print(f"\n✅ RUTA FINAL:")
    print(f"  Ruta: {ruta_elegida.nombre}")
    print(f"  Paradas: {len(paradas_recorridas)}")
    print(f"  Desde: {paradas_recorridas[0]['nombre']}")
    print(f"  Hasta: {paradas_recorridas[-1]['nombre']}")
    
    return JsonResponse({
        "nombre": ruta_elegida.nombre,
        "color": ruta_elegida.color,
        "origen": paradas_recorridas[0]["nombre"],
        "destino": paradas_recorridas[-1]["nombre"],
        "paradas": paradas_recorridas,
        "coordenadas": coordenadas_formateadas,
        "sentido": sentido_destino,
        "paradas_totales": len(paradas_recorridas),
        "distancia_caminata": opcion_elegida["distancia"] if usar_ubicacion and 'opcion_elegida' in locals() else 0
    })


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