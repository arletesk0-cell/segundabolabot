
import os
import re
import html
import random
import hashlib
import datetime
import requests
import xml.etree.ElementTree as ET

from urllib.parse import urlsplit, urlunsplit
from email.utils import parsedate_to_datetime
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ==================================================
# 1. CONFIGURACOES
# ==================================================

OBRIGATORIAS = [
    "GEMINI_KEY",
    "BLOG_ID",
    "BLOGGER_CLIENT_ID",
    "BLOGGER_CLIENT_SECRET",
    "BLOGGER_REFRESH_TOKEN"
]

for nome in OBRIGATORIAS:
    if not os.environ.get(nome):
        raise ValueError(f"Falta configurar: {nome}")

BLOG_ID = os.environ["BLOG_ID"]

MINIMO_PALAVRAS = 450
MAX_PUBLICACOES = 100

random.seed(datetime.datetime.now().timestamp())


# ==================================================
# 2. CATEGORIAS
# ==================================================

CATEGORIAS = [
    {"nome": "Champions League", "query": "Champions League", "pixabay": "Champions League football stadium", "label": "Champions League"},
    {"nome": "Europa League", "query": "Europa League", "pixabay": "Europa League football", "label": "Europa League"},
    {"nome": "Conference League", "query": "Conference League", "pixabay": "football stadium", "label": "Conference League"},
    {"nome": "Premier League", "query": "Premier League", "pixabay": "English Premier League football", "label": "Premier League"},
    {"nome": "La Liga", "query": "La Liga Real Madrid Barcelona", "pixabay": "Spanish football", "label": "La Liga"},
    {"nome": "Serie A", "query": "Serie A Italia Inter Milan Juventus", "pixabay": "Italian football", "label": "Serie A"},
    {"nome": "Bundesliga", "query": "Bundesliga Bayern Dortmund", "pixabay": "German football", "label": "Bundesliga"},
    {"nome": "Ligue 1", "query": "Ligue 1 PSG", "pixabay": "French football", "label": "Ligue 1"},
    {"nome": "Liga Portugal", "query": "Liga Portugal Sporting Benfica Porto", "pixabay": "Portuguese football", "label": "Liga Portugal"}
]


# ==================================================
# 3. CLUBES E PESQUISAS DE IMAGENS
# ==================================================

CLUBES = {
    "real madrid": "Real Madrid football",
    "real madrid cf": "Real Madrid football",
    "barcelona": "FC Barcelona football",
    "fc barcelona": "FC Barcelona football",
    "manchester city": "Manchester City football",
    "man city": "Manchester City football",
    "manchester united": "Manchester United football",
    "man united": "Manchester United football",
    "arsenal": "Arsenal FC football",
    "liverpool": "Liverpool FC football",
    "chelsea": "Chelsea FC football",
    "tottenham": "Tottenham Hotspur football",
    "newcastle": "Newcastle United football",
    "bayern munich": "Bayern Munich football",
    "bayern": "Bayern Munich football",
    "borussia dortmund": "Borussia Dortmund football",
    "dortmund": "Borussia Dortmund football",
    "psg": "Paris Saint Germain football",
    "paris saint-germain": "Paris Saint Germain football",
    "paris saint germain": "Paris Saint Germain football",
    "inter milan": "Inter Milan football",
    "inter de milao": "Inter Milan football",
    "ac milan": "AC Milan football",
    "juventus": "Juventus football",
    "napoli": "Napoli football",
    "atletico madrid": "Atletico Madrid football",
    "benfica": "Benfica football",
    "sporting": "Sporting CP football",
    "sporting cp": "Sporting CP football",
    "porto": "FC Porto football",
    "monaco": "AS Monaco football"
}


# ==================================================
# 4. INICIAR GEMINI
# ==================================================

client = genai.Client(
    api_key=os.environ["GEMINI_KEY"],
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)

print("Gemini iniciado.")


# ==================================================
# 5. LIGAR AO BLOGGER
# ==================================================

creds = Credentials(
    token=None,
    refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["BLOGGER_CLIENT_ID"],
    client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
    scopes=["https://www.googleapis.com/auth/blogger"]
)

service = build(
    "blogger",
    "v3",
    credentials=creds
)


# ==================================================
# 6. FUNCOES DE NORMALIZACAO
# ==================================================

