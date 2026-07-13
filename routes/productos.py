from flask import Blueprint, render_template, request, redirect, url_for, flash
from bson.objectid import ObjectId
import re

from db import productos_collection
from decorators import login_required, admin_required

productos_bp = Blueprint("productos", __name__)

CATEGORIAS = [
    "Electronica", "Computacion", "Celulares", "Audio",
    "Accesorios", "Hogar", "Deportes", "Juguetes", "Otra"
]


@productos_bp.route("/productos")
@login_required
@admin_required
def listar():
    busqueda = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    orden_precio = request.args.get("orden_precio", "").strip()

    query = {}
    if busqueda:
        regex = re.compile(re.escape(busqueda), re.IGNORECASE)
        query["$or"] = [{"nombre": regex}, {"descripcion": regex}, {"categoria": regex}]
    if categoria:
        query["categoria"] = categoria

    sort = [("nombre", 1)]
    if orden_precio == "asc":
        sort = [("precio", 1)]
    elif orden_precio == "desc":
        sort = [("precio", -1)]

    productos = list(productos_collection.find(query).sort(sort))
    for p in productos:
        p["_id_str"] = str(p["_id"])

    return render_template("productos/list.html",
                           productos=productos, categorias=CATEGORIAS,
                           busqueda=busqueda, categoria_filtro=categoria,
                           orden_precio=orden_precio)


@productos_bp.route("/productos/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio_str = request.form.get("precio", "0").strip()
        stock_str = request.form.get("stock", "0").strip()
        activo = request.form.get("activo") == "on"

        errors = []
        if not nombre:
            errors.append("El nombre es obligatorio")
        if not categoria:
            errors.append("La categoria es obligatoria")

        try:
            precio = float(precio_str)
            if precio <= 0:
                errors.append("El precio debe ser mayor a 0")
        except ValueError:
            errors.append("Precio invalido")
            precio = 0

        try:
            stock = int(stock_str)
            if stock < 0:
                errors.append("El stock no puede ser negativo")
        except ValueError:
            errors.append("Stock invalido")
            stock = 0

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("productos/form.html",
                                   producto={"nombre": nombre, "categoria": categoria,
                                             "descripcion": descripcion, "precio": precio,
                                             "stock": stock, "activo": activo},
                                   categorias=CATEGORIAS, editando=False)

        productos_collection.insert_one({
            "nombre": nombre, "categoria": categoria, "descripcion": descripcion,
            "precio": precio, "stock": stock, "activo": activo
        })
        flash(f"Producto {nombre} creado exitosamente", "success")
        return redirect(url_for("productos.listar"))

    return render_template("productos/form.html",
                           producto={"nombre": "", "categoria": "", "descripcion": "",
                                     "precio": 0, "stock": 0, "activo": True},
                           categorias=CATEGORIAS, editando=False)


@productos_bp.route("/productos/editar/<id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    try:
        producto = productos_collection.find_one({"_id": ObjectId(id)})
    except:
        flash("Producto no encontrado", "danger")
        return redirect(url_for("productos.listar"))
    if not producto:
        flash("Producto no encontrado", "danger")
        return redirect(url_for("productos.listar"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio_str = request.form.get("precio", "0").strip()
        stock_str = request.form.get("stock", "0").strip()
        activo = request.form.get("activo") == "on"

        errors = []
        if not nombre:
            errors.append("El nombre es obligatorio")

        try:
            precio = float(precio_str)
            if precio <= 0:
                errors.append("El precio debe ser mayor a 0")
        except ValueError:
            errors.append("Precio invalido")
            precio = producto["precio"]

        try:
            stock = int(stock_str)
            if stock < 0:
                errors.append("El stock no puede ser negativo")
        except ValueError:
            errors.append("Stock invalido")
            stock = producto["stock"]

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("productos/form.html",
                                   producto={**producto, "nombre": nombre, "categoria": categoria,
                                             "descripcion": descripcion, "precio": precio,
                                             "stock": stock, "activo": activo},
                                   categorias=CATEGORIAS, editando=True)

        productos_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"nombre": nombre, "categoria": categoria, "descripcion": descripcion,
                       "precio": precio, "stock": stock, "activo": activo}}
        )
        flash("Producto actualizado exitosamente", "success")
        return redirect(url_for("productos.listar"))

    return render_template("productos/form.html",
                           producto=producto, categorias=CATEGORIAS, editando=True)


@productos_bp.route("/productos/eliminar/<id>")
@login_required
@admin_required
def eliminar(id):
    try:
        result = productos_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count:
            flash("Producto eliminado exitosamente", "success")
        else:
            flash("Producto no encontrado", "danger")
    except Exception as e:
        flash(f"Error al eliminar: {str(e)}", "danger")
    return redirect(url_for("productos.listar"))
