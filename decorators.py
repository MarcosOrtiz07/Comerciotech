from flask import session, flash, redirect, url_for, render_template
from functools import wraps


def login_required(f):
    # Este mecanismo actúa como un filtro básico de autenticación para asegurar que solo el personal registrado pueda ver la pantalla
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Comprobamos si el usuario mantiene una sesión activa en su navegador web
        if "user" not in session:
            flash("Debe iniciar sesion para acceder", "warning")
            return redirect(url_for("index"))
        # Si todo está en orden permitimos que la pantalla se cargue con normalidad
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    # Este es el filtro de seguridad de alta jerarquía destinado a proteger las zonas exclusivas de la gerencia
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Verificamos primero que la persona al menos haya ingresado sus credenciales al sistema
        if "user" not in session:
            flash("Debe iniciar sesion para acceder", "warning")
            return redirect(url_for("index"))
        # Evaluamos si el rango del empleado es estrictamente el de un administrador de la tienda
        if session.get("rol") != "admin":
            return render_template("403.html"), 403
        # Si el usuario es administrador le damos luz verde para proceder
        return f(*args, **kwargs)
    return wrapper


def worker_required(f):
    # Este filtro protege los módulos operativos diseñados específicamente para el personal de piso y almacén
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Validamos que exista una sesión activa antes de revisar cualquier tipo de permisos adicionales
        if "user" not in session:
            flash("Debe iniciar sesion para acceder", "warning")
            return redirect(url_for("index"))
        # Bloqueamos el acceso si quien intenta entrar no cuenta con el rango operativo de trabajador
        if session.get("rol") != "trabajador":
            return render_template("403.html"), 403
        # Concedemos el acceso a la herramienta de trabajo si el rango es el correcto
        return f(*args, **kwargs)
    return wrapper
