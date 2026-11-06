import os, requests, random, hashlib, datetime
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# === 1. SORTEIA UM TEMA DIFERENTE A CADA TESTE ===
TEMAS = [
    ("Geny Catamo", "Uma noticia atual sobre Geny Catamo no Sporting, forma, golos, assistencias ou mercado"),
    ("Champions League", "Uma noticia atual sobre a Liga dos Campeoes, resultados, classificacao ou proximos jogos grandes"),
    ("Mambas", "Uma noticia atual sobre a Selecao de Mocambique, Mambas, CAN ou qualificacao"),
    ("Reinildo Mandava", "Uma noticia atual sobre Reinildo Mandava no Atletico Madrid"),
    ("Sporting CP", "Uma noticia atual sobre o Sporting CP na Liga Portugal, sem focar so no Geny"),
    ("Liga Portugal", "Uma noticia atual sobre a Liga Portugal, Benfica, Porto, Sporting, Braga"),
    ("Mocambola", "Uma noticia atual sobre a Mocambola, Costa do Sol, Black Bulls, Liga Desportiva de Maputo"),
    ("Real Madrid", "Uma noticia atual sobre o Real Madrid na La Liga ou Champions"),
    ("Barcelona", "Uma noticia atual sobre o Barcelona na La Liga ou Champions"),
    ("Premier League", "Uma noticia atual sobre a Premier League, Arsenal, City, Liverpool, Chelsea"),
    ("Mundial 2026", "Uma noticia atual sobre o Mundial 2026, preparacao, selecoes africanas"),
    ("Mercado de Transferencias", "Uma noticia atual sobre o mercado de transferencias, rumores e confirmacoes em Africa e Europa"),
]

# Sorteia usando a hora atual, para nunca repetir 2 vezes seguidas
random.seed(datetime.datetime.now().timestamp())
tema_escolhido, angulo = random.choice(TEMAS)
print(f"TEMA SORTEADO HOJE: {tema_escolhido} - {angulo}")

client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

prompt = f"""Escreve um artigo de noticias de futebol para o blog Segunda Bola, em portugues formal e NEUTRO, como um jornalista profissional da BBC ou do Record.
REGRAS DE NEUTRALIDADE: NUNCA uses: Viva malta, nosso craque, nosso Geny, maningue, Forca, estamos contigo, orgulho nacional, magia, mamba, foguetao, partir tudo. NUNCA uses primeira pessoa: eu, nos, nosso, nossa, estamos, vamos. SEMPRE usa terceira pessoa. Tom serio, informativo, sem torcida. Primeira linha APENAS o titulo, neutro e diferente. Segunda linha APENAS: TEMA: {tema_escolhido}. Depois so paragrafos corridos, SEM subtitulos, SEM listas, SEM asteriscos, SEM #. Nao inventes resultados. Nao repitas noticias antigas. Tema: {angulo}. Semente aleatoria: {random.randint(1,99999)} - inventa um angulo novo, nao o mais obvio."""

resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
texto = resposta.text.replace("**", "").replace("---", "").replace("#", "").strip()
linhas = [l.strip() for l in texto.split("\n") if l.strip()]
titulo = linhas[0]
corpo = []
for l in linhas[1:]:
    if l.upper().startswith("TEMA:"):
        continue
    else:
        corpo.append(l)

# === 2. FOTO DIFERENTE POR TEMA ===
BANCO_GERAL = [
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1560272564-c83b66b1ad12?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1553778263-73a83bab9b0c?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517466787929-bc90951d0974?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?q=80&w=1200&auto=format&fit=crop",
]

def buscar_pixabay(pesquisa):
    try:
        key = os.environ.get("PIXABAY_API_KEY", "")
        if not key:
            return None
        r = requests.get(f"https://pixabay.com/api/?key={key}&q={pesquisa}&image_type=photo&orientation=horizontal&per_page=10&safesearch=true&category=sports", timeout=15)
        hits = r.json().get("hits", [])
        if hits:
            return random.choice(hits)["largeImageURL"]
    except Exception as e:
        print("Pixabay falhou:", e)
    return None

# Pesquisa Pixabay conforme o tema sorteado
mapa_pesquisa = {
    "Champions League": "soccer stadium night lights",
    "Mambas": "african football player",
    "Mocambola": "african football player",
    "Geny Catamo": "football player",
    "Sporting CP": "football player",
    "Liga Portugal": "football player",
    "Real Madrid": "football player",
    "Barcelona": "football player",
    "Premier League": "football player action",
    "Mundial 2026": "soccer world cup stadium",
    "Mercado de Transferencias": "football player training",
    "Reinildo Mandava": "football player defending",
}
pesquisa = mapa_pesquisa.get(tema_escolhido, "football player")
foto_url = buscar_pixabay(pesquisa)
if not foto_url:
    numero = int(hashlib.md5((titulo + str(datetime.datetime.now())).encode()).hexdigest(), 16) % len(BANCO_GERAL)
    foto_url = BANCO_GERAL[numero]
print(f"Foto: {foto_url}")

html = f'<img src="{foto_url}" style="width:100%; border-radius:10px; margin-bottom:15px;" /><p style="font-size:13px; color:#888;">Foto: Segunda Bola / Pixabay</p>'
for linha in corpo:
    html += f'<p style="font-size:17px; line-height:1.7;">{linha}</p>'
html += f'<p style="font-size:14px; color:#0a2a5e;"><b>#{tema_escolhido.replace(" ", "")} #SegundaBola #Futebol</b></p>'

creds = Credentials(token=None, refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["BLOGGER_CLIENT_ID"], client_secret=os.environ["BLOGGER_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/blogger"])
service = build("blogger", "v3", credentials=creds)
post = {"kind": "blogger#post", "blog": {"id": os.environ["BLOG_ID"]}, "title": titulo, "content": html}
res = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado:", res.get("url"))
