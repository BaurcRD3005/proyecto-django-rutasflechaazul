import json
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login

from .models import (
    Parada,
    Ruta,
    RutaParada,
    HorarioRuta,
    TarifaRuta,
    ActividadReciente,
)


# ==============================
# PANEL
# ==============================

@login_required
def panel(request):
    return render(request, "adminpanel/panel.html")


@login_required
def admin_dashboard(request):
    actividades = ActividadReciente.objects.all()[:10]

    return render(request, "adminpanel/admin-dashboard.html", {
        "actividades": actividades
    })


# ==============================
# LOGIN
# ==============================

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("admin_dashboard")

        return render(request, "adminpanel/admin-login.html", {
            "error": "Usuario o contraseña incorrectos"
        })

    return render(request, "adminpanel/admin-login.html")


# ==============================
# PARADAS
# ==============================

@login_required
def paradas(request):
    paradas = Parada.objects.all()
    rutas = Ruta.objects.prefetch_related("ruta_paradas__parada")

    rutas_json = [
        {
            "id": r.id,
            "nombre": r.nombre,
            "color": getattr(r, "color", "#ff0000"),
            "paradas": [
                {
                    "id": rp.parada.id,
                    "nombre": rp.parada.nombre,
                    "lat": rp.parada.lat,
                    "lng": rp.parada.lng,
                    "orden": rp.orden
                }
                for rp in r.ruta_paradas.all().order_by("orden")
            ]
        }
        for r in rutas
    ]

    return render(request, "adminpanel/paradas.html", {
        "paradas": [
            {"id": p.id, "nombre": p.nombre, "lat": p.lat, "lng": p.lng}
            for p in paradas
        ],
        "rutas": rutas_json,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })


@login_required
def crear_parada(request):

    if request.method == "POST":

        data = json.loads(request.body)

        parada = Parada.objects.create(
            nombre=data["nombre"],
            lat=data["lat"],
            lng=data["lng"]
        )

        # registrar actividad
        ActividadReciente.objects.create(
            usuario=request.user,
            accion="add_parada",
            descripcion=f"Se agregó la parada {parada.nombre}"
        )

        return JsonResponse({
            "id": parada.id,
            "nombre": parada.nombre
        })


@login_required
def eliminar_parada(request):

    if request.method == "POST":

        data = json.loads(request.body)
        parada_id = data.get("id")

        try:
            parada = Parada.objects.get(id=parada_id)
            nombre = parada.nombre

            parada.delete()

            ActividadReciente.objects.create(
                usuario=request.user,
                accion="delete_parada",
                descripcion=f"Se eliminó la parada {nombre}"
            )

            return JsonResponse({"status": "success"})

        except Parada.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Parada no encontrada"
            })


# ==============================
# RUTAS
# ==============================

@login_required
def rutas(request):

    rutas = Ruta.objects.prefetch_related("ruta_paradas__parada")
    paradas = Parada.objects.all()

    return render(request, "adminpanel/rutas.html", {
        "rutas": [
            {
                "id": r.id,
                "nombre": r.nombre,
                "color": r.color,
                "coordenadas": (
                    json.loads(r.coordenadas)
                    if isinstance(r.coordenadas, str)
                    else r.coordenadas
                    ) if r.coordenadas else [],
                "paradas": [
                    {
                        "id": rp.parada.id,
                        "nombre": rp.parada.nombre,
                        "lat": rp.parada.lat,
                        "lng": rp.parada.lng,
                        "orden": rp.orden
                    }
                    for rp in r.ruta_paradas.all()
                ]
            }
            for r in rutas
        ],

        "paradas": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "lat": p.lat,
                "lng": p.lng
            }
            for p in paradas
        ],

        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY
    })


