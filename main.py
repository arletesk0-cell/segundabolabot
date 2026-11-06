import os
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
corpo = "\n".join(linhas[1:])

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
    "content": corpo.replace("\n", "<br>")
}

resultado = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado com sucesso:", resultado.get("url"))
