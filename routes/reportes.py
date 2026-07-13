from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, flash, make_response
from bson.objectid import ObjectId
from datetime import datetime
import csv
import io

from db import pedidos_collection, clientes_collection, productos_collection
from decorators import login_required, admin_required

reportes_bp = Blueprint("reportes", __name__)

MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
         5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
         9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}


def build_filtros():
    f_inicio = request.args.get("fecha_inicio", "")
    f_fin = request.args.get("fecha_fin", "")
    estado = request.args.get("estado", "")
    categoria = request.args.get("categoria", "")

    match = {"estado": {"$ne": "Cancelado"}}
    if estado:
        match["estado"] = estado
    if f_inicio:
        try:
            match["fecha"] = {"$gte": datetime.strptime(f_inicio, "%Y-%m-%d")}
        except:
            pass
    if f_fin:
        try:
            hasta = datetime.strptime(f_fin, "%Y-%m-%d")
            match.setdefault("fecha", {})["$lte"] = hasta
        except:
            pass
    if categoria:
        match["detalle.categoria"] = categoria
    return match


@reportes_bp.route("/reportes")
@login_required
@admin_required
def index():
    match = build_filtros()

    total_vendido = list(pedidos_collection.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]))
    total_vendido = total_vendido[0]["total"] if total_vendido else 0

    total_pedidos = pedidos_collection.count_documents(match)

    ticket_promedio = total_vendido / total_pedidos if total_pedidos > 0 else 0

    ventas_mes = list(pedidos_collection.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {"anio": {"$year": "$fecha"}, "mes": {"$month": "$fecha"}},
            "total": {"$sum": "$total"},
            "cantidad": {"$sum": 1}
        }},
        {"$sort": {"_id.anio": 1, "_id.mes": 1}}
    ]))

    ventas_mes_labels = [f"{MESES[v['_id']['mes']]} {v['_id']['anio']}" for v in ventas_mes]
    ventas_mes_data = [v["total"] for v in ventas_mes]

    prod_categoria = list(pedidos_collection.aggregate([
        {"$match": match},
        {"$unwind": "$detalle"},
        {"$group": {"_id": "$detalle.nombre", "total": {"$sum": {"$multiply": ["$detalle.cantidad", "$detalle.precio"]}}}},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]))

    stock_data = list(productos_collection.find({"activo": True}).sort("stock", -1).limit(10))
    stock_labels = [p["nombre"] for p in stock_data]
    stock_values = [p["stock"] for p in stock_data]

    ped_estado = list(pedidos_collection.aggregate([
        {"$group": {"_id": "$estado", "total": {"$sum": 1}}}
    ]))
    estado_labels = [e["_id"] for e in ped_estado]
    estado_values = [e["total"] for e in ped_estado]

    clientes_mes = list(clientes_collection.aggregate([
        {"$group": {
            "_id": {"anio": {"$year": "$fecha_registro"}, "mes": {"$month": "$fecha_registro"}},
            "total": {"$sum": 1}
        }},
        {"$sort": {"_id.anio": 1, "_id.mes": 1}}
    ]))
    cli_labels = [f"{MESES[c['_id']['mes']]} {c['_id']['anio']}" for c in clientes_mes]
    cli_data = [c["total"] for c in clientes_mes]

    total_clientes = clientes_collection.count_documents({})
    total_productos = productos_collection.count_documents({})
    productos_activos = productos_collection.count_documents({"activo": True})
    clientes_con_pedidos = len(pedidos_collection.distinct("cliente_id", match))

    filtros = {
        "fecha_inicio": request.args.get("fecha_inicio", ""),
        "fecha_fin": request.args.get("fecha_fin", ""),
        "estado": request.args.get("estado", ""),
        "categoria": request.args.get("categoria", "")
    }

    categorias = productos_collection.distinct("categoria")
    estados = ["Pendiente", "Procesando", "Enviado", "Entregado", "Cancelado"]

    productos_vendidos = list(pedidos_collection.aggregate([
        {"$match": match},
        {"$unwind": "$detalle"},
        {"$group": {
            "_id": "$detalle.nombre",
            "cantidad_total": {"$sum": "$detalle.cantidad"},
            "ingresos": {"$sum": {"$multiply": ["$detalle.cantidad", "$detalle.precio"]}}
        }},
        {"$sort": {"cantidad_total": -1}},
        {"$limit": 10}
    ]))

    return render_template("reportes/index.html",
                           email=session["user"],
                           total_vendido=total_vendido,
                           ticket_promedio=ticket_promedio,
                           total_pedidos=total_pedidos,
                           total_clientes=total_clientes,
                           total_productos=total_productos,
                           productos_activos=productos_activos,
                           clientes_con_pedidos=clientes_con_pedidos,
                           ventas_mes_labels=ventas_mes_labels,
                           ventas_mes_data=ventas_mes_data,
                           stock_labels=stock_labels,
                           stock_values=stock_values,
                           estado_labels=estado_labels,
                           estado_values=estado_values,
                           cli_labels=cli_labels,
                           cli_data=cli_data,
                           prod_categoria=prod_categoria,
                           filtros=filtros,
                           categorias=categorias,
                           estados=estados,
                           productos_vendidos=productos_vendidos)


@reportes_bp.route("/reportes/exportar/<formato>")
@login_required
@admin_required
def exportar(formato):
    match = build_filtros()
    datos = list(pedidos_collection.aggregate([
        {"$match": match},
        {"$unwind": "$detalle"},
        {"$group": {
            "_id": "$detalle.nombre",
            "cantidad": {"$sum": "$detalle.cantidad"},
            "ingresos": {"$sum": {"$multiply": ["$detalle.cantidad", "$detalle.precio"]}}
        }},
        {"$sort": {"cantidad": -1}}
    ]))

    if formato == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Producto", "Cantidad Vendida", "Ingresos"])
        for d in datos:
            writer.writerow([d["_id"], d["cantidad"], round(d["ingresos"], 2)])
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = "attachment;filename=reporte.csv"
        return response

    elif formato == "json":
        response = make_response(jsonify(datos))
        response.headers["Content-Disposition"] = "attachment;filename=reporte.json"
        return response

    flash("Formato no soportado", "danger")
    return redirect(url_for("reportes.index"))
