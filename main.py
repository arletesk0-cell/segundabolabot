import os, random, requests, google.generativeai as genai

GEMINI_KEY = os.environ.get("GEMINI_KEY")
BLOGGER_CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")
BLOG_ID = os.environ.get("BLOG_ID")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

TEMAS = [
 "Premier League - analise da jornada",
 "La Liga - Real Madrid e Barcelona",
 "Serie A - Inter, Milan, Juventus e Napoli",
 "Bundesliga - Bayern e Dortmund",
 "Ligue 1 - PSG e jovens talentos",
 "Champions League - resumo dos jogos",
 "Europa League - surpresas e resultados",
 "Conference League - equipas pequenas a brilhar",
 "Selecoes - Mambas, Portugal, Brasil, Angola",
 "Futebol Africano - CAN, CAF Champions League, Mocambola",
 "Mercado de transferencias na Europa",
 "Jovens talentos africanos na Europa",
]

def get_access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": BLOGGER_CLIENT_ID,
        "client_secret": BLOGGER_CLIENT_SECRET,
        "refresh_token": BLOGGER_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    return r.json()["access_token"]

def buscar_foto():
    try:
        r = requests.get("https://api.openverse.org/v1/images/", params={"q": "football stadium soccer", "license_type": "commercial", "page_size": 10}, timeout=15)
        data = r.json()
        if data.get("results"):
            img = random.choice(data["results"])
            return img["url"], img.get("creator", "Openverse")
    except: pass
    return "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=1200", "Unsplash"

def gerar_artigo(tema):
    prompt = f"""Escreve uma noticia de futebol em Portugues de Mocambique para o blog Segunda Bola.
Tema: {tema}
Regras:
- Titulo chamativo
- 500 a 700 palavras
- Estilo jornalista desportivo, emocionante, simples
- Nao inventes resultados falsos de hoje. Fala de analise, contexto, historia, taticas, jogadores, o que esperar.
- Divide em subtitulos H2
- Termina com: O que achas? Deixa a tua opiniao nos comentarios.
- Devolve em formato: TITULO: ||| TEXTO EM HTML
"""
    res = model.generate_content(prompt)
    texto = res.text
    if "|||" in texto:
        titulo, corpo = texto.split("|||", 1)
    else:
        titulo, corpo = tema, texto
    return titulo.strip().replace("TITULO:", "").strip(), corpo.strip()

def publicar(titulo, corpo, img_url, autor):
    token = get_access_token()
    html = f'<img src="{img_url}" style="width:100%;border-radius:10px;"><p><i>Foto: {autor} / Openverse - Licenca livre</i></p>{corpo}<p><b>Fonte: Segunda Bola</b></p>'
    r = requests.post(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/", headers={"Authorization": f"Bearer {token}"}, json={"title": titulo, "content": html, "labels": ["Futebol", "Segunda Bola"]})
    print(r.status_code, r.text[:500])
    return r.status_code == 200

if __name__ == "__main__":
    tema = random.choice(TEMAS)
    print("Tema:", tema)
    titulo, corpo = gerar_artigo(tema)
    img, autor = buscar_foto()
    ok = publicar(titulo, corpo, img, autor)
    print("Publicado!" if ok else "Falhou")
