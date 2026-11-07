
import os
import requests
import random
import datetime
import html
import re
import hashlib
import unicodedata
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

for variavel in OBRIGATORIAS:
    if not os.environ.get(variavel):
        raise ValueError(
            f"Configuracao em falta: {variavel}"
        )

MINIMO_PALAVRAS = 450
MAX_TENTATIVAS_ARTIGO = 3
MAX_PUBLICACOES_CONSULTADAS = 100

random.seed(datetime.datetime.now().timestamp())


# ==================================================
# 2. CATEGORIAS
# ==================================================

CATEGORIAS = [
    {
        "nome": "Champions League",
        "query": "Champions League",
        "pixabay": "soccer stadium night lights",
        "label": "Champions League"
    },
    {
        "nome": "Europa League",
        "query": "Europa League",
        "pixabay": "soccer stadium night",
        "label": "Europa League"
    },
    {
        "nome": "Conference League",
        "query": "Conference League",
        "pixabay": "football stadium night",
        "label": "Conference League"
    },
    {
        "nome": "Premier League",
        "query": "Premier League",
        "pixabay": "football player action",
        "label": "Premier League"
    },
    {
        "nome": "La Liga",
        "query": "La Liga Real Madrid Barcelona",
        "pixabay": "football player",
        "label": "La Liga"
    },
    {
        "nome": "Serie A",
        "query": "Serie A Italia Inter Milan Juventus",
        "pixabay": "football player",
        "label": "Serie A"
    },
    {
        "nome": "Bundesliga",
        "query": "Bundesliga Bayern Dortmund",
        "pixabay": "football player",
        "label": "Bundesliga"
    },
    {
        "nome": "Ligue 1",
        "query": "Ligue 1 PSG",
        "pixabay": "football player",
        "label": "Ligue 1"
    },
    {
        "nome": "Liga Portugal",
        "query": "Liga Portugal Sporting Benfica Porto",
        "pixabay": "football player",
        "label": "Liga Portugal"
    }
]


# ==================================================
# 3. INICIAR GEMINI
# ==================================================

client = genai.Client(
    api_key=os.environ["GEMINI_KEY"],
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)

print("Gemini iniciado com sucesso!")


# ==================================================
# 4. LIGAR AO BLOGGER
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

BLOG_ID = os.environ["BLOG_ID"]


# ==================================================
# 5. NORMALIZAR TEXTO E LINKS
# ==================================================

def normalizar_texto(texto):

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


def criar_hash(valor):

    return hashlib.sha256(
        valor.encode("utf-8")
    ).hexdigest()


def identificadores_noticia(noticia):

    link = normalizar_link(
        noticia["link"]
    )

    titulo_original = normalizar_texto(
        noticia["titulo"]
    )

    return {
        "url_hash": criar_hash(link),
        "titulo_hash": criar_hash(titulo_original),
        "titulo_normalizado": titulo_original
    }


# ==================================================
# 6. CONSULTAR PUBLICACOES DO BLOGGER
# ==================================================

def consultar_publicacoes():

    publicacoes = []

    try:

        resposta = service.posts().list(
            blogId=BLOG_ID,
            maxResults=MAX_PUBLICACOES_CONSULTADAS,
            fetchBodies=True,
            orderBy="PUBLISHED"
        ).execute()

        publicacoes.extend(
            resposta.get("items", [])
        )

        print(
            "Publicacoes consultadas:",
            len(publicacoes)
        )

        return publicacoes

    except Exception as erro:

        print(
            "ERRO ao consultar publicacoes do Blogger:",
            erro
        )

        raise RuntimeError(
            "Nao foi possivel verificar noticias duplicadas. "
            "Publicacao cancelada por seguranca."
        )


# ==================================================
# 7. CRIAR BANCO DE NOTICIAS JA PUBLICADAS
# ==================================================

def construir_banco_duplicados(publicacoes):

    urls_publicadas = set()
    titulos_publicados = set()

    for post in publicacoes:

        conteudo = post.get("content", "") or ""

        titulo = post.get("title", "") or ""

        status = post.get("status", "LIVE")

        if status != "LIVE":
            continue

        titulo_normalizado = normalizar_texto(
            titulo
        )

        if titulo_normalizado:
            titulos_publicados.add(
                titulo_normalizado
            )

        url_match = re.search(
            r"SEGUNDA_BOLA_SOURCE_URL_HASH:([a-f0-9]+)",
            conteudo
        )

        if url_match:
            urls_publicadas.add(
                url_match.group(1)
            )

        titulo_match = re.search(
            r"SEGUNDA_BOLA_SOURCE_TITLE_HASH:([a-f0-9]+)",
            conteudo
        )

        if titulo_match:
            titulos_publicados.add(
                "HASH:" + titulo_match.group(1)
            )

    print(
        "Links de noticias registados:",
        len(urls_publicadas)
    )

    print(
        "Titulos registados:",
        len(titulos_publicados)
    )

    return urls_publicadas, titulos_publicados


# ==================================================
# 8. VERIFICAR SE A NOTICIA JA FOI PUBLICADA
# ==================================================