def normalizar(texto):
    import unicodedata

    texto = unicodedata.normalize(
        "NFKD",
        texto or ""
    )

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    texto = texto.lower()

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    return " ".join(texto.split())


def gerar_hash(texto):
    return hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest()


def normalizar_link(link):
    try:
        partes = urlsplit(link.strip())

        return urlunsplit((
            partes.scheme.lower(),
            partes.netloc.lower(),
            partes.path.rstrip("/"),
            partes.query,
            ""
        ))

    except Exception:
        return link.strip()


# ==================================================
# 7. CONSULTAR PUBLICACOES
# ==================================================

def consultar_publicacoes():

    try:
        resposta = service.posts().list(
            blogId=BLOG_ID,
            maxResults=MAX_PUBLICACOES,
            fetchBodies=True,
            orderBy="PUBLISHED"
        ).execute()

        publicacoes = resposta.get("items", [])

        print(
            "Publicacoes encontradas:",
            len(publicacoes)
        )

        return publicacoes

    except Exception as erro:
        print("Erro ao consultar Blogger:", erro)
        raise RuntimeError(
            "Nao foi possivel verificar duplicacoes."
        )


def construir_banco(publicacoes):

    links = set()
    titulos = set()

    for post in publicacoes:

        if post.get("status", "LIVE") != "LIVE":
            continue

        titulo = normalizar(
            post.get("title", "")
        )

        if titulo:
            titulos.add(titulo)

        conteudo = post.get("content", "") or ""

        url_match = re.search(
            r"SEGUNDA_BOLA_SOURCE_URL_HASH:([a-f0-9]+)",
            conteudo
        )

        titulo_match = re.search(
            r"SEGUNDA_BOLA_SOURCE_TITLE_HASH:([a-f0-9]+)",
            conteudo
        )

        if url_match:
            links.add(url_match.group(1))

        if titulo_match:
            titulos.add(
                "HASH:" + titulo_match.group(1)
            )

    return links, titulos


def verificar_duplicacao(
    noticia,
    links,
    titulos
):

    link_hash = gerar_hash(
        normalizar_link(noticia["link"])
    )

    titulo_hash = gerar_hash(
        normalizar(noticia["titulo"])
    )

    titulo_normalizado = normalizar(
        noticia["titulo"]
    )

    if link_hash in links:
        return True

    if "HASH:" + titulo_hash in titulos:
        return True

    if titulo_normalizado in titulos:
        return True

    return False


# ==================================================
# 8. BUSCAR NOTICIAS RECENTES
# ==================================================

def buscar_noticias(query):

    url = (
        "https://news.google.com/rss/search?"
        f"q={requests.utils.quote(query)}%20when:2d"
        "&hl=pt-PT&gl=PT&ceid=PT:pt"
    )

    try:
        resposta = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resposta.raise_for_status()

        root = ET.fromstring(
            resposta.content
        )

        limite = (
            datetime.datetime.now(
                datetime.timezone.utc
            )
            - datetime.timedelta(days=2)
        )

        noticias = []

        for item in root.findall(".//item"):

            titulo = item.findtext("title") or ""
            descricao = item.findtext("description") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""

            try:
                data = parsedate_to_datetime(pub)

                if data.tzinfo is None:
                    data = data.replace(
                        tzinfo=datetime.timezone.utc
                    )

                data = data.astimezone(
                    datetime.timezone.utc
                )

            except Exception:
                continue

            if data >= limite and titulo and link:

                noticias.append({
                    "titulo": titulo,
                    "desc": descricao,
                    "link": link,
                    "data": data
                })

        noticias.sort(
            key=lambda x: x["data"],
            reverse=True
        )

        return noticias

    except Exception as erro:
        print("Erro Google News:", erro)
        return []


# ==================================================
# 9. ESCOLHER NOTICIA SEM REPETIR
# ==================================================

publicacoes = consultar_publicacoes()

links_publicados, titulos_publicados = (
    construir_banco(publicacoes)
)

categorias = CATEGORIAS.copy()

random.shuffle(categorias)

noticia = None
cat = None

for categoria in categorias:

    print(
        "A procurar:",
        categoria["nome"]
    )

    resultados = buscar_noticias(
        categoria["query"]
    )

    for resultado in resultados:

        if verificar_duplicacao(
            resultado,
            links_publicados,
            titulos_publicados
        ):

            print(
                "Noticia repetida ignorada:",
                resultado["titulo"]
            )

            continue

        noticia = resultado
        cat = categoria

        break

    if noticia:
        break


