from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import timedelta, datetime
import re

from db import db, users_collection, clientes_collection, productos_collection, pedidos_collection, movimientos_collection
from decorators import login_required, admin_required, worker_required

app = Flask(__name__)
app.secret_key = "ComercioTech2024SecretKey!"
app.permanent_session_lifetime = timedelta(days=1)

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PASSWORD_RE = re.compile(r'^(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$')

from routes.clientes import clientes_bp
from routes.productos import productos_bp
from routes.pedidos import pedidos_bp
from routes.reportes import reportes_bp
from routes.usuarios import usuarios_bp
from routes.worker import worker_bp

app.register_blueprint(clientes_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(worker_bp)


@app.context_processor
def inject_now():
    return {"now": datetime.now()}


@app.context_processor
def inject_roles():
    return {"is_admin": session.get("rol") == "admin",
            "is_worker": session.get("rol") == "trabajador"}


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.route("/")
def index():
    if "user" in session:
        if session.get("rol") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("worker.dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not EMAIL_RE.match(email):
        flash("Correo electronico invalido", "danger")
        return redirect(url_for("index"))

    user = users_collection.find_one({"email": email})
    if user and check_password_hash(user["password"], password):
        session.permanent = True
        session["user"] = user["email"]
        session["rol"] = user.get("rol", "trabajador")
        session["user_id"] = str(user["_id"])
        flash("Inicio de sesion exitoso", "success")
        if session["rol"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("worker.dashboard"))

    flash("Credenciales invalidas", "danger")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        errors = []
        if not EMAIL_RE.match(email):
            errors.append("Correo electronico invalido")
        if not PASSWORD_RE.match(password):
            errors.append("Minimo 8 caracteres, una mayuscula y un simbolo especial")
        if password != confirm:
            errors.append("Las contrasenas no coinciden")
        if users_collection.find_one({"email": email}):
            errors.append("El email ya esta registrado")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html")

        users_collection.insert_one({
            "email": email,
            "password": generate_password_hash(password),
            "rol": "trabajador",
            "created_at": datetime.now()
        })
        flash("Registro exitoso. Inicia sesion.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    total_clientes = clientes_collection.count_documents({})
    total_productos = productos_collection.count_documents({})
    total_pedidos = pedidos_collection.count_documents({})
    total_usuarios = users_collection.count_documents({})

    ventas_total = list(pedidos_collection.aggregate([
        {"$match": {"estado": {"$ne": "Cancelado"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]))
    ventas_total = ventas_total[0]["total"] if ventas_total else 0

    hoy = datetime.now()
    inicio_mes = datetime(hoy.year, hoy.month, 1)
    clientes_mes = clientes_collection.count_documents({"fecha_registro": {"$gte": inicio_mes}})
    stock_bajo = productos_collection.count_documents({"stock": {"$lt": 10, "$gt": 0}})
    sin_stock = productos_collection.count_documents({"stock": 0})
    pendientes = pedidos_collection.count_documents({"estado": "Pendiente"})

    ultimos_pedidos = list(pedidos_collection.find().sort("fecha", -1).limit(10))
    for p in ultimos_pedidos:
        p["_id_str"] = str(p["_id"])
        c = clientes_collection.find_one({"_id": p["cliente_id"]})
        p["cliente_nombre"] = f"{c['nombre']} {c['apellido']}" if c else "Eliminado"

    ultimos_clientes = list(clientes_collection.find().sort("fecha_registro", -1).limit(10))
    for c in ultimos_clientes:
        c["_id_str"] = str(c["_id"])

    ventas_mes = list(pedidos_collection.aggregate([
        {"$match": {"estado": {"$ne": "Cancelado"}}},
        {"$group": {
            "_id": {"anio": {"$year": "$fecha"}, "mes": {"$month": "$fecha"}},
            "total": {"$sum": "$total"}, "cantidad": {"$sum": 1}
        }},
        {"$sort": {"_id.anio": 1, "_id.mes": 1}},
        {"$limit": 12}
    ]))

    meses_n = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
               5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
               9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    chart_labels = [f"{meses_n[v['_id']['mes']]} {v['_id']['anio']}" for v in ventas_mes]
    chart_data = [v["total"] for v in ventas_mes]

    prod_categoria = list(pedidos_collection.aggregate([
        {"$match": {"estado": {"$ne": "Cancelado"}}},
        {"$unwind": "$detalle"},
        {"$group": {"_id": "$detalle.nombre", "total": {"$sum": {"$multiply": ["$detalle.cantidad", "$detalle.precio"]}}}},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]))

    stock_data = list(productos_collection.find({"activo": True}).sort("stock", 1).limit(10))
    stock_labels = [p["nombre"] for p in stock_data]
    stock_values = [p["stock"] for p in stock_data]

    ped_estado = list(pedidos_collection.aggregate([
        {"$group": {"_id": "$estado", "total": {"$sum": 1}}}
    ]))
    estado_labels = [e["_id"] for e in ped_estado]
    estado_values = [e["total"] for e in ped_estado]

    productos_sin_stock = list(productos_collection.find({"stock": 0}).limit(10))
    productos_stock_bajo = list(productos_collection.find({"stock": {"$lt": 10, "$gt": 0}}).limit(10))

    ultimos_movimientos = list(movimientos_collection.find().sort("fecha", -1).limit(10))
    for m in ultimos_movimientos:
        m["_id_str"] = str(m["_id"])
        if isinstance(m.get("fecha"), datetime):
            m["fecha_str"] = m["fecha"].strftime("%d/%m/%Y %H:%M")

    stock_por_categoria = list(productos_collection.aggregate([
        {"$group": {"_id": "$categoria", "total_stock": {"$sum": "$stock"}, "count": {"$sum": 1}}},
        {"$sort": {"total_stock": -1}}
    ]))
    cat_labels = [c["_id"] for c in stock_por_categoria]
    cat_stock_values = [c["total_stock"] for c in stock_por_categoria]

    return render_template("dashboard/index.html",
                           email=session["user"],
                           total_clientes=total_clientes,
                           total_productos=total_productos,
                           total_pedidos=total_pedidos,
                           total_usuarios=total_usuarios,
                           ventas_total=ventas_total,
                           clientes_mes=clientes_mes,
                           stock_bajo=stock_bajo,
                           sin_stock=sin_stock,
                           pendientes=pendientes,
                           ultimos_pedidos=ultimos_pedidos,
                           ultimos_clientes=ultimos_clientes,
                           ultimos_movimientos=ultimos_movimientos,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           prod_categoria=prod_categoria,
                           stock_labels=stock_labels,
                           stock_values=stock_values,
                           estado_labels=estado_labels,
                           estado_values=estado_values,
                           cat_labels=cat_labels,
                           cat_stock_values=cat_stock_values,
                           productos_sin_stock=productos_sin_stock,
                           productos_stock_bajo=productos_stock_bajo)


@app.route("/buscar")
@login_required
def buscar_global():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])

    regex = re.compile(re.escape(q), re.IGNORECASE)
    resultados = []

    if session.get("rol") == "admin":
        for c in clientes_collection.find({"$or": [{"nombre": regex}, {"apellido": regex}, {"email": regex}]}).limit(5):
            resultados.append({
                "tipo": "Cliente", "nombre": f"{c['nombre']} {c['apellido']}",
                "email": c.get("email", ""), "url": url_for("clientes.listar", q=q)
            })

        for p in productos_collection.find({"$or": [{"nombre": regex}, {"categoria": regex}]}).limit(5):
            resultados.append({
                "tipo": "Producto", "nombre": p["nombre"],
                "precio": f"${p['precio']:.2f}", "stock": p["stock"],
                "url": url_for("productos.listar", q=q)
            })

        for p in pedidos_collection.find({"detalle.nombre": regex}).limit(5):
            c = clientes_collection.find_one({"_id": p["cliente_id"]})
            cn = f"{c['nombre']} {c['apellido']}" if c else "Eliminado"
            resultados.append({
                "tipo": "Pedido", "nombre": f"Pedido #{str(p['_id'])[-6:]}",
                "cliente": cn, "total": f"${p['total']:.2f}",
                "url": url_for("pedidos.listar", q=q)
            })

        for u in users_collection.find({"email": regex}).limit(3):
            resultados.append({
                "tipo": "Usuario", "nombre": u["email"],
                "email": u.get("rol", ""),
                "url": url_for("usuarios.listar")
            })
    else:
        for p in productos_collection.find({"$or": [{"nombre": regex}, {"categoria": regex}]}).limit(5):
            resultados.append({
                "tipo": "Producto", "nombre": p["nombre"],
                "precio": f"${p['precio']:.2f}", "stock": p["stock"],
                "url": url_for("worker.productos", q=q)
            })

    return jsonify(resultados)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
