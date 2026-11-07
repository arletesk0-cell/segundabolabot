
import os
import re
import html
import requests
import random
import datetime
import hashlib
import xml.etree.ElementTree as ET

from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# =====================================================
# CONFIGURAÇÕES
# =====================================================

GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip()
BLOG_ID = os.environ.get("BLOG_ID", "").strip()

MINIMO_PALAVRAS = 450
MAX_TENTATIVAS_ARTIGO = 4

AUTOR = "Armando Massoca"

if not GEMINI_KEY:
    raise RuntimeError("GEMINI_KEY não configurada no GitHub Secrets.")

if not BLOG_ID:
    raise RuntimeError("BLOG_ID não configurado no GitHub Secrets.")


# =====================================================
# CATEGORIAS
# =====================================================

CATEGORIAS = [
    {
        "nome": "Champions League",
        "query": "UEFA Champions League",
        "pixabay": "soccer champions league match",
        "unsplash": "soccer champions league stadium"
    },
    {
        "nome": "Europa League",
        "query": "UEFA Europa League",
        "pixabay": "soccer europa league",
        "unsplash": "soccer football stadium"
    },
    {
        "nome": "Conference League",
        "query": "UEFA Conference League",
        "pixabay": "soccer conference league",
        "unsplash": "soccer match stadium"
    },
    {
        "nome": "Premier League",
        "query": "English Premier League",
        "pixabay": "soccer premier league",
        "unsplash": "english soccer football match"
    },
    {
        "nome": "La Liga",
        "query": "La Liga Real Madrid Barcelona",
        "pixabay": "soccer la liga",
        "unsplash": "spanish soccer football match"
    },
    {
        "nome": "Serie A",
        "query": "Serie A Italia Inter Milan Juventus",
        "pixabay": "soccer serie a italy",
        "unsplash": "italian soccer football match"
    },
    {
        "nome": "Bundesliga",
        "query": "Bundesliga Germany Bayern Dortmund",
        "pixabay": "soccer bundesliga germany",
        "unsplash": "german soccer football match"
    },
    {
        "nome": "Ligue 1",
        "query": "Ligue 1 France PSG",
        "pixabay": "soccer ligue 1 france",
        "unsplash": "french soccer football match"
    },
    {
        "nome": "Liga Portugal",
        "query": "Liga Portugal Sporting Benfica Porto",
        "pixabay": "soccer portugal football",
        "unsplash": "portuguese soccer football match"
    }
]


# =====================================================
# CONEXÃO COM BLOGGER
# =====================================================

def conectar_blogger():

    obrigatorias = [
        "BLOGGER_CLIENT_ID",
        "BLOGGER_CLIENT_SECRET",
        "BLOGGER_REFRESH_TOKEN"
    ]

    for nome in obrigatorias:
        if not os.environ.get(nome):
            raise RuntimeError(f"Secret em falta: {nome}")

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

    return build(
        "blogger",
        "v3",
        credentials=creds
    )


service = conectar_blogger()


# =====================================================
# VERIFICAR NOTÍCIAS JÁ PUBLICADAS
# =====================================================

def obter_publicacoes():

    try:

        resultado = service.posts().list(
            blogId=BLOG_ID,
            maxResults=100,
            orderBy="PUBLISHED"
        ).execute()

        return resultado.get("items", [])

    except Exception as e:

        print("Erro ao consultar publicações:", e)
        raise


publicacoes = obter_publicacoes()


def normalizar(texto):

    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9áàâãéêíóôõúç ]", "", texto)

    return " ".join(texto.split())


def gerar_hash(url):

    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()


def noticia_ja_publicada(noticia):

    marcador = gerar_hash(noticia["link"])

    for post in publicacoes:

        conteudo = post.get("content", "")
        titulo_antigo = normalizar(post.get("title", ""))
        titulo_novo = normalizar(noticia["titulo"])

        if f"SEGUNDA_BOLA_SOURCE:{marcador}" in conteudo:
            print("Notícia já publicada. Ignorando.")
            return True

        semelhanca = SequenceMatcher(
            None,
            titulo_antigo,
            titulo_novo
        ).ratio()

        if semelhanca >= 0.92:
            print("Título semelhante já publicado.")
            return True

    return False


# =====================================================
# BUSCAR NOTÍCIAS NO GOOGLE NEWS
# =====================================================

def buscar_noticias_recentes(query):

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

            except Exception:
                continue

            if data < limite:
                continue

            if not titulo or not link:
                continue

            candidatas.append({
                "titulo": titulo,
                "desc": descricao,
                "link": link,
                "data": data
            })

        print(
            f"{len(candidatas)} notícias encontradas: {query}"
        )

        return candidatas

    except Exception as e:

        print("Erro Google News:", e)
        return []


