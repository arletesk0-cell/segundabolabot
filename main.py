
import os
import requests
import random
import datetime
import html
import xml.etree.ElementTree as ET

from email.utils import parsedate_to_datetime
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ==================================================
# CONFIGURAÇÕES
# ==================================================

AUTOR = "Armando Massoca"
MINIMO_PALAVRAS = 450
MODELO_GEMINI = "gemini-3-flash-preview"

CATEGORIAS = [
    {
        "nome": "Champions League",
        "query": "Champions League",
        "pixabay": "soccer stadium night lights",
        "unsplash": "champions league football stadium",
        "label": "Champions League"
    },
    {
        "nome": "Europa League",
        "query": "Europa League",
        "pixabay": "soccer stadium night",
        "unsplash": "european football stadium",
        "label": "Europa League"
    },
    {
        "nome": "Conference League",
        "query": "Conference League",
        "pixabay": "football stadium night",
        "unsplash": "football stadium night",
        "label": "Conference League"
    },
    {
        "nome": "Premier League",
        "query": "Premier League",
        "pixabay": "football player action",
        "unsplash": "english football soccer match",
        "label": "Premier League"
    },
    {
        "nome": "La Liga",
        "query": "La Liga Real Madrid Barcelona",
        "pixabay": "football player",
        "unsplash": "spanish football stadium",
        "label": "La Liga"
    },
    {
        "nome": "Serie A",
        "query": "Serie A Italia Inter Milan Juventus",
        "pixabay": "football player",
        "unsplash": "italian football stadium",
        "label": "Serie A"
    },
    {
        "nome": "Bundesliga",
        "query": "Bundesliga Bayern Dortmund",
        "pixabay": "football player",
        "unsplash": "german football stadium",
        "label": "Bundesliga"
    },
    {
        "nome": "Ligue 1",
        "query": "Ligue 1 PSG",
        "pixabay": "football player",
        "unsplash": "french football stadium",
        "label": "Ligue 1"
    },
    {
        "nome": "Liga Portugal",
        "query": "Liga Portugal Sporting Benfica Porto",
        "pixabay": "football player",
        "unsplash": "portuguese football stadium",
        "label": "Liga Portugal"
    }
]

random.seed(datetime.datetime.now().timestamp())


# ==================================================
# VERIFICAR CONFIGURAÇÕES
# ==================================================

OBRIGATORIAS = [
    "GEMINI_KEY",
    "BLOG_ID",
    "BLOGGER_CLIENT_ID",
    "BLOGGER_CLIENT_SECRET",
    "BLOGGER_REFRESH_TOKEN"
]

for chave in OBRIGATORIAS:
    if not os.environ.get(chave):
        raise ValueError(
            f"Configuração obrigatória em falta: {chave}"
        )

print("Configurações verificadas.")


# ==================================================
# DATA DE MAPUTO
# ==================================================

FUSO_MAPUTO = datetime.timezone(
    datetime.timedelta(hours=2)
)

agora_maputo = datetime.datetime.now(FUSO_MAPUTO)

meses = [
    "janeiro", "fevereiro", "março", "abril",
    "maio", "junho", "julho", "agosto",
    "setembro", "outubro", "novembro", "dezembro"
]

data_formatada = (
    f"{agora_maputo.day} de "
    f"{meses[agora_maputo.month - 1]} de "
    f"{agora_maputo.year}"
)

data_curta = agora_maputo.strftime("%d/%m/%Y")


# ==================================================
# BUSCAR NOTÍCIAS NO GOOGLE NEWS
# ==================================================