def noticia_duplicada(
    noticia,
    urls_publicadas,
    titulos_publicados
):

    ids = identificadores_noticia(noticia)

    if ids["url_hash"] in urls_publicadas:

        print(
            "NOTICIA REPETIDA: link ja publicado."
        )

        return True

    if (
        "HASH:" + ids["titulo_hash"]
        in titulos_publicados
    ):

        print(
            "NOTICIA REPETIDA: titulo original ja publicado."
        )

        return True

    if (
        ids["titulo_normalizado"]
        in titulos_publicados
    ):

        print(
            "NOTICIA REPETIDA: titulo encontrado no Blogger."
        )

        return True

    return False


# ==================================================
# 9. BUSCAR NOTICIAS RECENTES
# ==================================================

def buscar_noticias_recentes(query):

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

        agora = datetime.datetime.now(
            datetime.timezone.utc
        )

        limite = agora - datetime.timedelta(days=2)

        candidatas = []

        for item in root.findall(".//item"):

            titulo = item.findtext("title") or ""
            descricao = item.findtext("description") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""

            try:

                data_pub = parsedate_to_datetime(pub)

                if data_pub.tzinfo is None:

                    data_pub = data_pub.replace(
                        tzinfo=datetime.timezone.utc
                    )

                data_pub = data_pub.astimezone(
                    datetime.timezone.utc
                )

            except Exception:

                continue

            if data_pub >= limite and titulo and link:

                candidatas.append({
                    "titulo": titulo,
                    "desc": descricao,
                    "link": link,
                    "data": data_pub
                })

        candidatas.sort(
            key=lambda x: x["data"],
            reverse=True
        )

        print(
            f"{len(candidatas)} noticias encontradas: {query}"
        )

        return candidatas

    except Exception as erro:

        print(
            "Erro Google News:",
            erro
        )

        return []


# ==================================================
# 10. ESCOLHER NOTICIA SEM DUPLICACAO
# ==================================================

publicacoes = consultar_publicacoes()

urls_publicadas, titulos_publicados = (
    construir_banco_duplicados(publicacoes)
)

categorias_disponiveis = CATEGORIAS.copy()

random.shuffle(categorias_disponiveis)

noticia = None
cat = None

for categoria in categorias_disponiveis:

    print(
        "A pesquisar categoria:",
        categoria["nome"]
    )

    candidatas = buscar_noticias_recentes(
        categoria["query"]
    )

    for candidata in candidatas:

        if noticia_duplicada(
            candidata,
            urls_publicadas,
            titulos_publicados
        ):

            continue

        noticia = candidata
        cat = categoria

        print(
            "NOTICIA NOVA SELECIONADA:",
            noticia["titulo"]
        )

        break

    if noticia:
        break


if not noticia:

    raise SystemExit(
        "Nenhuma noticia nova encontrada. "
        "Todas as noticias verificadas ja foram publicadas."
    )


print("CATEGORIA:", cat["nome"])
print("NOTICIA:", noticia["titulo"])
print("DATA:", noticia["data"])


# ==================================================
# 11. GERAR ARTIGO COM GEMINI
# ==================================================

titulo = ""
corpo = []
palavras = 0

