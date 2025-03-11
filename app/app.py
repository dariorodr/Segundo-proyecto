from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from sqlalchemy import func, and_, case
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:sarandeameelcabezudo@localhost/proyecto_cancha_2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'  # Cambia esto por una clave segura

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
    return render_template('index.html', title='Inicio')

@app.route('/turnos/')
def turnos():
    try:
        # Obtener parámetros de filtro de la URL
        cancha_id = request.args.get('cancha_id', type=int)
        cliente = request.args.get('cliente')
        hora = request.args.get('hora', type=str)
        tipoCesped = request.args.get('tipoCesped')
        duracion = request.args.get('duracion', type=int)
        capacidad = request.args.get('capacidad')
        fecha_desde = request.args.get('fecha_desde', type=str)
        fecha_hasta = request.args.get('fecha_hasta', type=str)

        # Iniciar la consulta con JOIN
        query = db.session.query(
            Turno.TurnoID, Turno.Dia, Turno.HoraDeTurno, Turno.Cliente, Turno.CanchaID,
            Turno.HorasSolicitadas, Turno.DiaDeReserva, Turno.HoraDeReserva, Cancha.Tipo, Cancha.Jugadores
        ).join(Cancha, Cancha.CanchaID == Turno.CanchaID)

        # Aplicar filtros dinámicos
        if cancha_id:
            query = query.filter(Turno.CanchaID == cancha_id)
        if cliente:
            query = query.filter(Turno.Cliente.ilike(f"%{cliente}%"))  # ilike para case-insensitive
        if hora:
            try:
                hora_obj = datetime.strptime(hora, "%H:%M").time()
                query = query.filter(Turno.HoraDeTurno == hora_obj)
            except ValueError:
                flash("Formato de hora inválido. Usa HH:MM.", "danger")
        if tipoCesped in ["Natural", "Sintético"]:
            query = query.filter(Cancha.Tipo == tipoCesped)
        if duracion:
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

        # Ordenar por TurnoID
        query = query.order_by(Turno.TurnoID)
        turnos = query.all()

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
    return render_template('admin_index.html', title='Gestión Administrativa')

@app.route('/canchas', methods=['GET', 'POST'])
def gestionar_canchas():
    try:
        if request.method == 'POST':
            nombre_cancha = request.form.get('nombre_cancha')
            tipo_cancha = request.form.get('tipo_cancha')
            jugadores = request.form.get('jugadores', type=int)
            if not all([nombre_cancha, tipo_cancha, jugadores]):
                flash("Todos los campos son obligatorios.", "danger")
            else:
                nueva_cancha = Cancha(NombreCancha=nombre_cancha, Tipo=tipo_cancha, Jugadores=jugadores)
                db.session.add(nueva_cancha)
                db.session.commit()
                flash("Cancha añadida correctamente.", "success")
            return redirect(url_for('gestionar_canchas'))

        canchas = Cancha.query.all()
        return render_template('canchas.html', canchas=canchas)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /canchas: {str(e)}")
        flash("Error al gestionar las canchas.", "danger")
        return redirect(url_for('admin_index'))

@app.route('/editar-cancha/<int:id>', methods=['GET', 'POST'])
def editar_cancha(id):
    try:
        cancha = Cancha.query.get_or_404(id)
        if request.method == 'POST':
            cancha.NombreCancha = request.form['nombre_cancha']
            cancha.Jugadores = request.form['jugadores']
            cancha.Tipo = request.form['tipo']
            db.session.commit()
            flash("Cancha actualizada correctamente.", "success")
            return redirect(url_for('gestionar_canchas'))
        return render_template('editar_cancha.html', cancha=cancha)
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /editar-cancha/{id}: {str(e)}")
        flash("Error al editar la cancha.", "danger")
        return redirect(url_for('gestionar_canchas'))

@app.route('/eliminar-cancha/<int:id>', methods=['POST'])
def eliminar_cancha(id):
    try:
        cancha = Cancha.query.get_or_404(id)
        db.session.delete(cancha)
        db.session.commit()
        flash("Cancha eliminada correctamente.", "success")
        return redirect(url_for('gestionar_canchas'))
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /eliminar-cancha/{id}: {str(e)}")
        flash("Error al eliminar la cancha.", "danger")
        return redirect(url_for('gestionar_canchas'))

@app.route('/reservar-turnos/', methods=['GET', 'POST'])
def reservar_turnos_formulario():
    try:
        if request.method == 'POST':
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

            conflictos = Turno.query.filter_by(CanchaID=cancha_id, Dia=dia, HoraDeTurno=hora).all()
            if conflictos:
                flash('El turno seleccionado no está disponible. Intenta con otro horario.', 'danger')
            else:
                nuevo_turno = Turno(
                    Dia=dia,
                    HoraDeTurno=hora,
                    Cliente=cliente,
                    CanchaID=cancha_id,
                    HorasSolicitadas=duracion,
                    DiaDeReserva=dia_reserva,
                    HoraDeReserva=hora_reserva
                )
                db.session.add(nuevo_turno)
                db.session.commit()
                flash('Turno reservado exitosamente.', 'success')
            return redirect(url_for('reservar_turnos_formulario'))

        canchas = Cancha.query.all()
        return render_template('reservar_turnos.html', canchas=canchas, title='Reservar Turnos')

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /reservar-turnos: {str(e)}")
        flash("Error al reservar el turno.", "danger")
        return redirect(url_for('index'))