if not noticia:
    raise SystemExit(
        "Nao existem noticias novas para publicar."
    )

print("NOTICIA:", noticia["titulo"])
print("CATEGORIA:", cat["nome"])


# ==================================================
# 10. GERAR ARTIGO COM GEMINI
# ==================================================

titulo = ""
corpo = []
palavras = 0

for tentativa in range(3):

    prompt = f"""
Escreve um artigo jornalistico para o blog Segunda Bola.

IDIOMA:
Portugues formal e neutro.

EXTENSAO:
- Minimo de 450 palavras.
- Entre 6 e 8 paragrafos desenvolvidos.

REGRAS:
- Usa apenas factos sustentados pela noticia fornecida.
- Nao inventes resultados, golos ou declaracoes.
- Nao inventes classificacoes ou estatisticas.
- Nao inventes datas de proximos jogos.
- Podes acrescentar contexto historico geral seguro.
- Nunca menciones Google News ou fontes.
- Nunca escrevas Fonte.
- Nunca uses primeira pessoa.
- Tom serio e jornalistico.
- Sem expressoes informais.

FORMATO:
Primeira linha: apenas titulo novo e neutro.
Depois: paragrafos corridos.
Sem subtitulos, listas, hashtags ou asteriscos.

NOTICIA REAL:

Titulo: {noticia['titulo']}

Descricao: {noticia['desc']}

Data: {noticia['data']}

Categoria: {cat['nome']}

Tentativa: {tentativa + 1}

Escreve um artigo completo e informativo.
"""

    try:

        resposta = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        texto = (
            resposta.text or ""
        ).strip()

        if not texto:
            continue

        texto = (
            texto
            .replace("**", "")
            .replace("---", "")
            .replace("#", "")
        )

        linhas = [
            linha.strip()
            for linha in texto.splitlines()
            if linha.strip()
        ]

        if len(linhas) < 2:
            continue

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
            break

    except Exception as erro:
        print("Erro Gemini:", erro)


if palavras < MINIMO_PALAVRAS:
    raise RuntimeError(
        "Artigo demasiado curto. Publicacao cancelada."
    )


# ==================================================
# 11. IDENTIFICAR CLUBE PARA IMAGEM
# ==================================================

def construir_pesquisas_imagem(noticia, categoria):

    texto = normalizar(
        noticia["titulo"] + " " + noticia["desc"]
    )

    pesquisas = []

    for clube, pesquisa in CLUBES.items():

        clube_normalizado = normalizar(clube)

        if clube_normalizado in texto:

            if pesquisa not in pesquisas:
                pesquisas.append(pesquisa)

    # Quando nao identifica um clube, usa a categoria.
    if not pesquisas:
        pesquisas.append(
            categoria["pixabay"]
        )

    # Pesquisa alternativa mais abrangente.
    pesquisas.append(
        categoria["pixabay"]
    )

    # Remover pesquisas repetidas.
    resultado = []

    for pesquisa in pesquisas:
        if pesquisa not in resultado:
            resultado.append(pesquisa)

    return resultado[:3]


# ==================================================
# 12. BUSCAR IMAGEM NO PIXABAY
# ==================================================

def buscar_pixabay(pesquisa):

    chave = os.environ.get(
        "PIXABAY_API_KEY",
        ""
    )

    if not chave:
        print("PIXABAY_API_KEY nao configurada.")
        return None

    try:

        resposta = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": chave,
                "q": pesquisa,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": 15,
                "safesearch": "true",
                "category": "sports"
            },
            timeout=20
        )

        resposta.raise_for_status()

        imagens = resposta.json().get(
            "hits",
            []
        )

        if imagens:

            imagem = random.choice(imagens)

            print(
                "Imagem encontrada para:",
                pesquisa
            )

            return imagem["largeImageURL"]

    except Exception as erro:
        print("Erro Pixabay:", erro)

    return None


# ==================================================
# 13. BANCO DE IMAGENS DE SEGURANCA
# ==================================================

BANCO_IMAGENS = [
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop"
]


# ==================================================
# 14. SELECIONAR IMAGEM
# ==================================================

pesquisas = construir_pesquisas_imagem(
    noticia,
    cat
)

foto_url = None

