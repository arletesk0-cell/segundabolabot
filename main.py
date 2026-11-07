
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
            f"Configuração em falta: {variavel}. "
            "Verifica os Secrets do GitHub."
        )

MINIMO_PALAVRAS = 450
MAX_TENTATIVAS_ARTIGO = 3

random.seed(datetime.datetime.now().timestamp())


# ==================================================
# CATEGORIAS
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
# INICIAR GEMINI
# ==================================================

client = genai.Client(
    api_key=os.environ["GEMINI_KEY"],
    http_options=types.HttpOptions(api_version="v1beta")
)

print("Gemini iniciado com sucesso!")


# ==================================================
# BUSCAR NOTÍCIAS NO GOOGLE NEWS
# ==================================================

def buscar_noticia_recente(query):

    url = (
        "https://news.google.com/rss/search?"
        f"q={requests.utils.quote(query)}%20when:2d"
        "&hl=pt-PT&gl=PT&ceid=PT:pt"
    )

    try:

        resposta = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        resposta.raise_for_status()

        root = ET.fromstring(resposta.content)

        agora = datetime.datetime.now(datetime.timezone.utc)

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

            if data_pub >= limite:

                candidatas.append({
                    "titulo": titulo,
                    "desc": descricao,
                    "link": link,
                    "data": data_pub
                })

        print(
            f"Encontradas {len(candidatas)} notícias "
            f"para {query}"
        )

        if candidatas:

            candidatas.sort(
                key=lambda noticia: noticia["data"],
                reverse=True
            )

            return random.choice(candidatas[:5])

    except Exception as erro:

        print("Erro Google News:", erro)

    return None


# ==================================================
# ESCOLHER CATEGORIA E NOTÍCIA
# ==================================================

categorias_disponiveis = CATEGORIAS.copy()

random.shuffle(categorias_disponiveis)

noticia = None
cat = None

for categoria in categorias_disponiveis:

    print(f"A pesquisar: {categoria['nome']}")

    resultado = buscar_noticia_recente(
        categoria["query"]
    )

    if resultado:

        cat = categoria
        noticia = resultado
        break


if not noticia:

    raise SystemExit(
        "Não foi encontrada nenhuma notícia recente."
    )


print("CATEGORIA:", cat["nome"])
print("NOTÍCIA:", noticia["titulo"])
print("DATA:", noticia["data"])


# ==================================================
# GERAR ARTIGO COM GEMINI
# ==================================================

titulo = ""
corpo = []
palavras = 0

for tentativa in range(MAX_TENTATIVAS_ARTIGO):

    prompt = f"""
Escreve um artigo jornalístico para o blog Segunda Bola.

IDIOMA:
Português formal, claro e neutro.

EXTENSÃO:
- Mínimo de 450 palavras.
- Entre 6 e 8 parágrafos desenvolvidos.
- Não escrevas um artigo superficial.

REGRAS EDITORIAIS:

1. Usa exclusivamente os factos fornecidos na notícia.
2. Não inventes resultados, golos, declarações ou estatísticas.
3. Não inventes classificações ou próximos jogos.
4. Não atribuas declarações a treinadores ou jogadores sem confirmação.
5. Podes acrescentar contexto histórico geral, desde que seja seguro.
6. Não menciones Google News, fontes ou links.
7. Não escrevas "Fonte:".
8. Não uses primeira pessoa.
9. Mantém um tom jornalístico sério.
10. Não uses expressões como "Viva malta", "maningue",
    "nosso craque", "foguetão" ou "magia".

FORMATO:

- Primeira linha: apenas um título novo e neutro.
- Depois: 6 a 8 parágrafos corridos.
- Sem subtítulos.
- Sem listas.
- Sem hashtags.
- Sem asteriscos.
- Sem comentários sobre o processo de escrita.

ESTRUTURA SUGERIDA:

1. Apresentação da notícia.
2. Detalhes confirmados do acontecimento.
3. Contexto da equipa ou competição.
4. Importância do acontecimento.
5. Consequências desportivas confirmadas.
6. Perspetivas futuras sem especulação apresentada como facto.
7. Conclusão jornalística.

NOTÍCIA REAL:

Título: {noticia['titulo']}

Descrição: {noticia['desc']}

Data: {noticia['data']}

Categoria: {cat['nome']}

Esta é a tentativa {tentativa + 1}.
Se a resposta anterior foi curta, desenvolve melhor os factos.

"""

    try:

        resposta = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        texto = (resposta.text or "").strip()

        if not texto:

            print("Gemini devolveu resposta vazia.")
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

            print("ARTIGO APROVADO!")
            break

    except Exception as erro:

        print("Erro ao gerar artigo:", erro)


if palavras < MINIMO_PALAVRAS:

    raise RuntimeError(
        f"Artigo rejeitado: {palavras} palavras. "
        "Não será publicado."
    )


# ==================================================
# DATA E AUTOR
# ==================================================

meses = [
    "janeiro", "fevereiro", "março",
    "abril", "maio", "junho",
    "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro"
]

fuso_maputo = datetime.timezone(
    datetime.timedelta(hours=2)
)

agora_maputo = datetime.datetime.now(fuso_maputo)

data_formatada = (
    f"{agora_maputo.day} de "
    f"{meses[agora_maputo.month - 1]} de "
    f"{agora_maputo.year}"
)

data_curta = agora_maputo.strftime("%d/%m/%Y")

print("DATA:", data_formatada)
print("AUTOR: Armando Massoca")
print("PALAVRAS:", palavras)


# ==================================================
# BUSCAR IMAGEM NO PIXABAY
# ==================================================

def buscar_pixabay(pesquisa):

    chave = os.environ.get("PIXABAY_API_KEY", "")

    if not chave:
        print("Pixabay sem chave. Usando imagem alternativa.")
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

        imagens = resposta.json().get("hits", [])

        if imagens:

            return random.choice(imagens)["largeImageURL"]

    except Exception as erro:

        print("Erro Pixabay:", erro)

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
# CONSTRUIR HTML DO ARTIGO
# ==================================================

titulo_html = html.escape(titulo)
categoria_html = html.escape(cat["nome"])
foto_html = html.escape(foto_url, quote=True)

conteudo_html = f"""
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

    paragrafo_seguro = html.escape(paragrafo)

    conteudo_html += f"""
<p style="font-size:17px;line-height:1.7;
margin-bottom:18px;">
{paragrafo_seguro}
</p>
"""


hashtag = cat["nome"].replace(" ", "")

conteudo_html += f"""
<p style="font-size:14px;color:#0a2a5e;">
<b>#{hashtag} #SegundaBola</b>
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
# PUBLICAR NOTÍCIA
# ==================================================

post = {
    "kind": "blogger#post",
    "blog": {
        "id": os.environ["BLOG_ID"]
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
        blogId=os.environ["BLOG_ID"],
        body=post
    ).execute()

    print("=" * 50)
    print("PUBLICAÇÃO REALIZADA COM SUCESSO!")
    print("CATEGORIA:", cat["label"])
    print("TÍTULO:", titulo)
    print("PALAVRAS:", palavras)
    print("URL:", resultado.get("url"))
    print("=" * 50)

except Exception as erro:

    print("ERRO AO PUBLICAR NO BLOGGER:", erro)
    raise
