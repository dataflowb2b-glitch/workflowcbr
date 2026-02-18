from flask import request, redirect, url_for, render_template, session
from werkzeug.utils import secure_filename
from supabase import create_client
import uuid
import os

SUPABASE_URL = "https://qoohwyaajiapqyjvotms.supabase.co"
SUPABASE_KEY = "SUA_SERVICE_ROLE_KEY_AQUI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/novo_envio', methods=['GET', 'POST'])
def novo_envio():
    if request.method == 'POST':

        cliente = request.form.get('cliente')
        numero_nf = request.form.get('numero_nf')
        teve_devolucao = request.form.get('teve_devolucao')
        teve_descarga = request.form.get('teve_descarga')

        foto_canhoto = request.files.get('foto_canhoto')
        foto_devolucao = request.files.get('foto_devolucao')
        foto_descarga = request.files.get('foto_descarga')

        url_canhoto = None
        url_devolucao = None
        url_descarga = None

        # ==========================
        # Upload CANHOTO
        # ==========================
        if foto_canhoto:
            nome_arquivo = f"{uuid.uuid4()}_{secure_filename(foto_canhoto.filename)}"
            supabase.storage.from_("entregas").upload(
                nome_arquivo,
                foto_canhoto.read(),
                {"content-type": foto_canhoto.content_type}
            )

            url_canhoto = supabase.storage.from_("entregas").get_public_url(nome_arquivo)

        # ==========================
        # Upload DEVOLUÇÃO
        # ==========================
        if teve_devolucao == "Sim" and foto_devolucao and foto_devolucao.filename != "":
            nome_arquivo_dev = f"{uuid.uuid4()}_{secure_filename(foto_devolucao.filename)}"
            supabase.storage.from_("entregas").upload(
                nome_arquivo_dev,
                foto_devolucao.read(),
                {"content-type": foto_devolucao.content_type}
            )

            url_devolucao = supabase.storage.from_("entregas").get_public_url(nome_arquivo_dev)

        # ==========================
        # Upload DESCARGA
        # ==========================
        if teve_descarga == "Sim" and foto_descarga and foto_descarga.filename != "":
            nome_arquivo_desc = f"{uuid.uuid4()}_{secure_filename(foto_descarga.filename)}"
            supabase.storage.from_("entregas").upload(
                nome_arquivo_desc,
                foto_descarga.read(),
                {"content-type": foto_descarga.content_type}
            )

            url_descarga = supabase.storage.from_("entregas").get_public_url(nome_arquivo_desc)

        # ==========================
        # SALVAR NO BANCO
        # ==========================
        supabase.table("envios").insert({
            "cliente": cliente,
            "numero_nf": numero_nf,
            "canhoto_url": url_canhoto,
            "teve_devolucao": teve_devolucao,
            "foto_devolucao_url": url_devolucao,
            "teve_descarga": teve_descarga,
            "foto_descarga_url": url_descarga
        }).execute()

        return redirect(url_for('meus_envios'))

    return render_template('novo_envio.html')