for pesquisa in pesquisas:

    print(
        "Pesquisa de imagem:",
        pesquisa
    )

    foto_url = buscar_pixabay(
        pesquisa
    )

    if foto_url:
        break


if not foto_url:

    foto_url = random.choice(
        BANCO_IMAGENS
    )

    print(
        "A utilizar imagem de seguranca."
    )


# ==================================================
# 15. DATA E AUTOR
# ==================================================

meses = [
    "janeiro", "fevereiro", "marco",
    "abril", "maio", "junho",
    "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro"
]

fuso = datetime.timezone(
    datetime.timedelta(hours=2)
)

agora = datetime.datetime.now(fuso)

data_formatada = (
    f"{agora.day} de "
    f"{meses[agora.month - 1]} de "
    f"{agora.year}"
)

data_curta = agora.strftime(
    "%d/%m/%Y"
)


# ==================================================
# 16. MARCADORES ANTI-DUPLICACAO
# ==================================================

link_hash = gerar_hash(
    normalizar_link(noticia["link"])
)

titulo_hash = gerar_hash(
    normalizar(noticia["titulo"])
)

marcadores = f"""
<!-- SEGUNDA_BOLA_SOURCE_URL_HASH:{link_hash} -->
<!-- SEGUNDA_BOLA_SOURCE_TITLE_HASH:{titulo_hash} -->
"""


# ==================================================
# 17. CONSTRUIR HTML
# ==================================================

categoria_segura = html.escape(
    cat["nome"]
)

foto_segura = html.escape(
    foto_url,
    quote=True
)

html_artigo = f"""
{marcadores}

<div style="border-bottom:1px solid #eee;
padding-bottom:12px;margin-bottom:18px;">

<p style="font-size:14px;color:#555;margin:0;">
Por <b>Armando Massoca</b> |
{data_formatada} |
{categoria_segura}
</p>

<p style="font-size:13px;color:#888;margin:4px 0 0;">
Segunda Bola - Futebol Europeu
</p>

</div>

<img
src="{foto_segura}"
alt="Fotografia ilustrativa de {categoria_segura}"
style="width:100%;height:auto;border-radius:10px;
margin-bottom:15px;"
/>

<p style="font-size:13px;color:#888;">
{categoria_segura} - {data_curta}
</p>
"""

for paragrafo in corpo:

    paragrafo_seguro = html.escape(
        paragrafo
    )

    html_artigo += f"""
<p style="font-size:17px;line-height:1.7;
margin-bottom:18px;">
{paragrafo_seguro}
</p>
"""


html_artigo += f"""
<p style="font-size:14px;color:#0a2a5e;">
<b>#{cat["nome"].replace(" ", "")} #SegundaBola</b>
</p>

<div style="border-top:1px solid #eee;
margin-top:25px;padding-top:12px;">

<p style="font-size:14px;color:#333;">
Artigo escrito por <b>Armando Massoca</b>
</p>

<p style="font-size:13px;color:#888;">
Publicado em {data_formatada} |
Categoria: {categoria_segura} |
Segunda Bola
</p>

</div>
"""


# ==================================================
# 18. VERIFICACAO FINAL
# ==================================================

publicacoes_finais = consultar_publicacoes()

links_finais, titulos_finais = construir_banco(
    publicacoes_finais
)

if verificar_duplicacao(
    noticia,
    links_finais,
    titulos_finais
):

    raise SystemExit(
        "Noticia repetida. Publicacao cancelada."
    )


# ==================================================
# 19. PUBLICAR NO BLOGGER
# ==================================================

post = {
    "kind": "blogger#post",
    "blog": {
        "id": BLOG_ID
    },
    "title": titulo,
    "content": html_artigo,
    "labels": [
        cat["label"],
        "Segunda Bola",
        "Futebol"
    ]
}

try:

    resultado = service.posts().insert(
        blogId=BLOG_ID,
        body=post,
        isDraft=False
    ).execute()

    print("=" * 55)
    print("PUBLICACAO REALIZADA COM SUCESSO!")
    print("TITULO:", titulo)
    print("CATEGORIA:", cat["nome"])
    print("PALAVRAS:", palavras)
    print("IMAGEM:", foto_url)
    print("ANTI-DUPLICACAO: ATIVO")
    print("URL:", resultado.get("url"))
    print("=" * 55)

except Exception as erro:

    print(
        "ERRO AO PUBLICAR:",
        erro
    )

    raise
