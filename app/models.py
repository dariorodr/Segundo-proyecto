from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Turno(db.Model):
    __tablename__ = 'turnos'
    TurnoID = db.Column(db.Integer, primary_key=True)
    Dia = db.Column(db.String(20))
    HoraDeTurno = db.Column(db.Time)
    Cliente = db.Column(db.String(50))
    CanchaID = db.Column(db.Integer)
    HorasSolicitadas = db.Column(db.Integer)
    DiaDeReserva = db.Column(db.Date)
    HoraDeReserva = db.Column(db.Time)

class Precio(db.Model):
    __tablename__ = 'precios'
    
    PrecioID = db.Column(db.Integer, primary_key=True)
    CanchaID = db.Column(db.Integer, db.ForeignKey('canchas.CanchaID'), nullable=False)
    TipoPrecio = db.Column(db.String(50), nullable=False)
    Precio = db.Column(db.Float, nullable=False)

    cancha = db.relationship('Cancha', backref=db.backref('precios', lazy=True))

class Cancha(db.Model):
    __tablename__ = 'canchas'
    CanchaID = db.Column(db.Integer, primary_key=True)
    NombreCancha = db.Column(db.String(50))
    Tipo = db.Column(db.String(20))
    Jugadores = db.Column(db.Integer, nullable=True)