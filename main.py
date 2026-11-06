import os, requests
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

prompt = "Escreve um artigo de noticias de futebol para o blog Segunda Bola, em portugues de Mocambique, simples e animado. REGRAS OBRIGATORIAS: 1. A primeira linha tem que ser APENAS o titulo, sem #, sem asteriscos. 2. A segunda linha tem que ser APENAS: FOTO: nome para pesquisar a foto, por exemplo FOTO: Geny Catamo Sporting ou FOTO: Moçambique selecao futebol. 3. Depois escreve so paragrafos corridos, SEM subtitulos, SEM titulos no meio, SEM listas, SEM asteriscos, SEM #. No fim, 3 hashtags. Tema: Uma noticia atual sobre Geny Catamo, futebol mocambicano ou futebol mundial."

resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
texto = resposta.text.replace("**", "").replace("#", "").replace("---", "").strip()

linhas = [l.strip() for l in texto.split("\n") if l.strip()]
titulo = linhas[0]
pesquisa_foto = "futebol"
corpo_linhas = []

for l in linhas[1:]:
    if l.upper().startswith("FOTO:"):
        pesquisa_foto = l.replace("FOTO:", "").replace("Foto:", "").strip()
    else:
        corpo_linhas.append(l)

# BUSCAR FOTO RELACIONADA COM A MATERIA
foto_url = "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=1200"
try:
    r = requests.get(f"https://api.openverse.org/v1/images/?q={pesquisa_foto}&page_size=1&license_type=all", timeout=15)
    dados = r.json()
    if dados.get("results"):
        foto_url = dados["results"][0]["url"]
        print(f"Foto encontrada para: {pesquisa_foto} -> {foto_url}")
except Exception as e:
    print("Falhou buscar foto, usar foto generica:", e)

# HTML SEM SUBTITULOS - so paragrafos
html = f'<img src="{foto_url}" style="width:100%; border-radius:10px; margin-bottom:15px;" /><br><br>'
for linha in corpo_linhas:
    html += f'<p style="font-size:17px; line-height:1.7;">{linha}</p>'

creds = Credentials(
    token=None,
    refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["BLOGGER_CLIENT_ID"],
    client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
    scopes=["https://www.googleapis.com/auth/blogger"]
)
service = build("blogger", "v3", credentials=creds)
post = {"kind": "blogger#post", "blog": {"id": os.environ["BLOG_ID"]}, "title": titulo, "content": html}
resultado = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado:", resultado.get("url"))
