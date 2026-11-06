import os, requests, random
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

prompt = """Escreve um artigo de noticias de futebol para o blog Segunda Bola, em portugues formal e NEUTRO, como um jornalista profissional da BBC ou do Record.
REGRAS DE NEUTRALIDADE: NUNCA uses: Viva malta, nosso craque, nosso Geny, maningue, Forca Geny, estamos contigo, orgulho nacional, magia, mamba, foguetao, partir tudo, espalhar magia. NUNCA uses primeira pessoa: eu, nos, nosso, nossa, estamos, vamos. SEMPRE usa terceira pessoa: O jogador mocambicano Geny Catamo, O extremo do Sporting, O internacional mocambicano. Tom serio, informativo, sem torcida. Primeira linha APENAS o titulo, neutro. Segunda linha APENAS: TEMA: Geny Catamo ou TEMA: Sporting ou TEMA: Mocambique ou TEMA: Liga Portugal. Depois so paragrafos corridos, SEM subtitulos, SEM listas, SEM asteriscos, SEM #. Nao inventes resultados. Tema: Uma noticia atual sobre Geny Catamo, futebol mocambicano ou futebol mundial."""

resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
texto = resposta.text.replace("**", "").replace("---", "").replace("#", "").strip()
linhas = [l.strip() for l in texto.split("\n") if l.strip()]
titulo = linhas[0]
tema = "Sporting"
corpo = []
for l in linhas[1:]:
    if l.upper().startswith("TEMA:"):
        tema = l.replace("TEMA:", "").replace("Tema:", "").strip()
    else:
        corpo.append(l)

# === API DE FOTOS - PIXABAY (chave sai na hora) + OPENVERSE (sem chave) ===
def buscar_pixabay(pesquisa):
    try:
        key = os.environ.get("PIXABAY_API_KEY", "")
        if not key:
            return None
        r = requests.get(f"https://pixabay.com/api/?key={key}&q={pesquisa}&image_type=photo&orientation=horizontal&per_page=5&safesearch=true", timeout=15)
        hits = r.json().get("hits", [])
        if hits:
            return random.choice(hits)["largeImageURL"]
    except Exception as e:
        print("Pixabay falhou:", e)
    return None

def buscar_openverse(pesquisa):
    try:
        r = requests.get(f"https://api.openverse.org/v1/images/?q={pesquisa}&page_size=5&license_type=all", timeout=15)
        results = r.json().get("results", [])
        if results:
            return random.choice(results)["url"]
    except Exception as e:
        print("Openverse falhou:", e)
    return None

if "Geny" in tema:
    tentativas = ["soccer player training", "football stadium", "soccer player"]
elif "Mocambique" in tema:
    tentativas = ["africa soccer", "football stadium africa", "soccer"]
else:
    tentativas = ["football stadium", "soccer stadium", "soccer player"]

foto_url = None
fonte = "Pixabay"
for t in tentativas:
    foto_url = buscar_pixabay(t)
    if foto_url:
        print(f"Foto Pixabay: {t} -> {foto_url}")
        break
    foto_url = buscar_openverse(t)
    if foto_url:
        fonte = "Openverse"
        print(f"Foto Openverse: {t} -> {foto_url}")
        break

if not foto_url:
    foto_url = "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop"
    fonte = "Unsplash"

html = f'<img src="{foto_url}" style="width:100%; border-radius:10px; margin-bottom:15px;" /><p style="font-size:13px; color:#888;">Foto: {fonte} / Segunda Bola</p>'
for linha in corpo:
    html += f'<p style="font-size:17px; line-height:1.7;">{linha}</p>'
html += '<p style="font-size:14px; color:#0a2a5e;"><b>#GenyCatamo #SportingCP #FutebolMocambicano</b></p>'

creds = Credentials(token=None, refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["BLOGGER_CLIENT_ID"], client_secret=os.environ["BLOGGER_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/blogger"])
service = build("blogger", "v3", credentials=creds)
post = {"kind": "blogger#post", "blog": {"id": os.environ["BLOG_ID"]}, "title": titulo, "content": html}
res = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado:", res.get("url"))
