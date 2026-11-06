import os, requests, random, hashlib, datetime, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# === 1. TEMAS - VAI SORTEAR UM A CADA TESTE ===
TEMAS = [
    ("Geny Catamo", "Geny Catamo Sporting"),
    ("Champions League", "Champions League"),
    ("Mambas", "Mocambique Mambas selecao"),
    ("Reinildo Mandava", "Reinildo Mandava Atletico Madrid"),
    ("Sporting CP", "Sporting CP"),
    ("Liga Portugal", "Liga Portugal Benfica Porto Sporting"),
    ("Mocambola", "Mocambola Mocambique"),
    ("Real Madrid", "Real Madrid"),
    ("Barcelona", "FC Barcelona"),
    ("Premier League", "Premier League"),
    ("Mundial 2026", "Mundial 2026"),
    ("Mercado Transferencias", "mercado transferencias futebol"),
]

random.seed(datetime.datetime.now().timestamp())
tema_nome, query_news = random.choice(TEMAS)
print(f"TEMA SORTEADO: {tema_nome}")

# === 2. BUSCAR NOTICIA REAL DOS ULTIMOS 2 DIAS NO GOOGLE NEWS ===
def buscar_noticia_recente(query):
    # Google News RSS em portugues
    url = f"https://news.google.com/rss/search?q={query}%20when:2d&hl=pt-PT&gl=PT&ceid=PT:pt"
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        agora = datetime.datetime.now(datetime.timezone.utc)
        limite = agora - datetime.timedelta(days=2)
        candidatas = []
        for item in root.findall(".//item"):
            titulo_rss = item.findtext("title") or ""
            desc = item.findtext("description") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""
            try:
                data_pub = parsedate_to_datetime(pub)
                if data_pub.tzinfo is None:
                    data_pub = data_pub.replace(tzinfo=datetime.timezone.utc)
            except:
                continue
            # SO ACEITA SE FOR DOS ULTIMOS 2 DIAS
            if data_pub >= limite:
                candidatas.append({"titulo": titulo_rss, "desc": desc, "link": link, "data": data_pub})
        print(f"Encontradas {len(candidatas)} noticias de 2 dias para {query}")
        if candidatas:
            return random.choice(candidatas)
    except Exception as e:
        print("Erro Google News:", e)
    return None

noticia = buscar_noticia_recente(query_news)

# Se nao achar noticia de 2 dias, tenta outro tema 3 vezes
tentativas = 0
while not noticia and tentativas < 3:
    tentativas += 1
    tema_nome, query_news = random.choice(TEMAS)
    print(f"Tentativa {tentativas} outro tema: {tema_nome}")
    noticia = buscar_noticia_recente(query_news)

if not noticia:
    print("NENHUMA NOTICIA DE 2 DIAS - NAO VOU PUBLICAR NOTICIA VELHA")
    raise SystemExit("Sem noticia atual de 2 dias")

print(f"NOTICIA ORIGINAL: {noticia['titulo']} | Data: {noticia['data']} | Link: {noticia['link']}")

# === 3. GEMINI REESCREVE A NOTICIA REAL, SEM INVENTAR ===
client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

prompt = f"""Escreve um artigo de noticias para o blog Segunda Bola, em portugues formal e NEUTRO, como jornalista da BBC.
REGRAS DURAS:
- Usa APENAS a informacao desta noticia real. NAO inventes resultados, golos, datas ou declaracoes.
- NUNCA uses: Viva malta, nosso craque, maningue, Forca, estamos contigo, orgulho nacional, magia, foguetao, partir tudo. NUNCA uses eu, nos, nosso, nossa.
- Tom serio, terceira pessoa. Primeira linha APENAS o titulo novo, neutro, diferente do original mas com mesmo facto. Depois so paragrafos corridos, SEM subtitulos, SEM listas, SEM asteriscos, SEM #.
- No fim, num paragrafo separado, escreve: Fonte: Google News.

NOTICIA REAL DE HOJE / ONTEM:
Titulo: {noticia['titulo']}
Descricao: {noticia['desc']}
Data: {noticia['data']}
Link: {noticia['link']}
Tema: {tema_nome}
"""

resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
texto = resposta.text.replace("**", "").replace("---", "").replace("#", "").strip()
linhas = [l.strip() for l in texto.split("\n") if l.strip()]
titulo = linhas[0]
corpo = [l for l in linhas[1:] if not l.upper().startswith("TEMA:")]

# === 4. FOTO ===
BANCO_GERAL = [
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1560272564-c83b66b1ad12?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",
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

foto_url = buscar_pixabay(query_news) or random.choice(BANCO_GERAL)

html = f'<img src="{foto_url}" style="width:100%; border-radius:10px; margin-bottom:15px;" /><p style="font-size:13px; color:#888;">Foto: Segunda Bola / Pixabay - Noticia de {noticia["data"].strftime("%d/%m/%Y")}</p>'
for linha in corpo:
    html += f'<p style="font-size:17px; line-height:1.7;">{linha}</p>'
html += f'<p style="font-size:13px; color:#666;">Fonte original: <a href="{noticia["link"]}" target="_blank">Ler noticia original</a></p>'
html += f'<p style="font-size:14px; color:#0a2a5e;"><b>#{tema_nome.replace(" ", "")} #SegundaBola #Futebol</b></p>'

creds = Credentials(token=None, refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["BLOGGER_CLIENT_ID"], client_secret=os.environ["BLOGGER_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/blogger"])
service = build("blogger", "v3", credentials=creds)
post = {"kind": "blogger#post", "blog": {"id": os.environ["BLOG_ID"]}, "title": titulo, "content": html}
res = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado:", res.get("url"))