# =====================================================
# ESCOLHER NOTÍCIA SEM REPETIÇÃO
# =====================================================

categorias_sorteadas = CATEGORIAS.copy()
random.shuffle(categorias_sorteadas)

noticia = None
cat = None

for categoria in categorias_sorteadas:

    print("A pesquisar:", categoria["nome"])

    noticias = buscar_noticias_recentes(
        categoria["query"]
    )

    random.shuffle(noticias)

    for candidata in noticias:

        if not noticia_ja_publicada(candidata):

            noticia = candidata
            cat = categoria
            break

    if noticia:
        break


if not noticia:

    raise SystemExit(
        "Não foram encontradas notícias novas para publicar."
    )


print("\nCATEGORIA:", cat["nome"])
print("NOTÍCIA:", noticia["titulo"])
print("DATA:", noticia["data"])


# =====================================================
# GEMINI - GERAÇÃO DO ARTIGO
# =====================================================

client = genai.Client(
    api_key=GEMINI_KEY,
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)


def contar_palavras(texto):

    return len(texto.split())


def limpar_texto(texto):

    texto = texto.replace("**", "")
    texto = texto.replace("---", "")

    texto = re.sub(
        r"^#+\s*",
        "",
        texto,
        flags=re.MULTILINE
    )

    return texto.strip()


def separar_artigo(texto):

    texto = limpar_texto(texto)

    blocos = [
        bloco.strip()
        for bloco in re.split(r"\n\s*\n", texto)
        if bloco.strip()
    ]

    if len(blocos) < 2:

        linhas = [
            linha.strip()
            for linha in texto.splitlines()
            if linha.strip()
        ]

        blocos = linhas

    titulo = blocos[0]

    paragrafos = blocos[1:]

    paragrafos = [
        p for p in paragrafos
        if not p.lower().startswith("fonte:")
        and "google news" not in p.lower()
        and not p.upper().startswith("TEMA:")
    ]

    return titulo, paragrafos


def gerar_artigo():

    for tentativa in range(MAX_TENTATIVAS_ARTIGO):

        print(
            f"\nA gerar artigo: tentativa {tentativa + 1}"
        )

        prompt = f"""
Escreve uma reportagem jornalística para o blog Segunda Bola.

IDIOMA:
Português formal, natural e neutro, adequado ao público
de Moçambique e de língua portuguesa.

ESTILO:
Jornalismo desportivo profissional, rigoroso e equilibrado.

REGRAS OBRIGATÓRIAS:

1. O artigo deve ter entre 500 e 650 palavras.
2. Deve conter entre 6 e 8 parágrafos desenvolvidos.
3. A primeira linha deve apresentar apenas um título novo.
4. Não utilizar subtítulos.
5. Não utilizar listas.
6. Não utilizar hashtags no corpo do artigo.
7. Não utilizar primeira pessoa.
8. Não mencionar Google News nem a fonte original.
9. Não inventar resultados, golos, declarações, estatísticas,
   classificações, transferências ou datas.
10. Utilizar apenas os factos disponibilizados.
11. Acrescentar contexto desportivo apenas quando for
    possível fazê-lo sem inventar informação.
12. Se a notícia não tiver relação com um jogo,
    adaptar o desenvolvimento ao acontecimento.
13. Não repetir a mesma informação para aumentar palavras.
14. Evitar expressões informais e linguagem de adepto.
15. Não utilizar expressões como:
    Viva malta, nosso craque, maningue, Força,
    estamos contigo, orgulho, magia ou foguetão.

ESTRUTURA:

- Primeiro parágrafo: apresentar o acontecimento.
- Segundo parágrafo: desenvolver os detalhes conhecidos.
- Terceiro parágrafo: explicar o contexto desportivo.
- Quarto parágrafo: analisar as consequências.
- Quinto parágrafo: abordar os possíveis próximos passos.
- Sexto parágrafo: apresentar uma conclusão equilibrada.

Se não existirem dados suficientes sobre algum ponto,
não inventes informação.

NOTÍCIA PARA DESENVOLVER:

Título: {noticia["titulo"]}

Descrição: {noticia["desc"]}

Data: {noticia["data"]}

Competição: {cat["nome"]}

FORMATO:
Título na primeira linha.
Uma linha vazia.
Depois, os parágrafos corridos.

Não escrevas qualquer introdução antes do título.
"""

        try:

            resposta = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )

            texto = resposta.text or ""

            titulo_temp, corpo_temp = separar_artigo(
                texto
            )

            palavras_temp = contar_palavras(
                " ".join(corpo_temp)
            )

            print(
                f"Artigo: {palavras_temp} palavras | "
                f"{len(corpo_temp)} parágrafos"
            )

            if (
                palavras_temp >= MINIMO_PALAVRAS
                and len(corpo_temp) >= 6
            ):

                print("ARTIGO APROVADO.")

                return (
                    titulo_temp,
                    corpo_temp,
                    palavras_temp
                )

            print("Artigo insuficiente. Nova tentativa.")

        except Exception as e:

            print("Erro na geração:", e)

    raise RuntimeError(
        "Não foi possível gerar um artigo com pelo menos "
        f"{MINIMO_PALAVRAS} palavras e 6 parágrafos. "
        "A publicação foi cancelada."
    )


