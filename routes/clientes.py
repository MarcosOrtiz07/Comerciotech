from flask import Blueprint, render_template, request, redirect, url_for, flash
from bson.objectid import ObjectId
from datetime import datetime
import re

from db import clientes_collection, pedidos_collection
from decorators import login_required, admin_required

clientes_bp = Blueprint("clientes", __name__)
PER_PAGE = 10
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_RE = re.compile(r'^[\d\s\-\+\(\)]{7,20}$')


@clientes_bp.route("/clientes")
@login_required
@admin_required
def listar():
    busqueda = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    query = {}
    if busqueda:
        regex = re.compile(re.escape(busqueda), re.IGNORECASE)
        query["$or"] = [
            {"nombre": regex}, {"apellido": regex},
            {"email": regex}, {"telefono": regex}
        ]

    total = clientes_collection.count_documents(query)
    total_pages = max(1, -(-total // PER_PAGE))
    if page > total_pages:
        page = total_pages

    skip = (page - 1) * PER_PAGE
    clientes = list(clientes_collection.find(query)
                    .sort("fecha_registro", -1).skip(skip).limit(PER_PAGE))

    for c in clientes:
        c["_id_str"] = str(c["_id"])
        c["pedidos_count"] = pedidos_collection.count_documents({"cliente_id": c["_id"]})

    return render_template("clientes/list.html",
                           clientes=clientes, busqueda=busqueda,
                           page=page, total_pages=total_pages, total=total)


@clientes_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        direccion = request.form.get("direccion", "").strip()

        errors = []
        if not nombre or not apellido:
            errors.append("Nombre y apellido son obligatorios")
        if email and not EMAIL_RE.match(email):
            errors.append("Correo electronico invalido")
        if email and clientes_collection.find_one({"email": email}):
            errors.append("El email ya esta registrado")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("clientes/form.html", cliente=request.form, editando=False)

        clientes_collection.insert_one({
            "nombre": nombre, "apellido": apellido, "email": email,
            "telefono": telefono, "direccion": direccion,
            "fecha_registro": datetime.now()
        })
        flash(f"Cliente {nombre} {apellido} creado exitosamente", "success")
        return redirect(url_for("clientes.listar"))

    return render_template("clientes/form.html", cliente={}, editando=False)


@clientes_bp.route("/clientes/editar/<id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    try:
        cliente = clientes_collection.find_one({"_id": ObjectId(id)})
    except:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for("clientes.listar"))
    if not cliente:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for("clientes.listar"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        direccion = request.form.get("direccion", "").strip()

        errors = []
        if not nombre or not apellido:
            errors.append("Nombre y apellido son obligatorios")
        if email and not EMAIL_RE.match(email):
            errors.append("Correo electronico invalido")
        if email and email != cliente.get("email") and clientes_collection.find_one({"email": email}):
            errors.append("El email ya esta registrado por otro cliente")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("clientes/form.html", cliente={**cliente, **request.form}, editando=True)

        clientes_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"nombre": nombre, "apellido": apellido, "email": email,
                       "telefono": telefono, "direccion": direccion}}
        )
        flash("Cliente actualizado exitosamente", "success")
        return redirect(url_for("clientes.listar"))

    return render_template("clientes/form.html", cliente=cliente, editando=True)


@clientes_bp.route("/clientes/eliminar/<id>")
@login_required
@admin_required
def eliminar(id):
    try:
        result = clientes_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count:
            flash("Cliente eliminado exitosamente", "success")
        else:
            flash("Cliente no encontrado", "danger")
    except Exception as e:
        flash(f"Error al eliminar: {str(e)}", "danger")
    return redirect(url_for("clientes.listar"))
