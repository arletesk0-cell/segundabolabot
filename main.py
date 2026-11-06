import os, requests
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = genai.Client(api_key=os.environ["GEMINI_KEY"], http_options=types.HttpOptions(api_version="v1beta"))

prompt = """Escreve um artigo de noticias de futebol para o blog Segunda Bola, em portugues formal e NEUTRO, como um jornalista profissional da BBC ou do Record.

REGRAS DE NEUTRALIDADE - OBRIGATORIO:
1. NUNCA uses: Viva malta, nosso craque, nosso Geny, maningue, Forca Geny, estamos contigo, orgulho nacional, magia, mamba, foguetao, partir tudo, espalhar magia.
2. NUNCA uses primeira pessoa: eu, nos, nosso, nossa, estamos, vamos.
3. SEMPRE usa terceira pessoa e tratamento formal: O jogador mocambicano Geny Catamo, O extremo do Sporting, O internacional mocambicano.
4. Tom serio, informativo, sem torcida, sem emocao, sem elogios exagerados. Apenas factos, analise e contexto.
5. Exemplo bom: 'O jogador mocambicano Geny Catamo foi titular na vitoria do Sporting e contribuiu com uma assistencia.'
6. Primeira linha APENAS o titulo, neutro e informativo, sem #, sem asteriscos.
7. Segunda linha APENAS: TEMA: Geny Catamo ou TEMA: Sporting ou TEMA: Mocambique ou TEMA: Liga Portugal
8. Depois so paragrafos corridos, SEM subtitulos, SEM listas, SEM asteriscos, SEM #.
9. Nao inventes resultados ou golos se nao tiveres a certeza. Fala de forma geral, desempenho, papel tatico e contexto.

Tema: Uma noticia atual sobre Geny Catamo, futebol mocambicano ou futebol mundial."""

resposta = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
texto = resposta.text.replace("**", "").replace("---", "").strip()
# Tirar # do texto mas guardar hashtags para o fim
texto = texto.replace("#", "")
linhas = [l.strip() for l in texto.split("\n") if l.strip()]
titulo = linhas[0]
tema = "Sporting"
corpo = []
for l in linhas[1:]:
    if l.upper().startswith("TEMA:"):
        tema = l.replace("TEMA:", "").replace("Tema:", "").strip()
    else:
        corpo.append(l)

# Limpar qualquer resto de linguagem de adepto que escape
banidas = ["Viva malta", "nosso craque", "nosso Geny", "Forca Geny", "estamos contigo", "maningue", "partir tudo", "espalhar magia", "orgulho nacional"]
for b in banidas:
    corpo = [p.replace(b, "o jogador") for p in corpo]
    titulo = titulo.replace(b, "Geny Catamo")

# FOTO - banco relacionado
banco_fotos = {
    "Geny Catamo": ["https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Est%C3%A1dio_Jos%C3%A9_Alvalade_2023.jpg/1200px-Est%C3%A1dio_Jos%C3%A9_Alvalade_2023.jpg"],
    "Sporting": ["https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Est%C3%A1dio_Jos%C3%A9_Alvalade_2023.jpg/1200px-Est%C3%A1dio_Jos%C3%A9_Alvalade_2023.jpg"],
    "Mocambique": ["https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Flag_of_Mozambique.svg/1200px-Flag_of_Mozambique.svg.png"],
    "Liga Portugal": ["https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Est%C3%A1dio_Jos%C3%A9_Alvalade_2023.jpg/1200px-Est%C3%A1dio_Jos%C3%A9_Alvalade_2023.jpg"]
}
foto_url = banco_fotos.get(tema, banco_fotos["Sporting"])[0]
try:
    busca = f"{tema} Sporting" if "Geny" in tema else tema
    r = requests.get(f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={busca}&gsrnamespace=6&gsrlimit=1&prop=imageinfo&iiprop=url&origin=*", timeout=15)
    paginas = r.json().get("query", {}).get("pages", {})
    for p in paginas.values():
        if "imageinfo" in p:
            foto_url = p["imageinfo"][0]["url"]
            break
except Exception as e:
    print("Wikimedia falhou:", e)

html = f'<img src="{foto_url}" style="width:100%; border-radius:10px; margin-bottom:15px;" /><p style="font-size:13px; color:#888;">Foto: {tema} / Segunda Bola</p>'
for linha in corpo:
    html += f'<p style="font-size:17px; line-height:1.7;">{linha}</p>'
html += '<p style="font-size:14px; color:#0a2a5e;"><b>#GenyCatamo #SportingCP #FutebolMocambicano</b></p>'

creds = Credentials(token=None, refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["BLOGGER_CLIENT_ID"], client_secret=os.environ["BLOGGER_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/blogger"])
service = build("blogger", "v3", credentials=creds)
post = {"kind": "blogger#post", "blog": {"id": os.environ["BLOG_ID"]}, "title": titulo, "content": html}
res = service.posts().insert(blogId=os.environ["BLOG_ID"], body=post).execute()
print("Publicado:", res.get("url"))