titulo, corpo, palavras = gerar_artigo()


# =====================================================
# DATA DE MAPUTO
# =====================================================

fuso_maputo = datetime.timezone(
    datetime.timedelta(hours=2)
)

agora_maputo = datetime.datetime.now(
    fuso_maputo
)

meses = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro"
]

data_formatada = (
    f"{agora_maputo.day} de "
    f"{meses[agora_maputo.month - 1]} de "
    f"{agora_maputo.year}"
)

data_curta = agora_maputo.strftime("%d/%m/%Y")


# =====================================================
# FILTRO DE FUTEBOL AMERICANO
# =====================================================

TERMOS_AMERICAN_FOOTBALL = [
    "american football",
    "nfl",
    "gridiron",
    "quarterback",
    "touchdown",
    "super bowl",
    "shoulder pads",
    "american football helmet"
]


def imagem_e_futebol_americano(texto):

    texto = (texto or "").lower()

    return any(
        termo in texto
        for termo in TERMOS_AMERICAN_FOOTBALL
    )


# =====================================================
# PIXABAY - PRIMEIRA OPÇÃO
# =====================================================

def buscar_pixabay(pesquisa):

    key = os.environ.get(
        "PIXABAY_API_KEY",
        ""
    ).strip()

    if not key:
        print("Pixabay sem API Key.")
        return None

    try:

        resposta = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": key,
                "q": pesquisa,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": 20,
                "safesearch": "true",
                "category": "sports"
            },
            timeout=20
        )

        resposta.raise_for_status()

        resultados = resposta.json().get(
            "hits",
            []
        )

        validas = []

        for imagem in resultados:

            tags = imagem.get("tags", "")

            if imagem_e_futebol_americano(tags):
                continue

            validas.append(imagem)

        if validas:

            imagem = random.choice(validas)

            print("Imagem encontrada no Pixabay.")

            return {
                "url": imagem["largeImageURL"],
                "credito": ""
            }

    except Exception as e:

        print("Erro Pixabay:", e)

    return None


# =====================================================
# UNSPLASH - SEGUNDA OPÇÃO
# =====================================================

def buscar_unsplash(pesquisa):

    key = os.environ.get(
        "UNSPLASH_ACCESS_KEY",
        ""
    ).strip()

    if not key:
        print("Unsplash sem API Key.")
        return None

    try:

        resposta = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": pesquisa,
                "orientation": "landscape",
                "per_page": 20,
                "content_filter": "high"
            },
            headers={
                "Authorization": f"Client-ID {key}"
            },
            timeout=20
        )

        resposta.raise_for_status()

        resultados = resposta.json().get(
            "results",
            []
        )

        validas = []

        for imagem in resultados:

            descricao = " ".join([
                imagem.get("alt_description") or "",
                imagem.get("description") or ""
            ])

            tags = " ".join([
                item.get("title", "")
                for item in imagem.get("tags", [])
            ])

            texto = descricao + " " + tags

            if imagem_e_futebol_americano(texto):
                continue

            validas.append(imagem)

        if validas:

            imagem = random.choice(validas)

            autor = imagem.get(
                "user",
                {}
            )

            nome_autor = html.escape(
                autor.get("name", "Fotógrafo Unsplash")
            )

            link_autor = autor.get(
                "links",
                {}
            ).get("html", "https://unsplash.com")

            link_foto = imagem.get(
                "links",
                {}
            ).get("html", "https://unsplash.com")

            credito = (
                f'Foto: <a href="{html.escape(link_autor, quote=True)}">'
                f'{nome_autor}</a> / '
                f'<a href="{html.escape(link_foto, quote=True)}">'
                f'Unsplash</a>'
            )

            print("Imagem encontrada no Unsplash.")

            return {
                "url": imagem["urls"]["regular"],
                "credito": credito
            }

    except Exception as e:

        print("Erro Unsplash:", e)

    return None


