from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from datetime import datetime
import re

from db import users_collection
from decorators import login_required, admin_required

usuarios_bp = Blueprint("usuarios", __name__)
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PASSWORD_RE = re.compile(r'^(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$')


@usuarios_bp.route("/usuarios")
@login_required
@admin_required
def listar():
    busqueda = request.args.get("q", "").strip()
    query = {}
    if busqueda:
        query["email"] = re.compile(re.escape(busqueda), re.IGNORECASE)
    usuarios = list(users_collection.find(query).sort("created_at", -1))
    for u in usuarios:
        u["_id_str"] = str(u["_id"])
    return render_template("admin/usuarios/list.html", usuarios=usuarios, busqueda=busqueda)


@usuarios_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def nuevo():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        rol = request.form.get("rol", "trabajador").strip()

        errors = []
        if not EMAIL_RE.match(email):
            errors.append("Correo electronico invalido")
        if not PASSWORD_RE.match(password):
            errors.append("Minimo 8 caracteres, una mayuscula y un simbolo especial")
        if users_collection.find_one({"email": email}):
            errors.append("El email ya esta registrado")
        if rol not in ("admin", "trabajador"):
            errors.append("Rol invalido")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/usuarios/form.html", usuario=request.form, editando=False)

        users_collection.insert_one({
            "email": email,
            "password": generate_password_hash(password),
            "rol": rol,
            "created_at": datetime.now()
        })
        flash(f"Usuario {email} creado como {rol}", "success")
        return redirect(url_for("usuarios.listar"))

    return render_template("admin/usuarios/form.html", usuario={}, editando=False)


@usuarios_bp.route("/usuarios/editar/<id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    try:
        usuario = users_collection.find_one({"_id": ObjectId(id)})
    except:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for("usuarios.listar"))
    if not usuario:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for("usuarios.listar"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        rol = request.form.get("rol", "trabajador").strip()
        nueva_password = request.form.get("password", "")

        errors = []
        if not EMAIL_RE.match(email):
            errors.append("Correo electronico invalido")
        if email != usuario["email"] and users_collection.find_one({"email": email}):
            errors.append("El email ya esta registrado")
        if rol not in ("admin", "trabajador"):
            errors.append("Rol invalido")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/usuarios/form.html", usuario={**usuario, **request.form}, editando=True)

        update = {"email": email, "rol": rol}
        if nueva_password:
            if not PASSWORD_RE.match(nueva_password):
                flash("Minimo 8 caracteres, una mayuscula y un simbolo especial", "danger")
                return render_template("admin/usuarios/form.html", usuario={**usuario, **request.form}, editando=True)
            update["password"] = generate_password_hash(nueva_password)

        users_collection.update_one({"_id": ObjectId(id)}, {"$set": update})
        flash("Usuario actualizado exitosamente", "success")
        return redirect(url_for("usuarios.listar"))

    return render_template("admin/usuarios/form.html", usuario=usuario, editando=True)


@usuarios_bp.route("/usuarios/eliminar/<id>")
@login_required
@admin_required
def eliminar(id):
    try:
        usuario = users_collection.find_one({"_id": ObjectId(id)})
        if not usuario:
            flash("Usuario no encontrado", "danger")
            return redirect(url_for("usuarios.listar"))
        if usuario["email"] == session.get("user"):
            flash("No puedes eliminar tu propio usuario", "danger")
            return redirect(url_for("usuarios.listar"))
        users_collection.delete_one({"_id": ObjectId(id)})
        flash("Usuario eliminado exitosamente", "success")
    except Exception as e:
        flash(f"Error al eliminar: {str(e)}", "danger")
    return redirect(url_for("usuarios.listar"))
