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
    ActividadReciente
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

    return render(request, "adminpanel/paradas.html", {
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

        ruta = Ruta.objects.create(
            nombre=data["nombre"],
            color=data.get("color", "#ff0000")
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

        data = json.loads(request.body)

        ruta = Ruta.objects.get(id=id)

        ruta.nombre = data["nombre"]
        ruta.color = data["color"]
        ruta.save()

        RutaParada.objects.filter(ruta=ruta).delete()

        for index, p in enumerate(data["paradas"]):

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
    paradas = Parada.objects.all()
    rutas = Ruta.objects.all()

    horarios_json = [
        {
            "id": h.id,
            "ruta": h.ruta.id,
            "origen": h.origen.id,
            "destino": h.destino.id,
            "primer_viaje": str(h.primer_viaje),
            "ultimo_viaje": str(h.ultimo_viaje),
            "frecuencia": h.frecuencia,
            "tarifa": h.tarifa,
            "descuento": h.descuento
        }
        for h in horarios
    ]

    return render(request, "adminpanel/horarios_admin.html", {
        "horarios": horarios,
        "paradas": paradas,
        "rutas": rutas,
        "horarios_json": horarios_json
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
            tarifa=data["tarifa"],
            descuento=data["descuento"],
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
        horario.tarifa = data["tarifa"]
        horario.descuento = data["descuento"]

        horario.save()

        # registrar actividad
        ActividadReciente.objects.create(
            usuario=request.user,
            accion="edit_horario",
            descripcion=f"Se editó un horario de la ruta {horario.ruta.nombre}"
        )

        return JsonResponse({"ok": True})