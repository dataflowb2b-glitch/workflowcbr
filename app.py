import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from supabase import create_client
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================
# FLASK INIT
# ==============================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")

app.config['PROPAGATE_EXCEPTIONS'] = True
app.debug = True

# ==============================
# DATABASE CONFIG
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada!")

if "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

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

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ SUPABASE não configurado")
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    tipo_devolucao = db.Column(db.String(20))
    foto_devolucao = db.Column(db.String(300))
    teve_descarga = db.Column(db.String(10))
    foto_descarga = db.Column(db.String(300))
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)

# ==============================
# HOME
# ==============================
@app.route("/")
def home():
    return redirect(url_for("login"))

# ==============================
# USER LOADER
# ==============================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# ==============================
# LOGIN
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
# ADMIN DASHBOARD
# ==============================
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.username != "admin":
        return redirect(url_for('meus_envios'))

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    query = Envio.query

    if data_inicio:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        query = query.filter(Envio.data_envio >= inicio)

    if data_fim:
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
        fim = fim.replace(hour=23, minute=59, second=59)
        query = query.filter(Envio.data_envio <= fim)

    envios = query.order_by(Envio.id.desc()).all()
    motoristas = Usuario.query.all()

    return render_template(
        "dashboard_admin.html",
        motoristas=motoristas,
        envios=envios,
        total_envios=len(envios),
        total_devolucoes=len([e for e in envios if e.teve_devolucao == "Sim"]),
        total_descargas=len([e for e in envios if e.teve_descarga == "Sim"]),
        total_motoristas=len(motoristas)
    )

# ==============================
# CADASTRAR MOTORISTA
# ==============================
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

        novo = Usuario(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(novo)
        db.session.commit()

        return redirect(url_for('cadastrar_motorista'))

    motoristas = Usuario.query.filter(Usuario.username != "admin").all()

    return render_template("cadastrar_motorista.html", motoristas=motoristas)

# ==============================
# EXCLUIR MOTORISTA
# ==============================
@app.route('/excluir_motorista/<int:id>', methods=['POST'])
@login_required
def excluir_motorista(id):

    if current_user.username != "admin":
        return redirect(url_for('meus_envios'))

    motorista = Usuario.query.get_or_404(id)

    if motorista.username == "admin":
        return "Não pode excluir admin"

    db.session.delete(motorista)
    db.session.commit()

    return redirect(url_for('cadastrar_motorista'))

# ==============================
# MEUS ENVIOS
# ==============================
@app.route("/meus_envios")
@login_required
def meus_envios():
    envios = Envio.query.filter_by(motorista=current_user.username).all()
    return render_template("meus_envios.html", envios=envios)

# ==============================
# NOVO ENVIO
# ==============================
@app.route("/novo_envio", methods=["GET", "POST"])
@login_required
def novo_envio():

    if request.method == "POST":

        if not supabase:
            return "Erro: Supabase não configurado"

        try:
            motorista = current_user.username
            cliente = request.form.get("cliente")
            numero_nf = request.form.get("numero_nf")

            foto = request.files.get("foto_canhoto")

            if not foto:
                return "Foto obrigatória"

            nome = f"{uuid.uuid4()}_{secure_filename(foto.filename)}"

            supabase.storage.from_("entregas").upload(
                nome,
                foto.read(),
                {"content-type": foto.content_type}
            )

            url = supabase.storage.from_("entregas").get_public_url(nome)

            envio = Envio(
                motorista=motorista,
                cliente=cliente,
                numero_nf=numero_nf,
                foto_canhoto=url
            )

            db.session.add(envio)
            db.session.commit()

            return redirect(url_for("sucesso_envio"))

        except Exception as e:
            print("ERRO:", str(e))
            return f"Erro interno: {str(e)}"

    return render_template("novo_envio.html")

# ==============================
# SUCESSO
# ==============================
@app.route('/sucesso_envio')
@login_required
def sucesso_envio():
    return render_template('sucesso_envio.html')

# ==============================
# START
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
