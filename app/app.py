from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:sarandeameelcabezudo@localhost/proyecto_cancha_2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'  


from models import db, Turno, Precio, Cancha

db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html', title='Inicio')

from flask import Flask, render_template, request
from datetime import datetime
from models import db, Turno, Cancha

from flask import Flask, render_template, request
from datetime import datetime
from models import db, Turno, Cancha

from flask import Flask, render_template, request
from datetime import datetime, time
from models import db, Turno, Cancha

@app.route('/turnos/')
def turnos():
    # Obtener parámetros de filtro de la URL
    cancha_id = request.args.get('cancha_id', type=int)
    cliente = request.args.get('cliente')
    hora = request.args.get('hora', type=str)
    tipoCesped = request.args.get('tipoCesped')
    duracion = request.args.get('duracion', type=int)
    capacidad = request.args.get('capacidad')
    
    
    # Parámetros para el rango de fechas
    fecha_desde = request.args.get('fecha_desde', type=str)
    fecha_hasta = request.args.get('fecha_hasta', type=str)

    # Iniciar la consulta con JOIN
    query = db.session.query(
        Turno.TurnoID, Turno.Dia, Turno.HoraDeTurno, Turno.Cliente, Turno.CanchaID,
        Turno.HorasSolicitadas, Turno.DiaDeReserva, Turno.HoraDeReserva, Cancha.Tipo, Cancha.Jugadores
    ).join(Cancha, Cancha.CanchaID == Turno.CanchaID)  # LEFT JOIN con la tabla Cancha

    # Aplicar filtros dinámicos
    if cancha_id:
        query = query.filter(Turno.CanchaID == cancha_id)
    if cliente:
        query = query.filter(Turno.Cliente.like(f"%{cliente}%"))  # Permite búsqueda parcial
    if hora:
        try:
            # Convertir la cadena 'HH:MM' a un objeto datetime.time
            hora_obj = datetime.strptime(hora, "%H:%M").time()
            query = query.filter(Turno.HoraDeTurno == hora_obj)
        except ValueError:
            pass  # En caso de error en el formato, ignoramos el filtro
    if tipoCesped in ["Natural", "Sintético"]:
        query = query.filter(Cancha.Tipo == tipoCesped)
    if duracion:
        query = query.filter(Turno.HorasSolicitadas == duracion)
    if capacidad:
        query = query.filter(Cancha.Jugadores == capacidad)        
        
    # Aplicar filtros de fecha si existen
    if fecha_desde and fecha_hasta:
        try:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            query = query.filter(Turno.DiaDeReserva.between(fecha_desde, fecha_hasta))
        except ValueError:
            pass  # Ignorar errores en el formato de fecha

    # Ordenar por TurnoID (para evitar que se ordene por CanchaID)
    query = query.order_by(Turno.TurnoID)

    turnos = query.all()  # Ejecutar la consulta

    return render_template('turnos.html', turnos=turnos, title='Turnos')





@app.route('/admin/')
def admin_index():
    return render_template('admin_index.html', title='Gestión Administrativa')

@app.route('/canchas', methods=['GET', 'POST'])
def gestionar_canchas():
    if request.method == 'POST':
        nombre_cancha = request.form.get('nombre_cancha')
        tipo_cancha = request.form.get('tipo_cancha')  
        jugadores = request.form.get('jugadores')  

        nueva_cancha = Cancha(NombreCancha=nombre_cancha, Tipo=tipo_cancha, Jugadores=jugadores)
        db.session.add(nueva_cancha)
        db.session.commit()
        flash("Cancha añadida correctamente", "success")
        return redirect(url_for('gestionar_canchas'))

    canchas = Cancha.query.all()
    return render_template('canchas.html', canchas=canchas)



@app.route('/editar-cancha/<int:id>', methods=['GET', 'POST'])
def editar_cancha(id):
    cancha = Cancha.query.get_or_404(id)

    if request.method == 'POST':
        cancha.NombreCancha = request.form['nombre_cancha']
        cancha.Jugadores = request.form['jugadores']
        cancha.Tipo = request.form['tipo']
        db.session.commit()
        flash("Cancha actualizada correctamente", "success")
        return redirect(url_for('gestionar_canchas'))

    return render_template('editar_cancha.html', cancha=cancha)




@app.route('/eliminar-cancha/<int:id>', methods=['POST'])
def eliminar_cancha(id):
    cancha = Cancha.query.get_or_404(id)
    db.session.delete(cancha)
    db.session.commit()
    flash("Cancha eliminada", "danger")
    return redirect(url_for('gestionar_canchas'))

