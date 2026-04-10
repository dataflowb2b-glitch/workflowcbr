import os
import uuid
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from supabase import create_client
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# ==============================
# LOAD ENV
# ==============================
load_dotenv()

# ==============================
# FLASK INIT
# ==============================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# ==============================
# LOGIN CONFIG
# ==============================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ==============================
# SUPABASE CONFIG
# ==============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# DATABASE CONFIG
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==============================
# MODELS
# ==============================
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Envio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    motorista = db.Column(db.String(100))
    cliente = db.Column(db.String(100))
    numero_nf = db.Column(db.String(100))
    foto_canhoto = db.Column(db.String(300))
    teve_devolucao = db.Column(db.String(10))
    foto_devolucao = db.Column(db.String(300))
    teve_descarga = db.Column(db.String(10))
    foto_descarga = db.Column(db.String(300))

# ==============================
# USER LOADER
# ==============================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# ==============================
# ROTA INICIAL (CORRIGE 404)
# ==============================
@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.username == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("meus_envios"))
    return redirect(url_for("login"))

# ==============================
# ROTAS LOGIN
# ==============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if username == "admin":
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('meus_envios'))
        return "Usuário ou senha inválidos"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==============================
# ROTAS ADMIN
# ==============================
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.username != "admin":
        return redirect(url_for('meus_envios'))

    motoristas = Usuario.query.all()
    envios = Envio.query.all()
    return render_template("dashboard_admin.html", motoristas=motoristas, envios=envios)

@app.route('/cadastrar_motorista', methods=['GET', 'POST'])
@login_required
def cadastrar_motorista():
    if current_user.username != "admin":
        return redirect(url_for('meus_envios'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if Usuario.query.filter_by(username=username).first():
            return "Motorista já existe!"

        novo_motorista = Usuario(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(novo_motorista)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template("cadastrar_motorista.html")

# ==============================
# ROTAS MOTORISTA
# ==============================
@app.route('/meus_envios')
@login_required
def meus_envios():
    envios = Envio.query.filter_by(motorista=current_user.username).all()
    return render_template("meus_envios.html", envios=envios)

@app.route('/novo_envio', methods=['GET', 'POST'])
@login_required
def novo_envio():
    if request.method == 'POST':
        motorista = current_user.username
        cliente = request.form['cliente']
        numero_nf = request.form['numero_nf']
        teve_devolucao = request.form['teve_devolucao']
        teve_descarga = request.form['teve_descarga']

        # FOTO CANHOTO
        foto_canhoto = request.files['foto_canhoto']
        nome_canhoto = f"{uuid.uuid4()}_{secure_filename(foto_canhoto.filename)}"
        supabase.storage.from_("entregas").upload(
            nome_canhoto,
            foto_canhoto.read(),
            {"content-type": foto_canhoto.content_type}
        )
        url_canhoto = supabase.storage.from_("entregas").get_public_url(nome_canhoto)

        # FOTO DEVOLUÇÃO
        url_devolucao = None
        if teve_devolucao == "Sim":
            foto_devolucao = request.files['foto_devolucao']
            nome_devolucao = f"{uuid.uuid4()}_{secure_filename(foto_devolucao.filename)}"
            supabase.storage.from_("entregas").upload(
                nome_devolucao,
                foto_devolucao.read(),
                {"content-type": foto_devolucao.content_type}
            )
            url_devolucao = supabase.storage.from_("entregas").get_public_url(nome_devolucao)

        # FOTO DESCARGA
        url_descarga = None
        if teve_descarga == "Sim":
            foto_descarga = request.files['foto_descarga']
            nome_descarga = f"{uuid.uuid4()}_{secure_filename(foto_descarga.filename)}"
            supabase.storage.from_("entregas").upload(
                nome_descarga,
                foto_descarga.read(),
                {"content-type": foto_descarga.content_type}
            )
            url_descarga = supabase.storage.from_("entregas").get_public_url(nome_descarga)

        envio = Envio(
            motorista=motorista,
            cliente=cliente,
            numero_nf=numero_nf,
            foto_canhoto=url_canhoto,
            teve_devolucao=teve_devolucao,
            foto_devolucao=url_devolucao,
            teve_descarga=teve_descarga,
            foto_descarga=url_descarga
        )

        db.session.add(envio)
        db.session.commit()

        return redirect(url_for('meus_envios'))

    return render_template("novo_envio.html")

# ==============================
# START APP
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