def buscar_noticia_recente(query):

    url = "https://news.google.com/rss/search"

    parametros = {
        "q": f"{query} when:2d",
        "hl": "pt-PT",
        "gl": "PT",
        "ceid": "PT:pt"
    }

    try:
        resposta = requests.get(
            url,
            params=parametros,
            timeout=25,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resposta.raise_for_status()

        root = ET.fromstring(resposta.content)

        agora = datetime.datetime.now(
            datetime.timezone.utc
        )

        limite = agora - datetime.timedelta(days=2)

        candidatas = []

        for item in root.findall(".//item"):

            titulo_rss = item.findtext("title") or ""
            descricao = item.findtext("description") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""

            try:
                data_pub = parsedate_to_datetime(pub)

                if data_pub.tzinfo is None:
                    data_pub = data_pub.replace(
                        tzinfo=datetime.timezone.utc
                    )

            except Exception:
                continue

            if data_pub >= limite:

                candidatas.append({
                    "titulo": titulo_rss,
                    "desc": descricao,
                    "link": link,
                    "data": data_pub
                })

        print(
            f"Encontradas {len(candidatas)} notícias "
            f"para {query}"
        )

        if candidatas:
            return random.choice(candidatas)

    except Exception as erro:
        print("Erro Google News:", erro)

    return None


# ==================================================
# ESCOLHER CATEGORIA E NOTÍCIA
# ==================================================

cat = random.choice(CATEGORIAS)

print("CATEGORIA SORTEADA:", cat["nome"])

noticia = buscar_noticia_recente(cat["query"])

tentativas_noticia = 0

while not noticia and tentativas_noticia < 8:

    tentativas_noticia += 1

    cat = random.choice(CATEGORIAS)

    print(
        f"Nova tentativa {tentativas_noticia}: "
        f"{cat['nome']}"
    )

    noticia = buscar_noticia_recente(cat["query"])

if not noticia:
    raise SystemExit("Não foram encontradas notícias recentes.")

print("NOTÍCIA BASE:", noticia["titulo"])
print("DATA DA NOTÍCIA:", noticia["data"])


# ==================================================
# INICIALIZAR GEMINI
# ==================================================

client = genai.Client(
    api_key=os.environ["GEMINI_KEY"],
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)


# ==================================================
# GERAR ARTIGO
# ==================================================

titulo = ""
corpo = []
palavras = 0

for tentativa in range(3):

    prompt = f"""
Escreve um artigo jornalístico para o blog Segunda Bola.

IDIOMA:
Português formal, natural e neutro.

EXTENSÃO:
- Mínimo de 500 palavras.
- Entre 6 e 8 parágrafos longos.
- Cada parágrafo deve desenvolver uma ideia.
- Não escrevas um artigo superficial.

REGRAS:
- Utiliza apenas os factos fornecidos pela notícia.
- Não inventes resultados, golos, declarações ou estatísticas.
- Não inventes datas de próximos jogos.
- Não apresentes rumores como factos.
- Podes acrescentar contexto geral sobre as equipas e competições.
- Se não existirem informações suficientes, não inventes detalhes.

ESTILO:
- Tom sério e profissional.
- Terceira pessoa.
- Linguagem jornalística.
- Sem opiniões pessoais.
- Sem emojis.
- Sem listas.
- Sem subtítulos.
- Sem hashtags.
- Sem links.
- Não menciones Google News ou fontes.
- Não utilizes as palavras: maningue, foguetão,
  magia, nosso craque ou Viva malta.
- Não utilizes eu, nós, nosso ou nossa.

ESTRUTURA:
1. Apresentação do acontecimento.
2. Desenvolvimento dos detalhes conhecidos.
3. Contexto da equipa e da competição.
4. Consequências desportivas.
5. Perspetivas e próximos desafios, sem inventar calendário.
6. Conclusão jornalística.

FORMATO:
A primeira linha deve conter apenas o título.
Depois escreve os parágrafos corridos.

NOTÍCIA REAL:

Título: {noticia['titulo']}
Descrição: {noticia['desc']}
Data: {noticia['data']}
Categoria: {cat['nome']}

Tentativa: {tentativa + 1}.
Escreve um artigo completo, com pelo menos 500 palavras.
"""

    try:

        resposta = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt
        )

        texto = (resposta.text or "").strip()

        texto = texto.replace("**", "")
        texto = texto.replace("---", "")
        texto = texto.replace("#", "")

        linhas = [
            linha.strip()
            for linha in texto.splitlines()
            if linha.strip()
        ]

        if len(linhas) < 2:
            raise ValueError("Resposta incompleta do Gemini.")

        titulo_temp = linhas[0]

        corpo_temp = [
            linha for linha in linhas[1:]
            if not linha.upper().startswith("TEMA:")
            and "google news" not in linha.lower()
            and not linha.lower().startswith("fonte:")
        ]

        palavras_temp = len(
            " ".join(corpo_temp).split()
        )

        print(
            f"Tentativa {tentativa + 1}: "
            f"{palavras_temp} palavras"
        )

        titulo = titulo_temp
        corpo = corpo_temp
        palavras = palavras_temp

        if palavras >= MINIMO_PALAVRAS:
            print("ARTIGO APROVADO.")
            break

    except Exception as erro:
        print("Erro ao gerar artigo:", erro)

        if tentativa == 2:
            raise

