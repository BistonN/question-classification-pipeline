import os
import json
import requests
import mysql.connector
import pytesseract
from PIL import Image
from io import BytesIO

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

AREAS = [
"Lógica de Programação e Algoritmos",
"Sistemas Operacionais",
"Arquitetura de Redes com IoT",
"Banco de Dados",
"Linguagem de Marcação",
"Programação Back-End",
"Programação Front-End",
"Programação para Dispositivos Móveis",
"Internet das Coisas (IoT)",
"Levantamento de Requisitos"
]

def conectar():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def extrair_texto_imagem(url):

    if not url:
        return ""

    try:
        r = requests.get(url, timeout=10)

        img = Image.open(BytesIO(r.content))

        texto = pytesseract.image_to_string(img)

        return texto

    except:
        return ""

def montar_texto(q):

    return f"""
Pergunta:
{q['titulo']}

Alternativas:
A) {q['resposta_a']}
B) {q['resposta_b']}
C) {q['resposta_c']}
D) {q['resposta_d']}
E) {q['resposta_e']}
"""

def classificar(texto):

    prompt = f"""
Classifique a questão em UMA área.

Áreas possíveis:
{chr(10).join(AREAS)}

Responda apenas em JSON:

{{
"area":"nome_da_area",
"confianca":0.0
}}

Questão:
{texto}
"""

    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    data = r.json()

    if "response" not in data:
        print("Erro Ollama:", data)
        return None, None

    resposta = data["response"].strip()

    try:

        dados = json.loads(resposta)

        area = dados.get("area")
        confianca = dados.get("confianca")

        if area in AREAS:
            return area, confianca

    except:
        pass

    for area in AREAS:
        if area.lower() in resposta.lower():
            return area, None

    return None, None

def salvar_resultado(id_q, area, confianca):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE questoes SET area=%s,confianca=%s WHERE id=%s",
        (area, confianca, id_q)
    )

    conn.commit()

    cursor.close()
    conn.close()

def carregar_questoes():

    conn = conectar()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT *
    FROM questoes
    WHERE area IS NULL
    """)

    questoes = cursor.fetchall()

    cursor.close()
    conn.close()

    return questoes


def main():

    questoes = carregar_questoes()

    print("Questões carregadas:", len(questoes))

    for q in questoes:

        texto = montar_texto(q)

        texto_img = extrair_texto_imagem(q["url_anexo"])

        texto_total = (texto + "\n" + texto_img)[:3000]

        area, confianca = classificar(texto_total)

        if area:

            salvar_resultado(q["id"], area, confianca)

            print(q["id"], area, confianca)

        else:

            print("Falha classificação:", q["id"])


if __name__ == "__main__":
    main()