@app.route('/editar_turno/<int:turno_id>', methods=['GET', 'POST'])
def editar_turno(turno_id):
    try:
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
            turno_obj = db.session.get(Turno, turno_id)
            turno_obj.Dia = request.form['dia']
            turno_obj.HoraDeTurno = request.form['hora_de_turno']
            turno_obj.Cliente = request.form['cliente']
            turno_obj.CanchaID = request.form['cancha_id']
            turno_obj.HorasSolicitadas = request.form['horas_solicitadas']
            turno_obj.DiaDeReserva = request.form['dia_de_reserva']
            turno_obj.HoraDeReserva = request.form['hora_de_reserva']
            db.session.commit()
            flash("Turno actualizado correctamente.", "success")
            return redirect(url_for('turnos'))

        return render_template('editar_turno.html', turno=turno_dict, canchas=canchas)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /editar_turno/{turno_id}: {str(e)}")
        flash("Error al editar el turno.", "danger")
        return redirect(url_for('turnos'))

@app.route('/eliminar-turno/<int:turno_id>', methods=['POST'])
def eliminar_turno(turno_id):
    try:
        turno = Turno.query.get_or_404(turno_id)  # Corregido: Usar Turno, no Precio
        db.session.delete(turno)
        db.session.commit()
        flash("Turno eliminado correctamente.", "success")
        return redirect(url_for('turnos'))
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /eliminar-turno/{turno_id}: {str(e)}")
        flash("Error al eliminar el turno.", "danger")
        return redirect(url_for('turnos'))

@app.route('/configurar-precios/', methods=['GET', 'POST'])
def configurar_precios():
    try:
        if request.method == 'POST':
            cancha_id = request.form['cancha_id']
            tipo_precio = request.form['tipo_precio']
            precio = request.form['precio']
            nuevo_precio = Precio(CanchaID=cancha_id, TipoPrecio=tipo_precio, Precio=precio)
            db.session.add(nuevo_precio)
            db.session.commit()
            flash("Precio configurado correctamente.", "success")
            return redirect(url_for('configurar_precios'))

        canchas = Cancha.query.all()
        precios = Precio.query.all()
        return render_template('configurar_precios.html', canchas=canchas, precios=precios)

    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /configurar-precios: {str(e)}")
        flash("Error al configurar precios.", "danger")
        return redirect(url_for('admin_index'))

@app.route('/editar-precio/<int:precio_id>', methods=['GET', 'POST'])
def editar_precio(precio_id):
    try:
        precio = Precio.query.get_or_404(precio_id)
        canchas = Cancha.query.all()
        if request.method == 'POST':
            precio.CanchaID = request.form['cancha_id']
            precio.TipoPrecio = request.form['tipo_precio']
            precio.Precio = request.form['precio']
            db.session.commit()
            flash("Precio actualizado correctamente.", "success")
            return redirect(url_for('configurar_precios'))
        return render_template('editar_precio.html', precio=precio, canchas=canchas)
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /editar-precio/{precio_id}: {str(e)}")
        flash("Error al editar el precio.", "danger")
        return redirect(url_for('configurar_precios'))

@app.route('/eliminar-precio/<int:precio_id>', methods=['POST'])
def eliminar_precio(precio_id):
    try:
        precio = Precio.query.get_or_404(precio_id)
        db.session.delete(precio)
        db.session.commit()
        flash("Precio eliminado correctamente.", "success")
        return redirect(url_for('configurar_precios'))
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos en /eliminar-precio/{precio_id}: {str(e)}")
        flash("Error al eliminar el precio.", "danger")
        return redirect(url_for('configurar_precios'))

@app.route("/reporte")
def reporte_recaudacion():
    try:
        cancha_id = request.args.get("cancha_id", type=int)
        tipo_cesped = request.args.get("tipo_cesped", type=str)
        desde_str = request.args.get("desde", type=str)
        hasta_str = request.args.get("hasta", type=str)

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
            query = query.add_columns(Cancha.Tipo).filter(Cancha.Tipo == tipo_cesped).group_by(Cancha.Tipo)

        resultados = query.all()
        print("Resultados obtenidos:", resultados)

        if not cancha_id and not tipo_cesped:
            total_recaudado = resultados[0].total_recaudado if resultados else 0
            return render_template("reporte_rec.html", total_recaudado={"Total": total_recaudado})

        total_recaudado = {
            resultado.NombreCancha if cancha_id else resultado.Tipo: resultado.total_recaudado
            for resultado in resultados
        } if resultados else {}

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
    app.run(debug=True)