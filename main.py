import os
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 1. Configurar Gemini novo
client = genai.Client(api_key=os.environ["GEMINI_KEY"])

prompt = """Escreve um artigo de noticias de futebol para o blog Segunda Bola, em portugues de Mocambique, com linguagem simples e animada.
Tema: Uma noticia atual e interessante do futebol mundial ou mocambicano, com titulo chamativo, introducao, 3 subtitulos e conclusao.
No fim, escreve 3 hashtags. Nao inventes resultados falsos se nao tiveres a certeza, usa temas gerais e analise."""

resposta = client.models.generate_content(model="gemini-3.0-flash", contents=prompt)
texto = resposta.text

# Separar titulo da primeira linha
linhas = texto.strip().split("\n")
titulo = linhas[0].replace("#", "").strip()
corpo = "\n".join(linhas[1:])

# 2. Configurar Blogger
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