@app.route('/reservar-turnos/', methods=['GET', 'POST'])
def reservar_turnos_formulario():
    if request.method == 'POST':
        cancha_id = request.form.get('cancha_id')
        dia = request.form.get('dia')
        hora = request.form.get('hora')
        duracion = request.form.get('duracion')
        cliente = request.form.get('cliente')

        conflictos = Turno.query.filter_by(CanchaID=cancha_id, Dia=dia, HoraDeTurno=hora).all()
        if conflictos:
            flash('El turno seleccionado no está disponible. Intenta con otro horario.', 'error')
        else:
            nuevo_turno = Turno(
                Dia=dia,
                HoraDeTurno=hora,
                Cliente=cliente,
                CanchaID=cancha_id,
                HorasSolicitadas=duracion,
                DiaDeReserva=request.form.get('dia_reserva'),
                HoraDeReserva=request.form.get('hora_reserva')
            )
            db.session.add(nuevo_turno)
            db.session.commit()
            flash('Turno reservado exitosamente.', 'turno')  
            return redirect(url_for('reservar_turnos_formulario'))

    
    canchas = Cancha.query.all()
    return render_template('reservar_turnos.html', canchas=canchas, title='Reservar Turnos')

@app.route('/editar_turno/<int:turno_id>', methods=['GET', 'POST'])
def editar_turno(turno_id):
    # Consultar el turno específico con datos de la cancha
    turno = db.session.query(
        Turno.TurnoID, Turno.Dia, Turno.HoraDeTurno, Turno.Cliente, 
        Turno.CanchaID, Turno.HorasSolicitadas, Turno.DiaDeReserva, 
        Turno.HoraDeReserva, Cancha.Tipo, Cancha.Jugadores
    ).join(Cancha, Cancha.CanchaID == Turno.CanchaID).filter(Turno.TurnoID == turno_id).first()

    if not turno:
        return "Turno no encontrado", 404

    # Convertir la tupla en un diccionario
    turno_dict = {
        "TurnoID": turno[0],
        "Dia": turno[1],
        "HoraDeTurno": turno[2],
        "Cliente": turno[3],
        "CanchaID": turno[4],
        "HorasSolicitadas": turno[5],
        "DiaDeReserva": turno[6],
        "HoraDeReserva": turno[7],
        "Tipo": turno[8],
        "Jugadores": turno[9],
    }

    # Obtener todas las canchas para mostrarlas en el select
    canchas = db.session.query(Cancha.CanchaID, Cancha.Tipo, Cancha.Jugadores).all()

    # Si la solicitud es POST, actualiza los datos
    if request.method == 'POST':
        turno_obj = db.session.get(Turno, turno_id)
        if turno_obj:
            turno_obj.Dia = request.form['dia']
            turno_obj.HoraDeTurno = request.form['hora_de_turno']
            turno_obj.Cliente = request.form['cliente']
            turno_obj.CanchaID = request.form['cancha_id']
            turno_obj.HorasSolicitadas = request.form['horas_solicitadas']
            turno_obj.DiaDeReserva = request.form['dia_de_reserva']
            turno_obj.HoraDeReserva = request.form['hora_de_reserva']

            db.session.commit()
            return redirect(url_for('turnos'))  # Redirigir después de la edición

    return render_template('editar_turno.html', turno=turno_dict, canchas=canchas)


@app.route('/eliminar-turno/<int:turno_id>', methods=['POST'])
def eliminar_turno(turno_id):
    turno = Precio.query.get_or_404(turno_id)
    db.session.delete(turno)
    db.session.commit()
    flash("Turno eliminado correctamente", "success")
    return redirect(url_for('turnos'))


@app.route('/configurar-precios/', methods=['GET', 'POST'])
def configurar_precios():
    if request.method == 'POST':
        cancha_id = request.form['cancha_id']
        tipo_precio = request.form['tipo_precio']
        precio = request.form['precio']

        nuevo_precio = Precio(CanchaID=cancha_id, TipoPrecio=tipo_precio, Precio=precio)
        db.session.add(nuevo_precio)
        db.session.commit()
        return redirect(url_for('configurar_precios'))

    canchas = Cancha.query.all()
    precios = Precio.query.all()
    return render_template('configurar_precios.html', canchas=canchas, precios=precios)


@app.route('/editar-precio/<int:precio_id>', methods=['GET', 'POST'])
def editar_precio(precio_id):
    precio = Precio.query.get_or_404(precio_id)
    canchas = Cancha.query.all()  

    if request.method == 'POST':
        precio.CanchaID = request.form['cancha_id']
        precio.TipoPrecio = request.form['tipo_precio']
        precio.Precio = request.form['precio']
        db.session.commit()
        return redirect(url_for('configurar_precios'))

    return render_template('editar_precio.html', precio=precio, canchas=canchas)


@app.route('/eliminar-precio/<int:precio_id>', methods=['POST'])
def eliminar_precio(precio_id):
    precio = Precio.query.get_or_404(precio_id)
    db.session.delete(precio)
    db.session.commit()
    flash("Precio eliminado correctamente", "success")
    return redirect(url_for('configurar_precios'))

@app.route('/reporte/')
def reporte():
    total_recaudado = db.session.query(
        func.sum(Turno.HorasSolicitadas * Precio.TipoPrecio)
    ).join(Precio, Turno.CanchaID == Precio.CanchaID).scalar()

    return render_template('reporte_rec.html', total_recaudado=total_recaudado)


if __name__ == '__main__':
    app.run(debug=True)


