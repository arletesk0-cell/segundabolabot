import os, random
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

prompt = "Escreve um artigo de noticias de futebol para o blog Segunda Bola, em portugues de Mocambique, simples e animado. REGRAS: A primeira linha tem que ser APENAS o titulo do artigo, sem a palavra Titulo, sem #, sem asteriscos, sem aspas. Depois escreve o artigo normal, sem usar asteriscos, sem usar #, sem usar tracos. Usa paragrafos curtos. Para subtitulos, escreve apenas o texto do subtitulo em MAIUSCULAS numa linha sozinha. No fim, 3 hashtags numa linha. Tema: Uma noticia atual e interessante sobre Geny Catamo, futebol mocambicano ou futebol mundial."

resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
texto = resposta.text

texto = texto.replace("**", "").replace("###", "").replace("##", "").replace("#", "").replace("---", "").strip()

linhas = texto.strip().split("\n")
titulo = linhas[0].strip()
corpo_linhas = linhas[1:]

# FOTOS DE FUTEBOL - escolhe uma diferente a cada post
fotos = [
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=1200",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=1200",
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=1200",
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=1200",
    "https://images.unsplash.com/photo-1560272564-c83b66b1ad12?w=1200",
]
foto = random.choice(fotos)

# CONVERTER TEXTO EM HTML COM DESTAQUE
html = f'<img src="{foto}" style="width:100%; border-radius:10px; margin-bottom:15px;" /><br><br>'
for linha in corpo_linhas:
    linha = linha.strip()
    if not linha:
        continue
    # Se a linha esta toda em MAIUSCULAS e e curta, e um SUBTITULO
    if linha.isupper() and len(linha) < 80 and len(linha) > 5:
        html += f'<h2 style="color:#0a2a5e; font-size:22px; margin-top:25px;">{linha}</h2>'
    elif linha.startswith("#"):
        continue
    else:
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

post = {
    "kind": "blogger#post",
    "blog": {"id": os.environ["BLOG_ID"]},
    "title": titulo,
    "content": html
}

resultado = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado com sucesso:", resultado.get("url"))