if not titulo or not corpo:
    raise SystemExit("O Gemini não conseguiu gerar o artigo.")

if palavras < MINIMO_PALAVRAS:
    raise SystemExit(
        f"Artigo demasiado curto: {palavras} palavras. "
        "Publicação cancelada para evitar conteúdo incompleto."
    )

print("TÍTULO:", titulo)
print("TOTAL DE PALAVRAS:", palavras)


# ==================================================
# BUSCAR IMAGEM NO UNSPLASH
# ==================================================

def buscar_unsplash(pesquisa):

    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")

    if not key:
        print("Unsplash sem chave configurada.")
        return None

    try:

        url = "https://api.unsplash.com/search/photos"

        parametros = {
            "query": pesquisa,
            "orientation": "landscape",
            "per_page": 15,
            "content_filter": "high"
        }

        resposta = requests.get(
            url,
            params=parametros,
            headers={
                "Authorization": f"Client-ID {key}"
            },
            timeout=20
        )

        resposta.raise_for_status()

        resultados = resposta.json().get("results", [])

        if not resultados:
            print("Unsplash não encontrou imagens.")
            return None

        foto = random.choice(resultados)

        return {
            "url": foto["urls"]["regular"],
            "autor": foto["user"]["name"],
            "perfil": foto["user"]["links"]["html"],
            "pagina": foto["links"]["html"],
            "origem": "Unsplash"
        }

    except Exception as erro:

        print("Erro Unsplash:", erro)

        return None


# ==================================================
# BUSCAR IMAGEM NO PIXABAY
# ==================================================

def buscar_pixabay(pesquisa):

    key = os.environ.get("PIXABAY_API_KEY", "")

    if not key:
        return None

    try:

        url = "https://pixabay.com/api/"

        parametros = {
            "key": key,
            "q": pesquisa,
            "image_type": "photo",
            "orientation": "horizontal",
            "per_page": 15,
            "safesearch": "true",
            "category": "sports"
        }

        resposta = requests.get(
            url,
            params=parametros,
            timeout=20
        )

        resposta.raise_for_status()

        resultados = resposta.json().get("hits", [])

        if resultados:

            foto = random.choice(resultados)

            return {
                "url": foto["largeImageURL"],
                "autor": "",
                "perfil": "",
                "pagina": "",
                "origem": "Pixabay"
            }

    except Exception as erro:

        print("Erro Pixabay:", erro)

    return None


# ==================================================
# BANCO DE IMAGENS DE RESERVA
# ==================================================

BANCO_IMAGENS = [
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop"
]


# ==================================================
# ESCOLHER IMAGEM
# ==================================================

imagem = buscar_unsplash(cat["unsplash"])

if imagem:

    print("IMAGEM ESCOLHIDA: UNSPLASH")

