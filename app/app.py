from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime
from sqlalchemy import func, and_, case
from jinja2 import TemplateNotFound
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:sarandeameelcabezudo@localhost/proyecto_cancha_2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mi_clave_secreta_12345'  # Clave segura única

# Configuración de logging
logging.basicConfig(filename='error.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

from models import db, Turno, Precio, Cancha

db.init_app(app)

# Manejadores de errores HTTP
@app.errorhandler(404)
def page_not_found(e):
    app.logger.error(f"404 - Página no encontrada: {request.url}")
    return render_template('error.html', error_code=404, error_message="Página no encontrada"), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"500 - Error interno del servidor: {str(e)}")
    return render_template('error.html', error_code=500, error_message="Error interno del servidor"), 500

@app.route('/')
def index():
    try:
        return render_template('index.html', title='Inicio')
    except TemplateNotFound as e:
        app.logger.error(f"Plantilla no encontrada en /: {str(e)}")
        flash("Página no disponible. Contacta al administrador.", "danger")
        return redirect(url_for('index'), code=500)
    except Exception as e:
        app.logger.error(f"Error inesperado en /: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('index'), code=500)

@app.route('/turnos/')
def turnos():
    try:
        cancha_id = request.args.get('cancha_id', type=int)
        cliente = request.args.get('cliente')
        hora = request.args.get('hora', type=str)
        tipoCesped = request.args.get('tipoCesped')
        duracion = request.args.get('duracion', type=int)
        capacidad = request.args.get('capacidad')
        fecha_desde = request.args.get('fecha_desde', type=str)
        fecha_hasta = request.args.get('fecha_hasta', type=str)

        query = db.session.query(
            Turno.TurnoID, Turno.Dia, Turno.HoraDeTurno, Turno.Cliente, Turno.CanchaID,
            Turno.HorasSolicitadas, Turno.DiaDeReserva, Turno.HoraDeReserva, Cancha.Tipo, Cancha.Jugadores
        ).join(Cancha, Cancha.CanchaID == Turno.CanchaID)

        # Variable para detectar si se aplicó algún filtro
        filtros_aplicados = any([cancha_id, cliente, hora, tipoCesped, duracion, capacidad, fecha_desde, fecha_hasta])

        if cancha_id:
            if cancha_id <= 0:
                flash("ID de cancha inválido.", "danger")
                return redirect(url_for('turnos'))
            query = query.filter(Turno.CanchaID == cancha_id)
        if cliente:
            query = query.filter(Turno.Cliente.ilike(f"%{cliente}%"))
        if hora:
            try:
                hora_obj = datetime.strptime(hora, "%H:%M").time()
                query = query.filter(Turno.HoraDeTurno == hora_obj)
            except ValueError:
                flash("Formato de hora inválido. Usa HH:MM.", "danger")
        if tipoCesped in ["Natural", "Sintético"]:
            query = query.filter(Cancha.Tipo == tipoCesped)
        if duracion:
            if duracion <= 0:
                flash("Duración inválida. Debe ser mayor a 0.", "danger")
                return redirect(url_for('turnos'))
            query = query.filter(Turno.HorasSolicitadas == duracion)
        if capacidad:
            query = query.filter(Cancha.Jugadores == capacidad)
        if fecha_desde and fecha_hasta:
            try:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                query = query.filter(Turno.DiaDeReserva.between(fecha_desde, fecha_hasta))
            except ValueError:
                flash("Formato de fecha inválido. Usa YYYY-MM-DD.", "danger")

        query = query.order_by(Turno.TurnoID)
        turnos = query.all()

        # Mostrar mensaje si se aplicaron filtros y no hay resultados
        if filtros_aplicados and not turnos:
            flash("No se encontraron turnos con estos parámetros.", "warning")

        return render_template('turnos.html', turnos=turnos, title='Turnos')

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /turnos: {str(e)}")
        flash("Error al cargar los turnos. Intenta de nuevo más tarde.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /turnos: {str(e)}")
        flash("Ocurrió un error inesperado. Por favor, intenta de nuevo.", "danger")
        return redirect(url_for('index'))

@app.route('/admin/')
def admin_index():
    try:
        return render_template('admin_index.html', title='Gestión Administrativa')
    except TemplateNotFound as e:
        app.logger.error(f"Plantilla no encontrada en /admin: {str(e)}")
        flash("Página no disponible. Contacta al administrador.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /admin: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('index'))

@app.route('/canchas', methods=['GET', 'POST'])
def gestionar_canchas():
    try:
        if request.method == 'POST':
            try:
                nombre_cancha = request.form.get('nombre_cancha')
                tipo_cancha = request.form.get('tipo_cancha')
                jugadores = request.form.get('jugadores', type=int)

                if not all([nombre_cancha, tipo_cancha, jugadores]):
                    flash("Todos los campos son obligatorios.", "danger")
                    return redirect(url_for('gestionar_canchas'))
                if jugadores <= 0:
                    flash("El número de jugadores debe ser mayor a 0.", "danger")
                    return redirect(url_for('gestionar_canchas'))
                if tipo_cancha not in ["Natural", "Sintético"]:
                    flash("Tipo de cancha inválido. Usa 'Natural' o 'Sintético'.", "danger")
                    return redirect(url_for('gestionar_canchas'))

                nueva_cancha = Cancha(NombreCancha=nombre_cancha, Tipo=tipo_cancha, Jugadores=jugadores)
                db.session.add(nueva_cancha)
                db.session.commit()
                flash("Cancha añadida correctamente.", "success")
            except ValueError as e:
                app.logger.error(f"Error de formato en /canchas: {str(e)}")
                flash("Formato inválido en los datos ingresados.", "danger")
            return redirect(url_for('gestionar_canchas'))

        canchas = Cancha.query.all()
        return render_template('canchas.html', canchas=canchas)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /canchas: {str(e)}")
        flash("Error al gestionar las canchas.", "danger")
        return redirect(url_for('admin_index'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /canchas: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('admin_index'))

@app.route('/editar-cancha/<int:id>', methods=['GET', 'POST'])
def editar_cancha(id):
    try:
        if id <= 0:
            flash("ID de cancha inválido.", "danger")
            return redirect(url_for('gestionar_canchas'))

        cancha = Cancha.query.get(id)
        if not cancha:
            flash("Cancha no encontrada.", "danger")
            return redirect(url_for('gestionar_canchas'), code=404)

        if request.method == 'POST':
            try:
                cancha.NombreCancha = request.form['nombre_cancha']
                cancha.Jugadores = int(request.form['jugadores'])
                cancha.Tipo = request.form['tipo']
                if cancha.Jugadores <= 0:
                    flash("El número de jugadores debe ser mayor a 0.", "danger")
                    return redirect(url_for('editar_cancha', id=id))
                if cancha.Tipo not in ["Natural", "Sintético"]:
                    flash("Tipo de cancha inválido. Usa 'Natural' o 'Sintético'.", "danger")
                    return redirect(url_for('editar_cancha', id=id))
                db.session.commit()
                flash("Cancha actualizada correctamente.", "success")
                return redirect(url_for('gestionar_canchas'))
            except ValueError as e:
                app.logger.error(f"Error de formato en /editar-cancha/{id}: {str(e)}")
                flash("Formato inválido en los datos ingresados.", "danger")
                return redirect(url_for('editar_cancha', id=id))

        return render_template('editar_cancha.html', cancha=cancha)
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /editar-cancha/{id}: {str(e)}")
        flash("Error al editar la cancha.", "danger")
        return redirect(url_for('gestionar_canchas'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /editar-cancha/{id}: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('gestionar_canchas'))

@app.route('/eliminar-cancha/<int:id>', methods=['POST'])
def eliminar_cancha(id):
    try:
        if id <= 0:
            flash("ID de cancha inválido.", "danger")
            return redirect(url_for('gestionar_canchas'))

        cancha = Cancha.query.get_or_404(id)
        db.session.delete(cancha)
        db.session.commit()
        flash("Cancha eliminada correctamente.", "success")
    except IntegrityError as e:
        db.session.rollback()
        app.logger.error(f"Error de integridad en /eliminar-cancha/{id}: {str(e)}")
        flash("No se puede eliminar la cancha porque tiene turnos asociados.", "danger")
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /eliminar-cancha/{id}: {str(e)}")
        flash("Error al eliminar la cancha.", "danger")
    except Exception as e:
        app.logger.error(f"Error inesperado en /eliminar-cancha/{id}: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
    return redirect(url_for('gestionar_canchas'))

@app.route('/reservar-turnos/', methods=['GET', 'POST'])
def reservar_turnos_formulario():
    try:
        if request.method == 'POST':
            try:
                cancha_id = request.form.get('cancha_id', type=int)
                dia = request.form.get('dia')
                hora = request.form.get('hora')
                duracion = request.form.get('duracion', type=int)
                cliente = request.form.get('cliente')
                dia_reserva = request.form.get('dia_reserva')
                hora_reserva = request.form.get('hora_reserva')

                if not all([cancha_id, dia, hora, duracion, cliente]):
                    flash("Todos los campos son obligatorios.", "danger")
                    return redirect(url_for('reservar_turnos_formulario'))
                if cancha_id <= 0:
                    flash("ID de cancha inválido.", "danger")
                    return redirect(url_for('reservar_turnos_formulario'))
                datetime.strptime(dia, '%Y-%m-%d')
                datetime.strptime(hora, '%H:%M').time()
                if dia_reserva:
                    datetime.strptime(dia_reserva, '%Y-%m-%d')
                if hora_reserva:
                    datetime.strptime(hora_reserva, '%H:%M').time()
                if duracion <= 0:
                    flash("La duración debe ser mayor a 0.", "danger")
                    return redirect(url_for('reservar_turnos_formulario'))

                conflictos = Turno.query.filter_by(CanchaID=cancha_id, Dia=dia, HoraDeTurno=hora).all()
                if conflictos:
                    flash('El turno seleccionado no está disponible.', 'danger')
                else:
                    nuevo_turno = Turno(
                        Dia=dia, HoraDeTurno=hora, Cliente=cliente, CanchaID=cancha_id,
                        HorasSolicitadas=duracion, DiaDeReserva=dia_reserva, HoraDeReserva=hora_reserva
                    )
                    db.session.add(nuevo_turno)
                    db.session.commit()
                    flash('Turno reservado exitosamente.', 'success')
            except ValueError as e:
                app.logger.error(f"Error de formato en /reservar-turnos: {str(e)}")
                flash("Formato inválido en fecha u hora. Usa YYYY-MM-DD y HH:MM.", "danger")
            except IntegrityError as e:
                db.session.rollback()
                app.logger.error(f"Conflicto de concurrencia en /reservar-turnos: {str(e)}")
                flash("El turno ya fue reservado por otro usuario.", "danger")
            return redirect(url_for('reservar_turnos_formulario'))

        canchas = Cancha.query.all()
        return render_template('reservar_turnos.html', canchas=canchas, title='Reservar Turnos')

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /reservar-turnos: {str(e)}")
        flash("Error al reservar el turno.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /reservar-turnos: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('index'))

@app.route('/editar_turno/<int:turno_id>', methods=['GET', 'POST'])
def editar_turno(turno_id):
    try:
        if turno_id <= 0:
            flash("ID de turno inválido.", "danger")
            return redirect(url_for('turnos'))

        turno = db.session.query(
            Turno.TurnoID, Turno.Dia, Turno.HoraDeTurno, Turno.Cliente, 
            Turno.CanchaID, Turno.HorasSolicitadas, Turno.DiaDeReserva, 
            Turno.HoraDeReserva, Cancha.Tipo, Cancha.Jugadores
        ).join(Cancha, Cancha.CanchaID == Turno.CanchaID).filter(Turno.TurnoID == turno_id).first()

        if not turno:
            flash("Turno no encontrado.", "danger")
            return redirect(url_for('turnos'))

        turno_dict = {
            "TurnoID": turno[0], "Dia": turno[1], "HoraDeTurno": turno[2], "Cliente": turno[3],
            "CanchaID": turno[4], "HorasSolicitadas": turno[5], "DiaDeReserva": turno[6],
            "HoraDeReserva": turno[7], "Tipo": turno[8], "Jugadores": turno[9]
        }

        canchas = db.session.query(Cancha.CanchaID, Cancha.Tipo, Cancha.Jugadores).all()

        if request.method == 'POST':
            try:
                turno_obj = db.session.get(Turno, turno_id)
                turno_obj.Dia = request.form['dia']
                turno_obj.HoraDeTurno = request.form['hora_de_turno']
                turno_obj.Cliente = request.form['cliente']
                turno_obj.CanchaID = int(request.form['cancha_id'])
                turno_obj.HorasSolicitadas = int(request.form['horas_solicitadas'])
                turno_obj.DiaDeReserva = request.form['dia_de_reserva']
                turno_obj.HoraDeReserva = request.form['hora_de_reserva']

                datetime.strptime(turno_obj.Dia, '%Y-%m-%d')
                datetime.strptime(turno_obj.HoraDeTurno, '%H:%M').time()
                if turno_obj.DiaDeReserva:
                    datetime.strptime(turno_obj.DiaDeReserva, '%Y-%m-%d')
                if turno_obj.HoraDeReserva:
                    datetime.strptime(turno_obj.HoraDeReserva, '%H:%M').time()
                if turno_obj.HorasSolicitadas <= 0:
                    flash("La duración debe ser mayor a 0.", "danger")
                    return redirect(url_for('editar_turno', turno_id=turno_id))
                if turno_obj.CanchaID <= 0:
                    flash("ID de cancha inválido.", "danger")
                    return redirect(url_for('editar_turno', turno_id=turno_id))

                db.session.commit()
                flash("Turno actualizado correctamente.", "success")
                return redirect(url_for('turnos'))
            except ValueError as e:
                app.logger.error(f"Error de formato en /editar_turno/{turno_id}: {str(e)}")
                flash("Formato inválido en fecha u hora. Usa YYYY-MM-DD y HH:MM.", "danger")
                return redirect(url_for('editar_turno', turno_id=turno_id))

        return render_template('editar_turno.html', turno=turno_dict, canchas=canchas)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /editar_turno/{turno_id}: {str(e)}")
        flash("Error al editar el turno.", "danger")
        return redirect(url_for('turnos'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /editar_turno/{turno_id}: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('turnos'))

@app.route('/eliminar-turno/<int:turno_id>', methods=['POST'])
def eliminar_turno(turno_id):
    try:
        if turno_id <= 0:
            flash("ID de turno inválido.", "danger")
            return redirect(url_for('turnos'))

        turno = Turno.query.get_or_404(turno_id)
        db.session.delete(turno)
        db.session.commit()
        flash("Turno eliminado correctamente.", "success")
    except IntegrityError as e:
        db.session.rollback()
        app.logger.error(f"Error de integridad en /eliminar-turno/{turno_id}: {str(e)}")
        flash("No se puede eliminar el turno debido a dependencias.", "danger")
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /eliminar-turno/{turno_id}: {str(e)}")
        flash("Error al eliminar el turno.", "danger")
    except Exception as e:
        app.logger.error(f"Error inesperado en /eliminar-turno/{turno_id}: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
    return redirect(url_for('turnos'))

@app.route('/configurar-precios/', methods=['GET', 'POST'])
def configurar_precios():
    try:
        if request.method == 'POST':
            try:
                cancha_id = int(request.form['cancha_id'])
                tipo_precio = request.form['tipo_precio']
                precio = float(request.form['precio'])

                if cancha_id <= 0:
                    flash("ID de cancha inválido.", "danger")
                    return redirect(url_for('configurar_precios'))
                if tipo_precio not in ["ConLuz", "SinLuz"]:
                    flash("Tipo de precio inválido. Usa 'ConLuz' o 'SinLuz'.", "danger")
                    return redirect(url_for('configurar_precios'))
                if precio < 0:
                    flash("El precio no puede ser negativo.", "danger")
                    return redirect(url_for('configurar_precios'))

                nuevo_precio = Precio(CanchaID=cancha_id, TipoPrecio=tipo_precio, Precio=precio)
                db.session.add(nuevo_precio)
                db.session.commit()
                flash("Precio configurado correctamente.", "success")
            except ValueError as e:
                app.logger.error(f"Error de formato en /configurar-precios: {str(e)}")
                flash("Formato inválido en el precio o ID.", "danger")
            return redirect(url_for('configurar_precios'))

        canchas = Cancha.query.all()
        precios = Precio.query.all()
        return render_template('configurar_precios.html', canchas=canchas, precios=precios)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /configurar-precios: {str(e)}")
        flash("Error al configurar precios.", "danger")
        return redirect(url_for('admin_index'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /configurar-precios: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('admin_index'))

@app.route('/editar-precio/<int:precio_id>', methods=['GET', 'POST'])
def editar_precio(precio_id):
    try:
        if precio_id <= 0:
            flash("ID de precio inválido.", "danger")
            return redirect(url_for('configurar_precios'))

        precio = Precio.query.get_or_404(precio_id)
        canchas = Cancha.query.all()

        if request.method == 'POST':
            try:
                precio.CanchaID = int(request.form['cancha_id'])
                precio.TipoPrecio = request.form['tipo_precio']
                precio.Precio = float(request.form['precio'])

                if precio.CanchaID <= 0:
                    flash("ID de cancha inválido.", "danger")
                    return redirect(url_for('editar_precio', precio_id=precio_id))
                if precio.TipoPrecio not in ["ConLuz", "SinLuz"]:
                    flash("Tipo de precio inválido. Usa 'ConLuz' o 'SinLuz'.", "danger")
                    return redirect(url_for('editar_precio', precio_id=precio_id))
                if precio.Precio < 0:
                    flash("El precio no puede ser negativo.", "danger")
                    return redirect(url_for('editar_precio', precio_id=precio_id))

                db.session.commit()
                flash("Precio actualizado correctamente.", "success")
                return redirect(url_for('configurar_precios'))
            except ValueError as e:
                app.logger.error(f"Error de formato en /editar-precio/{precio_id}: {str(e)}")
                flash("Formato inválido en el precio o ID.", "danger")
                return redirect(url_for('editar_precio', precio_id=precio_id))

        return render_template('editar_precio.html', precio=precio, canchas=canchas)
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /editar-precio/{precio_id}: {str(e)}")
        flash("Error al editar el precio.", "danger")
        return redirect(url_for('configurar_precios'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /editar-precio/{precio_id}: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('configurar_precios'))

@app.route('/eliminar-precio/<int:precio_id>', methods=['POST'])
def eliminar_precio(precio_id):
    try:
        if precio_id <= 0:
            flash("ID de precio inválido.", "danger")
            return redirect(url_for('configurar_precios'))

        precio = Precio.query.get_or_404(precio_id)
        db.session.delete(precio)
        db.session.commit()
        flash("Precio eliminado correctamente.", "success")
    except IntegrityError as e:
        db.session.rollback()
        app.logger.error(f"Error de integridad en /eliminar-precio/{precio_id}: {str(e)}")
        flash("No se puede eliminar el precio debido a dependencias.", "danger")
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /eliminar-precio/{precio_id}: {str(e)}")
        flash("Error al eliminar el precio.", "danger")
    except Exception as e:
        app.logger.error(f"Error inesperado en /eliminar-precio/{precio_id}: {str(e)}")
        flash("Ocurrió un error inesperado.", "danger")
    return redirect(url_for('configurar_precios'))

@app.route("/reporte")
def reporte_recaudacion():
    try:
        cancha_id = request.args.get("cancha_id", type=int)
        tipo_cesped = request.args.get("tipo_cesped", type=str)
        desde_str = request.args.get("desde", type=str)
        hasta_str = request.args.get("hasta", type=str)

        if cancha_id and cancha_id <= 0:
            flash("ID de cancha inválido.", "danger")
            return redirect(url_for('reporte_recaudacion'))

        # Variable para detectar si se aplicó algún filtro
        filtros_aplicados = any([cancha_id, tipo_cesped, desde_str, hasta_str])

        query = db.session.query(
            func.sum(Precio.Precio * Turno.HorasSolicitadas).label("total_recaudado")
        ).select_from(Turno).join(
            Cancha, Turno.CanchaID == Cancha.CanchaID
        ).join(
            Precio, and_(
                Precio.CanchaID == Turno.CanchaID,
                Precio.TipoPrecio == case(
                    (Turno.HoraDeTurno >= "18:00", "ConLuz"),
                    else_="SinLuz"
                )
            )
        )

        if desde_str and hasta_str:
            try:
                desde = datetime.strptime(desde_str, '%Y-%m-%d').date()
                hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date()
                query = query.filter(Turno.DiaDeReserva.between(desde, hasta))
                print(f"Filtro aplicado: Desde {desde} hasta {hasta}")
            except ValueError:
                flash("Formato de fecha inválido. Usa YYYY-MM-DD.", "danger")

        if cancha_id:
            query = query.add_columns(Cancha.NombreCancha).filter(Cancha.CanchaID == cancha_id).group_by(Cancha.CanchaID)
        elif tipo_cesped:
            if tipo_cesped not in ["Natural", "Sintético"]:
                flash("Tipo de césped inválido. Usa 'Natural' o 'Sintético'.", "danger")
                return redirect(url_for('reporte_recaudacion'))
            query = query.add_columns(Cancha.Tipo).filter(Cancha.Tipo == tipo_cesped).group_by(Cancha.Tipo)

        resultados = query.all()
        print("Resultados obtenidos:", resultados)

        if not cancha_id and not tipo_cesped:
            total_recaudado = resultados[0].total_recaudado if resultados and resultados[0].total_recaudado is not None else 0
            if filtros_aplicados and (not resultados or resultados[0].total_recaudado is None):
                flash("No se encontraron datos de recaudación con estos parámetros.", "warning")
            return render_template("reporte_rec.html", total_recaudado={"Total": total_recaudado})

        # Si hay filtro por cancha_id o tipo_cesped pero no hay resultados, asignar 0 explícitamente
        total_recaudado = {}
        if resultados:
            total_recaudado = {
                resultado.NombreCancha if cancha_id else resultado.Tipo: resultado.total_recaudado
                for resultado in resultados if resultado.total_recaudado is not None
            }
        elif cancha_id:
            # Si no hay resultados, buscar el nombre de la cancha para mostrar 0
            cancha = Cancha.query.get(cancha_id)
            total_recaudado = {cancha.NombreCancha if cancha else f"Cancha {cancha_id}": 0}
        elif tipo_cesped:
            total_recaudado = {tipo_cesped: 0}

        if filtros_aplicados and not any(total_recaudado.values()):
            flash("No se encontraron datos de recaudación con estos parámetros.", "warning")

        return render_template("reporte_rec.html", total_recaudado=total_recaudado)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /reporte: {str(e)}")
        flash("Error al acceder a la base de datos. Intenta de nuevo más tarde.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error inesperado en /reporte: {str(e)}")
        flash("Ocurrió un error inesperado. Por favor, intenta de nuevo.", "danger")
        return redirect(url_for('index'))
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Base de datos inicializada correctamente")
        except SQLAlchemyError as e:
            app.logger.error(f"Error al inicializar la base de datos: {str(e)}")
            print("No se pudo conectar a la base de datos. Revisa la configuración.")
            exit(1)
    app.run(debug=True)