for tentativa in range(MAX_TENTATIVAS_ARTIGO):

    prompt = f"""
Escreve um artigo jornalistico para o blog Segunda Bola.

IDIOMA:
Portugues formal, claro e neutro.

EXTENSAO:
- Minimo de 450 palavras.
- Entre 6 e 8 paragrafos desenvolvidos.
- Nao escrevas um artigo superficial.

REGRAS EDITORIAIS:

1. Usa exclusivamente os factos fornecidos na noticia.
2. Nao inventes resultados, golos, declaracoes ou estatisticas.
3. Nao inventes classificacoes ou proximos jogos.
4. Nao atribuas declaracoes sem confirmacao.
5. Podes acrescentar contexto historico geral seguro.
6. Nao menciones Google News, fontes ou links.
7. Nao escrevas Fonte.
8. Nao uses primeira pessoa.
9. Mantem tom jornalistico serio.
10. Nao uses expressoes informais ou promocionais.

FORMATO:

- Primeira linha: apenas um titulo novo e neutro.
- Depois: 6 a 8 paragrafos corridos.
- Sem subtitulos.
- Sem listas.
- Sem hashtags.
- Sem asteriscos.

NOTICIA REAL:

Titulo: {noticia['titulo']}

Descricao: {noticia['desc']}

Data: {noticia['data']}

Categoria: {cat['nome']}

Tentativa: {tentativa + 1}

Escreve um artigo completo, rigoroso e informativo.
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

            print(
                "Gemini devolveu resposta vazia."
            )

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

        corpo_temp = []

        for linha in linhas[1:]:

            if linha.upper().startswith("TEMA:"):
                continue

            if "google news" in linha.lower():
                continue

            if linha.lower().startswith("fonte:"):
                continue

            corpo_temp.append(linha)

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

            print(
                "ARTIGO APROVADO!"
            )

            break

    except Exception as erro:

        print(
            "Erro Gemini:",
            erro
        )


if palavras < MINIMO_PALAVRAS:

    raise RuntimeError(
        f"Artigo rejeitado: {palavras} palavras. "
        "Publicacao cancelada."
    )


# ==================================================
# 12. DATA E AUTOR
# ==================================================

meses = [
    "janeiro", "fevereiro", "marco",
    "abril", "maio", "junho",
    "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro"
]

fuso_maputo = datetime.timezone(
    datetime.timedelta(hours=2)
)

agora_maputo = datetime.datetime.now(
    fuso_maputo
)

data_formatada = (
    f"{agora_maputo.day} de "
    f"{meses[agora_maputo.month - 1]} de "
    f"{agora_maputo.year}"
)

data_curta = agora_maputo.strftime(
    "%d/%m/%Y"
)

print("DATA:", data_formatada)
print("AUTOR: Armando Massoca")
print("PALAVRAS:", palavras)


# ==================================================
# 13. BUSCAR IMAGEM PIXABAY
# ==================================================

def buscar_pixabay(pesquisa):

    chave = os.environ.get(
        "PIXABAY_API_KEY",
        ""
    )

    if not chave:
        return None

    try:

        resposta = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": chave,
                "q": pesquisa,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": 10,
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

            return random.choice(
                imagens
            )["largeImageURL"]

    except Exception as erro:

        print(
            "Erro Pixabay:",
            erro
        )

    return None


BANCO_IMAGENS = [
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop"
]

foto_url = (
    buscar_pixabay(cat["pixabay"])
    or random.choice(BANCO_IMAGENS)
)


# ==================================================
# 14. CONSTRUIR MARCADORES ANTI-DUPLICACAO
# ==================================================

ids_noticia = identificadores_noticia(
    noticia
)

marcador_url = (
    "<!-- SEGUNDA_BOLA_SOURCE_URL_HASH:"
    + ids_noticia["url_hash"]
    + " -->"
)

marcador_titulo = (
    "<!-- SEGUNDA_BOLA_SOURCE_TITLE_HASH:"
    + ids_noticia["titulo_hash"]
    + " -->"
)


# ==================================================
# 15. CONSTRUIR HTML
# ==================================================

categoria_html = html.escape(
    cat["nome"]
)

foto_html = html.escape(
    foto_url,
    quote=True
)

conteudo_html = f"""
{marcador_url}
{marcador_titulo}

<div style="border-bottom:1px solid #eee;
padding-bottom:12px;margin-bottom:18px;">

<p style="font-size:14px;color:#555;margin:0;">
Por <b>Armando Massoca</b> |
{data_formatada} |
{categoria_html}
</p>

<p style="font-size:13px;color:#888;margin:4px 0 0 0;">
Segunda Bola - Futebol Europeu
</p>

</div>

<img src="{foto_html}"
alt="{categoria_html}"
style="width:100%;height:auto;border-radius:10px;
margin-bottom:15px;" />

<p style="font-size:13px;color:#888;">
{categoria_html} - {data_curta}
</p>
"""

for paragrafo in corpo:

    paragrafo_seguro = html.escape(
        paragrafo
    )

    conteudo_html += f"""
<p style="font-size:17px;line-height:1.7;
margin-bottom:18px;">
{paragrafo_seguro}
</p>
"""


hashtag = cat["nome"].replace(
    " ",
    ""
)

conteudo_html += f"""
<p style="font-size:14px;color:#0a2a5e;">
<b>#{html.escape(hashtag)} #SegundaBola</b>
</p>

<div style="border-top:1px solid #eee;
margin-top:25px;padding-top:12px;">

<p style="font-size:14px;color:#333;">
Artigo escrito por <b>Armando Massoca</b>
</p>

<p style="font-size:13px;color:#888;">
Publicado em {data_formatada} |
Categoria: {categoria_html} |
Segunda Bola
</p>

</div>
"""


# ==================================================
# 16. VERIFICACAO FINAL ANTES DA PUBLICACAO
# ==================================================

# Consulta novamente o Blogger para reduzir
# o risco de duas execucoes publicarem a mesma noticia.

publicacoes_finais = consultar_publicacoes()

urls_finais, titulos_finais = (
    construir_banco_duplicados(
        publicacoes_finais
    )
)

if noticia_duplicada(
    noticia,
    urls_finais,
    titulos_finais
):

    raise SystemExit(
        "Publicacao cancelada: noticia ja publicada "
        "por outra execucao."
    )


# ==================================================
# 17. PUBLICAR NO BLOGGER
# ==================================================

post = {
    "kind": "blogger#post",
    "blog": {
        "id": BLOG_ID
    },
    "title": titulo,
    "content": conteudo_html,
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
    print("CATEGORIA:", cat["label"])
    print("TITULO:", titulo)
    print("PALAVRAS:", palavras)
    print("URL:", resultado.get("url"))
    print("ANTI-DUPLICACAO: ATIVO")
    print("=" * 55)

except Exception as erro:

    print(
        "ERRO AO PUBLICAR NO BLOGGER:",
        erro
    )

    raise