@login_required
def crear_ruta(request):

    if request.method == "POST":

        data = json.loads(request.body)

        coords = data.get("coordenadas", [])
        if isinstance(coords, str):
            try:
                coords = json.loads(coords)
            except:
                coords = []
                
        ruta = Ruta.objects.create(
                nombre=data["nombre"],
                color=data.get("color", "#ff0000"),
                coordenadas=json.dumps(coords)
        )

        for index, p in enumerate(data["paradas"]):

            parada = Parada.objects.get(id=p["id"])

            RutaParada.objects.create(
                ruta=ruta,
                parada=parada,
                orden=index
            )

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="add_ruta",
            descripcion=f"Se creó la ruta {ruta.nombre}"
        )

        return JsonResponse({"ok": True})


@login_required
def editar_ruta(request, id):

    if request.method == "POST":

        try:

            data = json.loads(request.body)

            ruta = Ruta.objects.get(id=id)

            ruta.nombre = data["nombre"]
            ruta.color = data["color"]
            coords = data.get("coordenadas", [])
            if isinstance(coords, str):
                try:
                    coords = json.loads(coords)
                except:
                    coords = []

            ruta.coordenadas = json.dumps(coords)

            ruta.save()

            RutaParada.objects.filter(ruta=ruta).delete()

            for index, p in enumerate(data["paradas"]):
                
                parada_id = p.get("id")
                
                if not parada_id:
                    continue

                parada = Parada.objects.get(id=p["id"])

                RutaParada.objects.create(
                    ruta=ruta,
                    parada=parada,
                    orden=index
                )

            ActividadReciente.objects.create(
                usuario=request.user,
                accion="edit_ruta",
                descripcion=f"Se editó la ruta {ruta.nombre}"
            )

            return JsonResponse({"ok": True})

        except Exception as e:
            return JsonResponse({
                "ok": False,
                "error": str(e)
            }, status=500)
            

@login_required
def eliminar_ruta(request, id):

    if request.method == "POST":

        ruta = Ruta.objects.get(id=id)

        RutaParada.objects.filter(ruta_id=id).delete()
        ruta.delete()

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="delete_ruta",
            descripcion=f"Se eliminó la ruta {ruta.nombre}"
        )

        return JsonResponse({"ok": True})


# ==============================
# HORARIOS
# ==============================

@login_required
def horarios_admin(request):

    horarios = HorarioRuta.objects.select_related("ruta", "origen", "destino")

    rutas = Ruta.objects.all()
    paradas = Parada.objects.all()

    # horarios json
    horarios_json = [
        {
            "id": h.id,
            "ruta": h.ruta.id,
            "origen": h.origen.id,
            "destino": h.destino.id,
            "primer_viaje": str(h.primer_viaje),
            "ultimo_viaje": str(h.ultimo_viaje),
            "frecuencia": h.frecuencia,
        }
        for h in horarios
    ]

    # ⭐ paradas por ruta
    paradas_ruta = {}

    for rp in RutaParada.objects.select_related("parada", "ruta").order_by("orden"):

        ruta_id = rp.ruta.id

        if ruta_id not in paradas_ruta:
            paradas_ruta[ruta_id] = []

        paradas_ruta[ruta_id].append({
            "id": rp.parada.id,
            "nombre": rp.parada.nombre
        })

    return render(request, "adminpanel/horarios_admin.html", {
        "horarios": horarios,
        "paradas": paradas,
        "rutas": rutas,
        "horarios_json": horarios_json,
        "paradas_ruta_json": paradas_ruta
    })

@login_required
def crear_horario(request):

    if request.method == "POST":

        data = json.loads(request.body)

        ruta = Ruta.objects.get(id=data["ruta"])
        origen = Parada.objects.get(id=data["origen"])
        destino = Parada.objects.get(id=data["destino"])

        horario = HorarioRuta.objects.create(
            ruta=ruta,
            origen=origen,
            destino=destino,
            primer_viaje=data["primer_viaje"],
            ultimo_viaje=data["ultimo_viaje"],
            frecuencia=data["frecuencia"],
        )

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="edit_horario",
            descripcion=f"Se modificó el horario de la ruta {ruta.nombre}"
        )

        return JsonResponse({
            "status": "ok",
            "id": horario.id
        })