else:

    imagem = buscar_pixabay(cat["pixabay"])

    if imagem:
        print("IMAGEM ESCOLHIDA: PIXABAY")

    else:

        imagem = {
            "url": random.choice(BANCO_IMAGENS),
            "autor": "",
            "perfil": "",
            "pagina": "",
            "origem": "Banco de reserva"
        }

        print("IMAGEM ESCOLHIDA: RESERVA")

foto_url = imagem["url"]


# ==================================================
# CRIAR HTML DO ARTIGO
# ==================================================

titulo_html = html.escape(titulo)
categoria_html = html.escape(cat["nome"])
data_html = html.escape(data_formatada)
data_curta_html = html.escape(data_curta)
foto_html = html.escape(foto_url, quote=True)

html_artigo = f"""
<div style="border-bottom:1px solid #eee;
padding-bottom:12px;margin-bottom:18px;">

<p style="font-size:14px;color:#555;margin:0;">
Por <b>{AUTOR}</b> | {data_html} | {categoria_html}
</p>

<p style="font-size:13px;color:#888;margin:4px 0 0 0;">
Segunda Bola - Futebol Europeu
</p>

</div>

<figure style="margin:0 0 18px 0;">

<img
src="{foto_html}"
alt="{categoria_html} - futebol europeu"
loading="eager"
style="width:100%;height:auto;display:block;
border-radius:10px;"
/>

<figcaption style="font-size:12px;color:#888;
margin-top:6px;">

{categoria_html} - {data_curta_html}
"""

if imagem["origem"] == "Unsplash":

    autor = html.escape(imagem["autor"])
    perfil = html.escape(imagem["perfil"], quote=True)
    pagina = html.escape(imagem["pagina"], quote=True)

    html_artigo += f"""
<br>
Fotografia de
<a href="{perfil}?utm_source=segundabola&utm_medium=referral"
target="_blank" rel="noopener">{autor}</a>
/
<a href="{pagina}?utm_source=segundabola&utm_medium=referral"
target="_blank" rel="noopener">Unsplash</a>
"""

html_artigo += """
</figcaption>
</figure>
"""

for paragrafo in corpo:

    paragrafo_html = html.escape(paragrafo)

    html_artigo += f"""
<p style="font-size:17px;line-height:1.8;
margin-bottom:18px;color:inherit;">
{paragrafo_html}
</p>
"""

hashtag = cat["nome"].replace(" ", "")

html_artigo += f"""
<p style="font-size:14px;color:#0a2a5e;">
<b>#{hashtag} #SegundaBola</b>
</p>

<div style="border-top:1px solid #eee;
margin-top:25px;padding-top:12px;">

<p style="font-size:14px;color:#333;">
Artigo escrito por <b>{AUTOR}</b>
</p>

<p style="font-size:13px;color:#888;">
Publicado em {data_html} |
Categoria: {categoria_html} |
Segunda Bola
</p>

</div>
"""


# ==================================================
# LIGAR AO BLOGGER
# ==================================================

creds = Credentials(
    token=None,
    refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["BLOGGER_CLIENT_ID"],
    client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
    scopes=[
        "https://www.googleapis.com/auth/blogger"
    ]
)

service = build(
    "blogger",
    "v3",
    credentials=creds
)


# ==================================================
# PUBLICAR ARTIGO
# ==================================================

post = {
    "kind": "blogger#post",
    "blog": {
        "id": os.environ["BLOG_ID"]
    },
    "title": titulo,
    "content": html_artigo,
    "labels": [
        cat["label"],
        "Segunda Bola",
        "Futebol"
    ]
}

resultado = service.posts().insert(
    blogId=os.environ["BLOG_ID"],
    body=post
).execute()

print("=" * 50)
print("PUBLICAÇÃO CONCLUÍDA!")
print("TÍTULO:", titulo)
print("CATEGORIA:", cat["nome"])
print("PALAVRAS:", palavras)
print("IMAGEM:", imagem["origem"])
print("LINK:", resultado.get("url"))
print("=" * 50)
