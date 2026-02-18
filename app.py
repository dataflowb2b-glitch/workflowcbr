from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ==============================
# CONFIG SUPABASE
# ==============================
SUPABASE_URL = "https://qoohwyaajiapqyjvotms.supabase.co"
SUPABASE_KEY = "SUA_SERVICE_ROLE_KEY_AQUI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# LOGIN
# ==============================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        response = supabase.table("motoristas") \
            .select("*") \
            .eq("usuario", usuario) \
            .eq("senha", senha) \
            .execute()

        if response.data:
            session["usuario"] = usuario
            session["motorista_id"] = response.data[0]["id"]
            session["is_admin"] = usuario == "admin"

            if session["is_admin"]:
                return redirect(url_for("admin"))
            return redirect(url_for("meus_envios"))

    return render_template("login.html")


# ==============================
# NOVO ENVIO
# ==============================
@app.route("/novo_envio", methods=["GET", "POST"])
def novo_envio():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        cliente = request.form.get("cliente")
        numero_nf = request.form.get("numero_nf")
        teve_devolucao = request.form.get("teve_devolucao")
        teve_descarga = request.form.get("teve_descarga")

        # VALIDAÇÃO BACKEND
        if teve_devolucao == "Sim" and not request.files.get("foto_devolucao"):
            return "Erro: Foto da devolução é obrigatória.", 400

        if teve_descarga == "Sim" and not request.files.get("foto_descarga"):
            return "Erro: Foto da descarga é obrigatória.", 400

        url_canhoto = None
        url_devolucao = None
        url_descarga = None

        # ==========================
        # CANHOTO
        # ==========================
        foto_canhoto = request.files.get("foto_canhoto")

        if foto_canhoto and foto_canhoto.filename != "":
            nome = f"{uuid.uuid4()}_{secure_filename(foto_canhoto.filename)}"

            supabase.storage.from_("entregas").upload(
                nome,
                foto_canhoto.read(),
                {"content-type": foto_canhoto.content_type}
            )

            url_canhoto = supabase.storage.from_("entregas").get_public_url(nome)

        # ==========================
        # DEVOLUÇÃO
        # ==========================
        if teve_devolucao == "Sim":
            foto_devolucao = request.files.get("foto_devolucao")

            if foto_devolucao and foto_devolucao.filename != "":
                nome_dev = f"{uuid.uuid4()}_{secure_filename(foto_devolucao.filename)}"

                supabase.storage.from_("entregas").upload(
                    nome_dev,
                    foto_devolucao.read(),
                    {"content-type": foto_devolucao.content_type}
                )

                url_devolucao = supabase.storage.from_("entregas").get_public_url(nome_dev)

        # ==========================
        # DESCARGA
        # ==========================
        if teve_descarga == "Sim":
            foto_descarga = request.files.get("foto_descarga")

            if foto_descarga and foto_descarga.filename != "":
                nome_desc = f"{uuid.uuid4()}_{secure_filename(foto_descarga.filename)}"

                supabase.storage.from_("entregas").upload(
                    nome_desc,
                    foto_descarga.read(),
                    {"content-type": foto_descarga.content_type}
                )

                url_descarga = supabase.storage.from_("entregas").get_public_url(nome_desc)

        # ==========================
        # SALVAR NO BANCO
        # ==========================
        supabase.table("envios").insert({
            "motorista_id": session["motorista_id"],
            "cliente": cliente,
            "numero_nf": numero_nf,
            "canhoto_url": url_canhoto,
            "teve_devolucao": teve_devolucao,
            "foto_devolucao_url": url_devolucao,
            "teve_descarga": teve_descarga,
            "foto_descarga_url": url_descarga
        }).execute()

        return redirect(url_for("meus_envios"))

    return render_template("novo_envio.html")


# ==============================
# MEUS ENVIOS
# ==============================
@app.route("/meus_envios")
def meus_envios():

    if "usuario" not in session:
        return redirect(url_for("login"))

    response = supabase.table("envios") \
        .select("*") \
        .eq("motorista_id", session["motorista_id"]) \
        .execute()

    return render_template("meus_envios.html", envios=response.data)


# ==============================
# ADMIN
# ==============================
@app.route("/admin")
def admin():

    if not session.get("is_admin"):
        return redirect(url_for("login"))

    motoristas = supabase.table("motoristas").select("*").execute()
    envios = supabase.table("envios").select("*").execute()

    return render_template(
        "admin.html",
        motoristas=motoristas.data,
        envios=envios.data
    )


# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