# =====================================================
# BANCO NEUTRO - ÚLTIMA ALTERNATIVA
# =====================================================

BANCO_IMAGENS = [

    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",

    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1200&auto=format&fit=crop",

    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1200&auto=format&fit=crop"

]


def escolher_imagem():

    # PRIMEIRO: PIXABAY

    imagem = buscar_pixabay(
        cat["pixabay"]
    )

    if imagem:
        return imagem

    # SEGUNDO: UNSPLASH

    imagem = buscar_unsplash(
        cat["unsplash"]
    )

    if imagem:
        return imagem

    # TERCEIRO: BANCO NEUTRO

    print("A utilizar imagem do banco neutro.")

    return {
        "url": random.choice(BANCO_IMAGENS),
        "credito": (
            '<a href="https://unsplash.com/">Unsplash</a>'
        )
    }


imagem = escolher_imagem()

foto_url = html.escape(
    imagem["url"],
    quote=True
)

credito_imagem = imagem["credito"]


# =====================================================
# CONSTRUIR HTML DO ARTIGO
# =====================================================

def criar_html():

    marcador = gerar_hash(
        noticia["link"]
    )

    categoria_html = html.escape(
        cat["nome"]
    )

    titulo_html = html.escape(
        titulo
    )

    html_artigo = f"""
<!-- SEGUNDA_BOLA_SOURCE:{marcador} -->

<div style="
    border-bottom:1px solid #eeeeee;
    padding-bottom:12px;
    margin-bottom:18px;
">
    <p style="
        font-size:14px;
        color:#555;
        margin:0;
    ">
        Por <b>{AUTOR}</b> |
        {data_formatada} |
        {categoria_html}
    </p>

    <p style="
        font-size:13px;
        color:#888;
        margin-top:5px;
    ">
        Segunda Bola - Futebol Europeu
    </p>
</div>

<img
    src="{foto_url}"
    alt="{titulo_html}"
    style="
        width:100%;
        height:auto;
        display:block;
        border-radius:10px;
        margin-bottom:8px;
    "
/>

<p style="
    font-size:12px;
    color:#888;
    margin-bottom:18px;
">
    {categoria_html} - {data_curta}
</p>
"""

    if credito_imagem:

        html_artigo += f"""
<p style="
    font-size:11px;
    color:#999;
    margin-top:-10px;
    margin-bottom:18px;
">
    {credito_imagem}
</p>
"""

    for paragrafo in corpo:

        paragrafo_html = html.escape(
            paragrafo
        )

        html_artigo += f"""
<p style="
    font-size:17px;
    line-height:1.8;
    color:#333;
    margin-bottom:18px;
">
    {paragrafo_html}
</p>
"""

    hashtag = cat["nome"].replace(
        " ",
        ""
    )

    html_artigo += f"""
<p style="
    font-size:14px;
    color:#0a2a5e;
    margin-top:25px;
">
    <b>#{hashtag} #SegundaBola</b>
</p>

<div style="
    border-top:1px solid #eeeeee;
    margin-top:25px;
    padding-top:12px;
">
    <p style="
        font-size:14px;
        color:#333;
    ">
        Artigo escrito por <b>{AUTOR}</b>
    </p>

    <p style="
        font-size:13px;
        color:#888;
    ">
        Publicado em {data_formatada} |
        Categoria: {categoria_html} |
        Segunda Bola
    </p>
</div>
"""

    return html_artigo


conteudo_html = criar_html()


# =====================================================
# PUBLICAR NO BLOGGER
# =====================================================

post = {

    "kind": "blogger#post",

    "blog": {
        "id": BLOG_ID
    },

    "title": titulo,

    "content": conteudo_html,

    "labels": [
        cat["nome"],
        "Segunda Bola",
        "Futebol",
        "Notícias Desportivas"
    ]
}


try:

    resultado = service.posts().insert(
        blogId=BLOG_ID,
        body=post
    ).execute()

    print("\n====================================")
    print("PUBLICAÇÃO CONCLUÍDA COM SUCESSO")
    print("====================================")

    print("Título:", titulo)
    print("Categoria:", cat["nome"])
    print("Palavras:", palavras)
    print("Imagem:", imagem["url"])
    print("Autor:", AUTOR)
    print("Link:", resultado.get("url"))

except Exception as e:

    print("ERRO AO PUBLICAR NO BLOGGER:")
    print(e)

    raise
