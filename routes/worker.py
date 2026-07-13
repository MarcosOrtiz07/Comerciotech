from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from bson.objectid import ObjectId
from datetime import datetime
import re

from db import productos_collection, movimientos_collection
from decorators import login_required, worker_required

worker_bp = Blueprint("worker", __name__)
PER_PAGE = 10


@worker_bp.route("/worker/dashboard")
@login_required
@worker_required
def dashboard():
    total_productos = productos_collection.count_documents({})
    stock_bajo = productos_collection.count_documents({"stock": {"$lt": 10, "$gt": 0}})
    sin_stock = productos_collection.count_documents({"stock": 0})

    hoy = datetime.now()
    inicio_hoy = datetime(hoy.year, hoy.month, hoy.day)
    mov_hoy = movimientos_collection.count_documents({"fecha": {"$gte": inicio_hoy}})

    ultimos_mov = list(movimientos_collection.find().sort("fecha", -1).limit(10))
    for m in ultimos_mov:
        m["_id_str"] = str(m["_id"])
        if isinstance(m.get("fecha"), datetime):
            m["fecha_str"] = m["fecha"].strftime("%d/%m/%Y %H:%M")

    productos_alertas = list(productos_collection.find({"$or": [
        {"stock": 0}, {"stock": {"$lt": 10, "$gt": 0}}
    ]}).limit(10))

    return render_template("worker/dashboard.html",
                           email=session["user"],
                           total_productos=total_productos,
                           stock_bajo=stock_bajo,
                           sin_stock=sin_stock,
                           mov_hoy=mov_hoy,
                           ultimos_mov=ultimos_mov,
                           productos_alertas=productos_alertas)


@worker_bp.route("/worker/productos")
@login_required
@worker_required
def productos():
    busqueda = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    query = {"activo": True}
    if busqueda:
        regex = re.compile(re.escape(busqueda), re.IGNORECASE)
        query["$or"] = [{"nombre": regex}, {"descripcion": regex}, {"categoria": regex}]

    total = productos_collection.count_documents(query)
    total_pages = max(1, -(-total // PER_PAGE))
    if page > total_pages:
        page = total_pages

    productos = list(productos_collection.find(query).sort("nombre", 1)
                     .skip((page - 1) * PER_PAGE).limit(PER_PAGE))
    for p in productos:
        p["_id_str"] = str(p["_id"])

    return render_template("worker/productos.html",
                           productos=productos, busqueda=busqueda,
                           page=page, total_pages=total_pages, total=total)


@worker_bp.route("/worker/stock/entrada", methods=["POST"])
@login_required
@worker_required
def entrada_stock():
    producto_id = request.form.get("producto_id", "").strip()
    cantidad = request.form.get("cantidad", "0").strip()
    motivo = request.form.get("motivo", "").strip()

    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0", "danger")
            return redirect(url_for("worker.productos"))
    except ValueError:
        flash("Cantidad invalida", "danger")
        return redirect(url_for("worker.productos"))

    try:
        prod = productos_collection.find_one({"_id": ObjectId(producto_id)})
        if not prod:
            flash("Producto no encontrado", "danger")
            return redirect(url_for("worker.productos"))
    except:
        flash("Producto invalido", "danger")
        return redirect(url_for("worker.productos"))

    productos_collection.update_one(
        {"_id": ObjectId(producto_id)},
        {"$inc": {"stock": cantidad}}
    )

    movimientos_collection.insert_one({
        "producto_id": ObjectId(producto_id),
        "producto_nombre": prod["nombre"],
        "tipo": "entrada",
        "cantidad": cantidad,
        "stock_anterior": prod["stock"],
        "stock_nuevo": prod["stock"] + cantidad,
        "motivo": motivo or "Entrada manual",
        "usuario": session.get("user"),
        "fecha": datetime.now()
    })

    flash(f"Entrada de {cantidad} unidades para {prod['nombre']}", "success")
    return redirect(url_for("worker.productos"))


@worker_bp.route("/worker/stock/salida", methods=["POST"])
@login_required
@worker_required
def salida_stock():
    producto_id = request.form.get("producto_id", "").strip()
    cantidad = request.form.get("cantidad", "0").strip()
    motivo = request.form.get("motivo", "").strip()

    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0", "danger")
            return redirect(url_for("worker.productos"))
    except ValueError:
        flash("Cantidad invalida", "danger")
        return redirect(url_for("worker.productos"))

    try:
        prod = productos_collection.find_one({"_id": ObjectId(producto_id)})
        if not prod:
            flash("Producto no encontrado", "danger")
            return redirect(url_for("worker.productos"))
    except:
        flash("Producto invalido", "danger")
        return redirect(url_for("worker.productos"))

    if prod["stock"] < cantidad:
        flash(f"Stock insuficiente. Disponible: {prod['stock']}", "danger")
        return redirect(url_for("worker.productos"))

    productos_collection.update_one(
        {"_id": ObjectId(producto_id)},
        {"$inc": {"stock": -cantidad}}
    )

    movimientos_collection.insert_one({
        "producto_id": ObjectId(producto_id),
        "producto_nombre": prod["nombre"],
        "tipo": "salida",
        "cantidad": cantidad,
        "stock_anterior": prod["stock"],
        "stock_nuevo": prod["stock"] - cantidad,
        "motivo": motivo or "Salida manual",
        "usuario": session.get("user"),
        "fecha": datetime.now()
    })

    flash(f"Salida de {cantidad} unidades para {prod['nombre']}", "success")
    return redirect(url_for("worker.productos"))


@worker_bp.route("/worker/movimientos")
@login_required
@worker_required
def movimientos():
    busqueda = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    query = {}
    if busqueda:
        query["producto_nombre"] = re.compile(re.escape(busqueda), re.IGNORECASE)
    if tipo:
        query["tipo"] = tipo

    total = movimientos_collection.count_documents(query)
    total_pages = max(1, -(-total // PER_PAGE))
    if page > total_pages:
        page = total_pages

    movs = list(movimientos_collection.find(query).sort("fecha", -1)
                .skip((page - 1) * PER_PAGE).limit(PER_PAGE))
    for m in movs:
        m["_id_str"] = str(m["_id"])
        if isinstance(m.get("fecha"), datetime):
            m["fecha_str"] = m["fecha"].strftime("%d/%m/%Y %H:%M")

    return render_template("worker/movimientos.html",
                           movimientos=movs, busqueda=busqueda,
                           tipo_filtro=tipo, page=page,
                           total_pages=total_pages, total=total)


@worker_bp.route("/worker/perfil")
@login_required
@worker_required
def perfil():
    return render_template("worker/perfil.html", email=session.get("user"))
