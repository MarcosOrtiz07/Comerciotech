from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from bson.objectid import ObjectId
from datetime import datetime
import re

from db import pedidos_collection, clientes_collection, productos_collection
from decorators import login_required, admin_required

pedidos_bp = Blueprint("pedidos", __name__)
ESTADOS = ["Pendiente", "Procesando", "Enviado", "Entregado", "Cancelado"]


def serializar_productos():
    raw = list(productos_collection.find({"activo": True}).sort("nombre", 1))
    return [{"_id": str(p["_id"]), "nombre": p["nombre"],
             "precio": p["precio"], "stock": p["stock"]} for p in raw]


def serializar_clientes():
    raw = list(clientes_collection.find().sort("nombre", 1))
    return [{"_id": str(c["_id"]), "nombre": c["nombre"],
             "apellido": c["apellido"], "email": c["email"]} for c in raw]


@pedidos_bp.route("/pedidos")
@login_required
@admin_required
def listar():
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    per_page = 10

    query = {}
    if busqueda:
        try:
            oid = ObjectId(busqueda)
            query["$or"] = [{"_id": oid}, {"detalle.nombre": re.compile(re.escape(busqueda), re.IGNORECASE)}]
        except:
            query["detalle.nombre"] = re.compile(re.escape(busqueda), re.IGNORECASE)
    if estado:
        query["estado"] = estado

    total = pedidos_collection.count_documents(query)
    total_pages = max(1, -(-total // per_page))
    if page > total_pages:
        page = total_pages

    pedidos = list(pedidos_collection.find(query).sort("fecha", -1)
                   .skip((page - 1) * per_page).limit(per_page))

    for p in pedidos:
        p["_id_str"] = str(p["_id"])
        c = clientes_collection.find_one({"_id": p["cliente_id"]})
        p["cliente_nombre"] = f"{c['nombre']} {c['apellido']}" if c else "Eliminado"
        p["items_count"] = len(p.get("detalle", []))

    return render_template("pedidos/list.html",
                           pedidos=pedidos, estados=ESTADOS,
                           busqueda=busqueda, estado_filtro=estado,
                           page=page, total_pages=total_pages, total=total)


@pedidos_bp.route("/pedidos/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def nuevo():
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id", "").strip()
        estado = request.form.get("estado", "Pendiente").strip()
        producto_ids = request.form.getlist("producto_id[]")
        cantidades = request.form.getlist("cantidad[]")

        errors = []
        try:
            cliente_oid = ObjectId(cliente_id)
            if not clientes_collection.find_one({"_id": cliente_oid}):
                errors.append("Cliente no encontrado")
        except:
            errors.append("Cliente invalido")
            cliente_oid = None

        detalle = []
        total = 0
        for pid, cant_str in zip(producto_ids, cantidades):
            if not pid.strip():
                continue
            try:
                prod = productos_collection.find_one({"_id": ObjectId(pid)})
                if not prod:
                    errors.append(f"Producto no encontrado")
                    continue
                cant = int(cant_str)
                if cant <= 0:
                    errors.append(f"Cantidad invalida")
                    continue
                if cant > prod["stock"]:
                    errors.append(f"Stock insuficiente para {prod['nombre']} (disp: {prod['stock']})")
                    continue
                detalle.append({
                    "producto_id": prod["_id"], "nombre": prod["nombre"],
                    "cantidad": cant, "precio": prod["precio"]
                })
                total += prod["precio"] * cant
            except:
                errors.append("Error al procesar productos")

        if not detalle:
            errors.append("Debe agregar al menos un producto valido")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("pedidos/form.html",
                                   clientes=serializar_clientes(),
                                   productos=serializar_productos(),
                                   estados=ESTADOS, editando=False)

        pedido = {
            "cliente_id": cliente_oid, "fecha": datetime.now(),
            "estado": estado, "total": total, "detalle": detalle
        }
        result = pedidos_collection.insert_one(pedido)

        for item in detalle:
            productos_collection.update_one(
                {"_id": item["producto_id"]},
                {"$inc": {"stock": -item["cantidad"]}}
            )

        flash(f"Pedido #{str(result.inserted_id)[-6:]} creado - Total: ${total:.2f}", "success")
        return redirect(url_for("pedidos.listar"))

    return render_template("pedidos/form.html",
                           clientes=serializar_clientes(),
                           productos=serializar_productos(),
                           estados=ESTADOS, editando=False)


@pedidos_bp.route("/pedidos/ver/<id>")
@login_required
@admin_required
def ver(id):
    try:
        pedido = pedidos_collection.find_one({"_id": ObjectId(id)})
    except Exception as e:
        print(f"[pedidos] Error al convertir ObjectId '{id}': {e}")
        return jsonify({"error": "ID de pedido invalido"}), 400
    if not pedido:
        return jsonify({"error": "Pedido no encontrado"}), 404

    c = clientes_collection.find_one({"_id": pedido["cliente_id"]})
    pedido["cliente_nombre"] = f"{c['nombre']} {c['apellido']}" if c else "Eliminado"
    pedido["cliente_email"] = c["email"] if c else ""
    pedido["_id_str"] = str(pedido["_id"])
    pedido["cliente_id_str"] = str(pedido["cliente_id"])
    pedido["fecha_str"] = pedido["fecha"].strftime("%d/%m/%Y %H:%M") if isinstance(pedido.get("fecha"), datetime) else str(pedido.get("fecha", ""))

    for item in pedido.get("detalle", []):
        item["producto_id_str"] = str(item["producto_id"])
        item["subtotal"] = item["cantidad"] * item["precio"]

    # jsonify serializacion: reemplazar ObjectId/datetime con strings
    pedido["_id"] = pedido["_id_str"]
    pedido["cliente_id"] = pedido["cliente_id_str"]
    pedido.pop("fecha", None)
    for item in pedido.get("detalle", []):
        item["producto_id"] = item["producto_id_str"]

    return jsonify(pedido)


@pedidos_bp.route("/pedidos/editar_estado/<id>", methods=["POST"])
@login_required
@admin_required
def editar_estado(id):
    estado = request.form.get("estado", "").strip()
    if estado not in ESTADOS:
        flash("Estado invalido", "danger")
        return redirect(url_for("pedidos.listar"))
    try:
        oid = ObjectId(id)
    except Exception as e:
        print(f"[pedidos] editar_estado: ObjectId invalido '{id}': {e}")
        flash("ID de pedido invalido", "danger")
        return redirect(url_for("pedidos.listar"))
    pedido = pedidos_collection.find_one({"_id": oid})
    if not pedido:
        flash("Pedido no encontrado", "danger")
        return redirect(url_for("pedidos.listar"))
    try:
        pedidos_collection.update_one({"_id": oid}, {"$set": {"estado": estado}})
        flash("Estado del pedido actualizado", "success")
    except Exception as e:
        print(f"[pedidos] Error al actualizar estado del pedido {id}: {e}")
        flash("Error al actualizar el pedido", "danger")
    return redirect(url_for("pedidos.listar"))


@pedidos_bp.route("/pedidos/eliminar/<id>")
@login_required
@admin_required
def eliminar(id):
    try:
        oid = ObjectId(id)
    except Exception as e:
        print(f"[pedidos] eliminar: ObjectId invalido '{id}': {e}")
        flash("ID de pedido invalido", "danger")
        return redirect(url_for("pedidos.listar"))
    try:
        pedido = pedidos_collection.find_one({"_id": oid})
        if not pedido:
            flash("Pedido no encontrado", "danger")
            return redirect(url_for("pedidos.listar"))
        for item in pedido.get("detalle", []):
            try:
                prod_oid = item["producto_id"]
                productos_collection.update_one(
                    {"_id": prod_oid},
                    {"$inc": {"stock": item["cantidad"]}}
                )
            except Exception as e:
                print(f"[pedidos] Error restaurando stock: {e}")
        pedidos_collection.delete_one({"_id": oid})
        flash("Pedido eliminado - stock restaurado", "success")
    except Exception as e:
        print(f"[pedidos] Error al eliminar pedido {id}: {e}")
        flash(f"Error al eliminar: {str(e)}", "danger")
    return redirect(url_for("pedidos.listar"))
