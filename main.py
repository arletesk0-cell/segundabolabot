import os, requests, random, datetime, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# === CATEGORIAS ===
CATEGORIAS = [
    {"nome": "Champions League", "query": "Champions League", "pixabay": "soccer stadium night lights", "label": "Champions League"},
    {"nome": "Europa League", "query": "Europa League", "pixabay": "soccer stadium night", "label": "Europa League"},
    {"nome": "Conference League", "query": "Conference League", "pixabay": "football stadium night", "label": "Conference League"},
    {"nome": "Premier League", "query": "Premier League", "pixabay": "football player action", "label": "Premier League"},
    {"nome": "La Liga", "query": "La Liga Real Madrid Barcelona", "pixabay": "football player", "label": "La Liga"},
    {"nome": "Serie A", "query": "Serie A Italia Inter Milan Juventus", "pixabay": "football player", "label": "Serie A"},
    {"nome": "Bundesliga", "query": "Bundesliga Bayern Dortmund", "pixabay": "football player", "label": "Bundesliga"},
    {"nome": "Ligue 1", "query": "Ligue 1 PSG", "pixabay": "football player", "label": "Ligue 1"},
    {"nome": "Liga Portugal", "query": "Liga Portugal Sporting Benfica Porto", "pixabay": "football player", "label": "Liga Portugal"},
]

random.seed(datetime.datetime.now().timestamp())
cat = random.choice(CATEGORIAS)
print(f"CATEGORIA SORTEADA: {cat['nome']}")

def buscar_noticia_recente(query):
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
            if data_pub >= limite:
                candidatas.append({"titulo": titulo_rss, "desc": desc, "link": link, "data": data_pub})
        print(f"Encontradas {len(candidatas)} noticias de 2 dias para {query}")
        if candidatas:
            return random.choice(candidatas)
    except Exception as e:
        print("Erro Google News:", e)
    return None

noticia = buscar_noticia_recente(cat["query"])
tentativas = 0
while not noticia and tentativas < 4:
    tentativas += 1
    cat = random.choice(CATEGORIAS)
    print(f"Tentativa {tentativas} outra categoria: {cat['nome']}")
    noticia = buscar_noticia_recente(cat["query"])

if not noticia:
    raise SystemExit("Sem noticia atual")

print(f"NOTICIA BASE: {noticia['titulo']} | Data: {noticia['data']}")

client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

# === GERAR ARTIGO COM MINIMO DE PALAVRAS - SE FOR CURTO, TENTA DE NOVO ===
MINIMO_PALAVRAS = 450
titulo = ""
corpo = []
palavras = 0

for tentativa in range(3):
    prompt = f"""Escreve um artigo de noticias para o blog Segunda Bola, em portugues formal e NEUTRO, como jornalista da BBC.
REGRAS OBRIGATORIAS:
- MINIMO 500 PALAVRAS, 6 a 8 paragrafos longos. Artigo curto e PROIBIDO.
- Usa APENAS a informacao desta noticia real. NAO inventes resultados, golos ou declaracoes. Podes acrescentar contexto geral: situacao na classificacao, historico do clube, o que significa este resultado para os proximos jogos, sem inventar numeros.
- NUNCA uses: Viva malta, nosso craque, maningue, Forca, estamos contigo, orgulho, magia, foguetao. NUNCA uses eu, nos, nosso, nossa. NUNCA menciones fonte, Google News, ou link. NUNCA escrevas Fonte:.
- Tom serio, terceira pessoa. Primeira linha APENAS o titulo novo, neutro. Depois so paragrafos corridos, SEM subtitulos, SEM listas, SEM asteriscos, SEM #.
- Desenvolve bem: 1 paragrafo o que aconteceu, 2 paragrafo detalhes do jogo / acontecimento, 3 paragrafo contexto da equipa na liga, 4 paragrafo o que isto muda na classificacao, 5 paragrafo proximos jogos e o que esperar, 6 paragrafo conclusao.

NOTICIA REAL PARA REESCREVER:
Titulo: {noticia['titulo']}
Descricao: {noticia['desc']}
Data: {noticia['data']}
Categoria: {cat['nome']}
Tentativa: {tentativa+1} - se o artigo anterior foi curto, escreve ainda mais longo agora.
"""
    resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    texto = resposta.text.replace("**", "").replace("---", "").replace("#", "").strip()
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    titulo_temp = linhas[0]
    corpo_temp = [l for l in linhas[1:] if not l.upper().startswith("TEMA:") and "fonte" not in l.lower() and "google" not in l.lower()]
    palavras_temp = len(" ".join(corpo_temp).split())
    print(f"Tentativa {tentativa+1}: {palavras_temp} palavras")
    titulo, corpo, palavras = titulo_temp, corpo_temp, palavras_temp
    if palavras >= MINIMO_PALAVRAS:
        print(f"APROVADO: {palavras} palavras")
        break
    else:
        print(f"MUITO CURTO, vou tentar de novo...")

if palavras < MINIMO_PALAVRAS:
    print(f"AVISO: Mesmo apos 3 tentativas ficou com {palavras} palavras, vou publicar assim para nao falhar, mas foi o maximo.")

# === DATA E AUTOR ===
meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
agora_maputo = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
data_formatada = f"{agora_maputo.day} de {meses[agora_maputo.month-1]} de {agora_maputo.year}"
data_curta = agora_maputo.strftime("%d/%m/%Y")
print(f"DATA: {data_formatada} - AUTOR: Armando Massoca - PALAVRAS: {palavras}")

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

BANCO = [
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop",
]
foto_url = buscar_pixabay(cat["pixabay"]) or random.choice(BANCO)

html = f'''
<div style="border-bottom:1px solid #eee; padding-bottom:12px; margin-bottom:18px;">
  <p style="font-size:14px; color:#555; margin:0;">Por <b>Armando Massoca</b> | {data_formatada} | {cat["nome"]}</p>
  <p style="font-size:13px; color:#888; margin:4px 0 0 0;">Segunda Bola - Futebol Europeu</p>
</div>
<img src="{foto_url}" style="width:100%; border-radius:10px; margin-bottom:15px;" />
<p style="font-size:13px; color:#888;">{cat["nome"]} - {data_curta}</p>
'''

for linha in corpo:
    html += f'<p style="font-size:17px; line-height:1.7;">{linha}</p>'

html += f'<p style="font-size:14px; color:#0a2a5e;"><b>#{cat["nome"].replace(" ", "")} #SegundaBola</b></p>'
html += f'<div style="border-top:1px solid #eee; margin-top:25px; padding-top:12px;"><p style="font-size:14px; color:#333;">Artigo escrito por <b>Armando Massoca</b></p><p style="font-size:13px; color:#888;">Publicado em {data_formatada} | Categoria: {cat["nome"]} | Segunda Bola</p></div>'

creds = Credentials(token=None, refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["BLOGGER_CLIENT_ID"], client_secret=os.environ["BLOGGER_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/blogger"])
service = build("blogger", "v3", credentials=creds)

post = {
    "kind": "blogger#post",
    "blog": {"id": os.environ["BLOG_ID"]},
    "title": titulo,
    "content": html,
    "labels": [cat["label"], "Segunda Bola", "Futebol"]
}
res = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print(f"Publicado na categoria {cat['label']}: {res.get('url')}")