@login_required
def eliminar_horario(request, id):

    if request.method == "POST":

        HorarioRuta.objects.filter(id=id).delete()

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="edit_horario",
            descripcion="Se eliminó un horario"
        )

        return JsonResponse({"status": "ok"})
    
@login_required
def editar_horario(request, id):

    if request.method == "POST":

        data = json.loads(request.body)

        horario = HorarioRuta.objects.get(id=id)

        horario.ruta_id = data["ruta"]
        horario.origen_id = data["origen"]
        horario.destino_id = data["destino"]

        horario.primer_viaje = data["primer_viaje"]
        horario.ultimo_viaje = data["ultimo_viaje"]

        horario.frecuencia = data["frecuencia"]

        horario.save()

        # registrar actividad
        ActividadReciente.objects.create(
            usuario=request.user,
            accion="edit_horario",
            descripcion=f"Se editó un horario de la ruta {horario.ruta.nombre}"
        )

        return JsonResponse({"ok": True})
    
# ==============================
# TARIFAS
# ==============================

@login_required
def tarifas_admin(request):

    tarifas = TarifaRuta.objects.select_related("ruta", "origen", "destino")
    paradas = Parada.objects.all().order_by("nombre")
    rutas = Ruta.objects.all()

    tarifas_json = [
        {
            "id": t.id,
            "ruta": t.ruta.id,
            "origen": t.origen.id,
            "destino": t.destino.id,
            "tarifa": float(t.tarifa),
            "descuento": float(t.descuento),
        }
        for t in tarifas
    ]

    # ⭐ paradas por ruta
    paradas_ruta = {}

    for rp in RutaParada.objects.select_related("parada", "ruta").order_by("orden"):

        ruta_id = rp.ruta.id

        if ruta_id not in paradas_ruta:
            paradas_ruta[ruta_id] = []

        paradas_ruta[ruta_id].append({
            "id": rp.parada.id,
            "nombre": rp.parada.nombre
        })

    return render(request, "adminpanel/tarifas.html", {
        "tarifas": tarifas,
        "paradas": paradas,
        "rutas": rutas,
        "tarifas_json": tarifas_json,
        "paradas_ruta_json": paradas_ruta
    })
    
@login_required
def crear_tarifa(request):

    if request.method == "POST":

        data = json.loads(request.body)

        ruta = Ruta.objects.get(id=data["ruta"])
        origen = Parada.objects.get(id=data["origen"])
        destino = Parada.objects.get(id=data["destino"])

        tarifa = TarifaRuta.objects.create(
            ruta=ruta,
            origen=origen,
            destino=destino,
            tarifa=data["tarifa"],
            descuento=data.get("descuento", 0)
        )

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="add_tarifa",
            descripcion=f"Se agregó tarifa a la ruta {ruta.nombre}"
        )

        return JsonResponse({
            "status": "ok",
            "id": tarifa.id
        })
        
@login_required
def editar_tarifa(request, id):

    if request.method == "POST":

        data = json.loads(request.body)

        tarifa = TarifaRuta.objects.get(id=id)

        tarifa.ruta_id = data["ruta"]
        tarifa.origen_id = data["origen"]
        tarifa.destino_id = data["destino"]

        tarifa.tarifa = data["tarifa"]
        tarifa.descuento = data["descuento"]

        tarifa.save()

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="edit_tarifa",
            descripcion=f"Se editó tarifa de la ruta {tarifa.ruta.nombre}"
        )

        return JsonResponse({"ok": True})
    
@login_required
def eliminar_tarifa(request, id):

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"})

    try:
        tarifa = TarifaRuta.objects.get(id=id)

        ActividadReciente.objects.create(
            usuario=request.user,
            accion="delete_tarifa",
            descripcion=f"Se eliminó tarifa de la ruta {tarifa.ruta.nombre}"
        )

        tarifa.delete()

        return JsonResponse({"status": "ok"})

    except TarifaRuta.DoesNotExist:

        return JsonResponse({
            "status": "error",
            "message": "Tarifa no encontrada"
        })
        