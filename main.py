import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from googleapiclient.discovery import build
from cryptography.fernet import Fernet
from datetime import datetime, timezone, timedelta
import json
import os
import difflib

app = FastAPI(title="Statsfy Ultimate Production")

# 🔐 CHAVES DE PRODUÇÃO (Substitua por sua chave real para testes locais no Pydroid)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "MINHA_CHAVE_AQUI")
ENCRYPTION_KEY = os.getenv("STATSFY_CRYPTO_KEY", "")

if not ENCRYPTION_KEY:
    CHAVE_ARQUIVO = "secret.key"
    if os.path.exists(CHAVE_ARQUIVO):
        with open(CHAVE_ARQUIVO, "rb") as k_file:
            ENCRYPTION_KEY = k_file.read()
    else:
        ENCRYPTION_KEY = Fernet.generate_key()
        with open(CHAVE_ARQUIVO, "wb") as k_file:
            k_file.write(ENCRYPTION_KEY)

fernet = Fernet(ENCRYPTION_KEY)
DB_CRIPTOGRAFADO = "top_canais.enc"

def carregar_e_descriptografar_db():
    dados_padrao = {
        "ultima_atualizacao_ranking": datetime.now(timezone.utc).isoformat(),
        "brasil": [
            {"name": "Bispo Bruno Leonardo", "handle": "@bispobrunoleonardo", "subs": "75.0M", "subs_num": 75000000},
            {"name": "KondZilla", "handle": "@kondzilla", "subs": "68.1M", "subs_num": 68100000},
            {"name": "Luccas Neto", "handle": "@luccasnetoluccastoon", "subs": "53.5M", "subs_num": 53500000},
            {"name": "Maria Clara & JP", "handle": "@mariaclaraejp", "subs": "49.9M", "subs_num": 49900000},
            {"name": "Felipe Neto", "handle": "@felipeneto", "subs": "47.9M", "subs_num": 47900000},
            {"name": "Você Sabia?", "handle": "@vocesabia", "subs": "46.9M", "subs_num": 46900000},
            {"name": "Enaldinho", "handle": "@enaldinho", "subs": "44.9M", "subs_num": 44900000},
            {"name": "Whindersson Nunes", "handle": "@whindersson", "subs": "44.7M", "subs_num": 44700000},
            {"name": "GR6 EXPLODE", "handle": "@gr6explode", "subs": "42.8M", "subs_num": 42800000},
            {"name": "Galinha Pintadinha", "handle": "@galinhapintadinha", "subs": "38.3M", "subs_num": 38300000}
        ],
        "mundo": [
            {"name": "MrBeast", "handle": "@mrbeast", "subs": "500M", "subs_num": 500000000},
            {"name": "T-Series", "handle": "@tseries", "subs": "312M", "subs_num": 312000000},
            {"name": "Cocomelon", "handle": "@cocomelon", "subs": "201M", "subs_num": 201000000},
            {"name": "SET India", "handle": "@setindia", "subs": "189M", "subs_num": 189000000},
            {"name": "Vlad and Niki", "handle": "@vladandniki", "subs": "150M", "subs_num": 150000000},
            {"name": "Stokes Twins", "handle": "@stokestwins", "subs": "140M", "subs_num": 140000000},
            {"name": "Kids Diana Show", "handle": "@kidsdianashow", "subs": "138M", "subs_num": 138000000},
            {"name": "KIMPRO", "handle": "@kimpro_short", "subs": "133M", "subs_num": 133000000},
            {"name": "Like Nastya", "handle": "@likenastya", "subs": "132M", "subs_num": 132000000},
            {"name": "Zee Music Company", "handle": "@zeemusiccompany", "subs": "122M", "subs_num": 122000000}
        ],
        "historico_pesquisas": {}
    }

    if os.path.exists(DB_CRIPTOGRAFADO):
        try:
            with open(DB_CRIPTOGRAFADO, "rb") as f:
                conteudo_cripto = f.read()
            conteudo_json = fernet.decrypt(conteudo_cripto).decode("utf-8")
            db_carregado = json.loads(conteudo_json)
            return verificar_e_atualizar_rankings_semanais(db_carregado)
        except Exception:
            pass

    criptografar_e_salvar_db(dados_padrao)
    return dados_padrao

def criptografar_e_salvar_db(dados):
    conteudo_json = json.dumps(dados, indent=2, ensure_ascii=False).encode("utf-8")
    conteudo_cripto = fernet.encrypt(conteudo_json)
    with open(DB_CRIPTOGRAFADO, "wb") as f:
        f.write(conteudo_cripto)

def verificar_e_atualizar_rankings_semanais(db):
    try:
        data_atu_str = db.get("ultima_atualizacao_ranking")
        if not data_atu_str:
            return db
        data_atu = datetime.fromisoformat(data_atu_str)
        agora = datetime.now(timezone.utc)
        
        # 🗓️ Condição de 1 semana (7 dias) para atualização automática de dados
        if (agora - data_atu) > timedelta(days=7):
            youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            
            # Atualiza Brasil
            for canal in db["brasil"]:
                res = youtube.channels().list(part="statistics", forHandle=canal["handle"]).execute()
                if res.get("items"):
                    s = res["items"][0]["statistics"]
                    canal["subs_num"] = int(s.get("subscriberCount", canal["subs_num"]))
                    canal["subs"] = formatar_numero(canal["subs_num"])
            
            # Atualiza Mundo
            for canal in db["mundo"]:
                res = youtube.channels().list(part="statistics", forHandle=canal["handle"]).execute()
                if res.get("items"):
                    s = res["items"][0]["statistics"]
                    canal["subs_num"] = int(s.get("subscriberCount", canal["subs_num"]))
                    canal["subs"] = formatar_numero(canal["subs_num"])
            
            db["ultima_atualizacao_ranking"] = agora.isoformat()
            criptografar_e_salvar_db(db)
    except:
        pass # Protege o app de cair se a cota estourar durante o update semanal
    return db

def formatar_numero(valor):
    if not valor: return "N/A"
    num = int(valor)
    if num >= 1_000_000_000: return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000: return f"{num / 1_000_000:.1f}M"
    if num >= 1_000: return f"{num / 1_000:.1f}K"
    return str(num)

def formatar_data(data_iso):
    try:
        dt = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except:
        return "N/A"

def calcular_ganho_estimado(media_views_str, total_videos):
    try:
        if media_views_str == "N/A": return "N/A"
        fator = 1
        if "M" in media_views_str: fator = 1_000_000
        elif "K" in media_views_str: fator = 1_000
        
        views_limpas = float(media_views_str.replace("M", "").replace("K", "").strip()) * fator
        videos_por_mes = min(max(int(total_videos) / 24, 2), 12)
        views_mensais_estimadas = views_limpas * videos_por_mes
        
        ganho_min = (views_mensais_estimadas / 1000) * 0.25
        ganho_max = (views_mensais_estimadas / 1000) * 4.00
        return f"${formatar_numero(ganho_min)} - ${formatar_numero(ganho_max)}"
    except:
        return "N/A"

def encontrar_sugestao_proxima(handle_digitado, db):
    todos_handles = [c["handle"] for c in db.get("brasil", [])] + [c["handle"] for c in db.get("mundo", [])]
    procura = handle_digitado.replace("@", "")
    lista_limpa = [h.replace("@", "") for h in todos_handles]
    correspondencias = difflib.get_close_matches(procura, lista_limpa, n=1, cutoff=0.3)
    if correspondencias:
        return f"@{correspondencias[0]}"
    return None

def obter_posicao_ranking(handle, subs_atual, db):
    handle_limpo = handle.lower()
    for idx, c in enumerate(db.get("brasil", [])):
        if c.get("handle", "").lower() == handle_limpo:
            return f"#{idx + 1} Oficial no Brasil"
    for idx, c in enumerate(db.get("mundo", [])):
        if c.get("handle", "").lower() == handle_limpo:
            return f"#{idx + 1} Oficial no Mundo"
            
    br_list = sorted([c.get("subs_num", 0) for c in db.get("brasil", [])], reverse=True)
    wd_list = sorted([c.get("subs_num", 0) for c in db.get("mundo", [])], reverse=True)
    
    for idx, val in enumerate(br_list):
        if subs_atual >= val: return f"#{idx + 1} pos. comparada Brasil"
    for idx, val in enumerate(wd_list):
        if subs_atual >= val: return f"#{idx + 1} pos. comparada Global"
    return "Classificado fora do Top de Referência"

@app.get("/api/rankings")
async def obter_rankings():
    db = carregar_e_descriptografar_db()
    return {"brasil": db["brasil"], "mundo": db["mundo"]}

# 🔍 ENDPOINT DE AUTO-COMPLETAR COM TODOS OS CANAIS DO MUNDO (Direto da Search API)
@app.get("/api/sugerir")
async def sugerir_canais(q: str = Query(..., min_length=1)):
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "SUA_CHAVE_AQUI":
        return []
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        busca = youtube.search().list(
            q=q, part="snippet", type="channel", maxResults=5
        ).execute()
        
        sugestoes = []
        for item in busca.get("items", []):
            snippet = item["snippet"]
            sugestoes.append({
                "name": snippet["title"],
                "id_canal": item["id"]["channelId"]
            })
        return congestoes
    except:
        return []

@app.get("/api/analisar")
async def analisar_canal(handle: str = Query(..., min_length=1)):
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "SUA_CHAVE_AQUI":
        return JSONResponse(status_code=400, content={"error": "Erro de Produção: API Key oculta ou não configurada."})

    handle = handle.strip().lower()
    # Se o parâmetro for um ID direto vindo do clique do autocomplete global
    id_direto = None
    if handle.startswith("id:"):
        id_direto = handle.replace("id:", "")
    elif not handle.startswith("@"): 
        handle = f"@{handle}"
    
    db = carregar_e_descriptografar_db()
    agora = datetime.now(timezone.utc)

    # Cache de pesquisa para economizar requisições
    chave_cache = id_direto if id_direto else handle
    if chave_cache in db.get("historico_pesquisas", {}):
        cache = db["historico_pesquisas"][chave_cache]
        data_cache = datetime.fromisoformat(cache["timestamp"])
        if (agora - data_cache).days < 1:
            return cache["dados"]

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        if id_direto:
            busca_canal = youtube.channels().list(part="snippet,statistics,contentDetails,brandingSettings", id=id_direto).execute()
        else:
            busca_canal = youtube.channels().list(part="snippet,statistics,contentDetails,brandingSettings", forHandle=handle).execute()

        if not busca_canal.get("items"):
            sugestao = encontrar_sugestao_proxima(handle, db)
            if sugestao:
                return JSONResponse(status_code=404, content={"error": f'Canal "{handle}" não encontrado. Você quis dizer "{sugestao}"?'})
            return JSONResponse(status_code=404, content={"error": f'Canal "{handle}" não encontrado.'})

        canal = busca_canal["items"][0]
        snippet = canal["snippet"]
        stats = canal["statistics"]
        branding = canal.get("brandingSettings", {})
        playlist_envios = canal["contentDetails"]["relatedPlaylists"]["uploads"]
        canal_handle_real = snippet.get("customUrl", handle)

        foto_perfil = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
        banner_url = branding.get("image", {}).get("bannerExternalUrl", "")
        if banner_url: 
            banner_url += "=w1060-fcrop64=1,00005a57ffffa5a7-no-nd-v1"

        # Captura de uploads recentes
        busca_videos = youtube.playlistItems().list(
            part="snippet,contentDetails", playlistId=playlist_envios, maxResults=15
        ).execute()

        itens_videos = [v for v in busca_videos.get("items", []) if v["snippet"]["title"] not in ["Deleted video", "Private video"]]
        ultimo_video_titulo = "N/A"
        ultimo_video_data = "N/A"
        ultimo_video_views = "N/A"
        ultimo_video_likes = "N/A"
        media_views = "N/A"

        if itens_videos:
            ultimo_video_titulo = itens_videos[0]["snippet"]["title"]
            ultimo_video_data = formatar_data(itens_videos[0]["snippet"]["publishedAt"])
            ids_videos = [v["contentDetails"]["videoId"] for v in itens_videos[:10]]
            dados_videos = youtube.videos().list(part="statistics", id=",".join(ids_videos)).execute()
            
            video_items = dados_videos.get("items", [])
            if video_items:
                ultimo_video_views = formatar_numero(video_items[0]["statistics"].get("viewCount", 0))
                ultimo_video_likes = formatar_numero(video_items[0]["statistics"].get("likeCount", 0))

            views_lista = [int(v["statistics"].get("viewCount", 0)) for v in video_items]
            if views_lista:
                media_views = formatar_numero(sum(views_lista) / len(views_lista))

        # Rastreamento avançado do primeiro vídeo da história
        busca_primeiro_page = youtube.playlistItems().list(
            part="snippet", playlistId=playlist_envios, maxResults=1
        ).execute()
        
        primeiro_video_titulo = "N/A"
        primeiro_video_data = "N/A"
        if busca_primeiro_page.get("items"):
            total_resultados = busca_primeiro_page.get("pageInfo", {}).get("totalResults", 0)
            if total_resultados > 0:
                token_pagina = None
                passos_maximos = (total_resultados // 50)
                
                for _ in range(min(passos_maximos, 20)):
                    busca_token = youtube.playlistItems().list(
                        part="id", playlistId=playlist_envios, maxResults=50, pageToken=token_pagina
                    ).execute()
                    token_pagina = busca_token.get("nextPageToken")
                    if not token_pagina:
                        break
                
                busca_final = youtube.playlistItems().list(
                    part="snippet", playlistId=playlist_envios, maxResults=50, pageToken=token_pagina
                ).execute()
                
                itens_finais = [v for v in busca_final.get("items", []) if v["snippet"]["title"] not in ["Deleted video", "Private video"]]
                if itens_finais:
                    primeiro_video_titulo = itens_finais[-1]["snippet"]["title"]
                    primeiro_video_data = formatar_data(itens_finais[-1]["snippet"]["publishedAt"])

        data_criacao_iso = snippet["publishedAt"]
        data_obj = datetime.fromisoformat(data_criacao_iso.replace("Z", "+00:00"))
        idade_anos = agora.year - data_obj.year

        views_totais_num = int(stats.get("viewCount", 0))
        inscritos_num = int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") else 0
        total_videos = stats.get("videoCount", 0)
        
        anos_lista = [str(ano) for ano in range(data_obj.year, agora.year + 1)]
        total_passos = len(anos_lista)
        
        dados_grafico_views = []
        dados_grafico_subs = []
        for idx in range(total_passos):
            fator_crescimento = ((idx + 1) / total_passos) ** 2
            dados_grafico_views.append(int(views_totais_num * fator_crescimento))
            dados_grafico_subs.append(int(inscritos_num * fator_crescimento))

        posicao_rank = obter_posicao_ranking(canal_handle_real, inscritos_num, db)
        ganho_mensal = calcular_ganho_estimado(media_views, total_videos)

        resultado = {
            "nome": snippet["title"],
            "descricao": snippet.get("description", "Sem bio disponível."),
            "foto": foto_perfil,
            "banner": banner_url,
            "ranking": posicao_rank,
            "criacao": data_obj.strftime("%d/%m/%Y"),
            "idade": f"{idade_anos} anos" if idade_anos > 0 else "Menos de 1 ano",
            "views_totais": formatar_numero(views_totais_num),
            "inscritos": formatar_numero(inscritos_num),
            "total_videos": str(total_videos),
            "ultimo_video": ultimo_video_titulo,
            "ultimo_video_data": ultimo_video_data,
            "ultimo_video_views": ultimo_video_views,
            "ultimo_video_likes": ultimo_video_likes,
            "primeiro_video": primeiro_video_titulo,
            "primeiro_video_data": primeiro_video_data,
            "media_views_recente": media_views,
            "ganho_mensal_estimado": ganho_mensal,
            "grafico_anos": anos_lista,
            "grafico_views": dados_grafico_views,
            "grafico_subs": dados_grafico_subs
        }

        db["historico_pesquisas"][chave_cache] = {
            "timestamp": agora.isoformat(),
            "dados": resultado
        }
        criptografar_e_salvar_db(db)
        return resultado
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Erro crítico na API do YouTube ou Cota Esgotada."})

@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Statsfy Ultimate Pro</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root { --bg: #060608; --card: #111116; --border: #1d1d29; --accent: #ff004c; --text: #f1f1f6; --text-muted: #6c6c85; }
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Roboto, sans-serif; }
            body { background-color: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; padding: 1.5rem 1rem; min-height: 100vh; }
            .container { width: 100%; max-width: 650px; position: relative; }
            header { text-align: center; margin: 1.5rem 0 2.5rem 0; }
            header h1 { font-size: 2.8rem; font-weight: 800; letter-spacing: -1.5px; }
            header h1 span { color: var(--accent); text-shadow: 0 0 25px rgba(255, 0, 76, 0.4); }
            header p { color: var(--text-muted); font-size: 0.95rem; margin-top: 0.3rem; }
            .search-area { position: relative; margin-bottom: 2rem; }
            .search-box { display: flex; background: var(--card); padding: 0.5rem; border-radius: 16px; border: 1px solid var(--border); }
            .search-box input { flex: 1; background: transparent; border: none; outline: none; color: #fff; padding: 0.5rem 1rem; font-size: 1rem; }
            .search-box button { background: var(--accent); color: white; border: none; padding: 0.7rem 1.8rem; border-radius: 12px; cursor: pointer; font-weight: 700; }
            .autocomplete-box { position: absolute; top: 105%; left: 0; right: 0; background: var(--card); border: 1px solid var(--border); border-radius: 12px; max-height: 250px; overflow-y: auto; z-index: 999; display: none; box-shadow: 0 15px 30px rgba(0,0,0,0.6); }
            .autocomplete-item { padding: 0.85rem 1.2rem; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.01); font-size: 0.9rem; color: #d1d1d6; }
            .autocomplete-item:hover { background: rgba(255, 0, 76, 0.08); color: #fff; }
            .loading-placeholder { text-align: center; padding: 2rem; background: var(--card); border: 1px solid var(--border); border-radius: 24px; display: none; margin-bottom: 2rem; font-weight: bold; font-size: 1.1rem; animation: pulseLoading 1s infinite ease-in-out; }
            @keyframes pulseLoading { 0% { color: #444455; } 50% { color: #f1f1f6; } 100% { color: #444455; } }
            .dashboard { background: var(--card); border-radius: 24px; border: 1px solid var(--border); margin-bottom: 2rem; display: none; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
            .channel-banner { width: 100%; height: 120px; background: #15151f; background-size: cover; background-position: center; }
            .profile-area { display: flex; align-items: flex-end; padding: 0 1.5rem; margin-top: -50px; gap: 15px; margin-bottom: 1.5rem; }
            .profile-avatar { width: 90px; height: 90px; border-radius: 50%; border: 4px solid var(--card); background: #222; background-size: cover; background-position: center; }
            .profile-titles { padding-bottom: 5px; }
            .profile-titles h2 { font-size: 1.6rem; font-weight: 800; }
            .ranking-badge { display: inline-block; background: rgba(255, 0, 76, 0.12); color: var(--accent); padding: 0.2rem 0.7rem; border-radius: 30px; font-size: 0.8rem; font-weight: 700; margin-top: 4px; border: 1px solid rgba(255,0,76,0.15); }
            .bio-card { background: rgba(255,255,255,0.01); margin: 0 1.5rem 1.5rem 1.5rem; padding: 1rem; border-radius: 14px; border: 1px solid var(--border); }
            .bio-card label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; display: block; margin-bottom: 4px; }
            .bio-card p { font-size: 0.9rem; color: #c5c5cd; line-height: 1.4; }
            .dash-tabs { display: flex; gap: 6px; margin: 0 1.5rem 1.5rem 1.5rem; background: rgba(255,255,255,0.02); padding: 4px; border-radius: 12px; }
            .sub-tab-btn { flex: 1; background: transparent; color: var(--text-muted); border: none; padding: 0.6rem; border-radius: 9px; font-weight: 700; cursor: pointer; font-size: 0.85rem; }
            .sub-tab-btn.active { background: var(--border); color: #fff; }
            .dash-content { display: none; padding: 0 1.5rem 1.5rem 1.5rem; }
            .dash-content.active { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
            .metric-card { background: rgba(255,255,255,0.01); border: 1px solid var(--border); padding: 1rem; border-radius: 14px; }
            .metric-card label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; display: block; margin-bottom: 4px; }
            .metric-card span { font-size: 1.25rem; font-weight: 700; color: #fff; }
            .full-width { grid-column: span 2; }
            .chart-holder { background: rgba(255,255,255,0.01); border: 1px solid var(--border); border-radius: 16px; padding: 1rem; margin: 0 1.5rem 1.5rem 1.5rem; display: none; }
            .chart-container-box { display: flex; flex-direction: column; gap: 15px; }
            .ranking-box { background: var(--card); border-radius: 24px; padding: 1.5rem; border: 1px solid var(--border); }
            .main-tabs { display: flex; gap: 10px; margin-bottom: 1.2rem; }
            .main-tab-btn { flex: 1; background: #13131a; color: var(--text-muted); border: none; padding: 0.75rem; border-radius: 12px; font-weight: 700; cursor: pointer; }
            .main-tab-btn.active { background: var(--accent); color: white; }
            .list-container { display: none; flex-direction: column; gap: 8px; }
            .list-container.active { display: flex; }
            .channel-row { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.005); padding: 0.8rem 1rem; border-radius: 12px; border: 1px solid var(--border); cursor: pointer; }
            .channel-row:hover { border-color: var(--accent); background: rgba(255, 0, 76, 0.02); }
            .rank-index { font-weight: 800; color: var(--accent); width: 30px; }
            .channel-name { font-weight: 600; font-size: 0.95rem; }
            .channel-badge { font-size: 0.8rem; color: var(--text-muted); background: #13131a; padding: 0.3rem 0.7rem; border-radius: 30px; font-weight: 700; }
        </style>
    </head>
    <body>

    <div class="container">
        <header>
            <h1>Stats<span>fy</span></h1>
            <p>Métricas de Canais e Auto-completar Global</p>
        </header>

        <div class="search-area">
            <div class="search-box">
                <input type="text" id="channelInput" placeholder="Busque qualquer canal do mundo..." autocomplete="off">
                <button onclick="buscarCanal()">Analisar</button>
            </div>
            <div id="autocompleteList" class="autocomplete-box"></div>
        </div>

        <div id="loadingBox" class="loading-placeholder">Procurando...</div>

        <div id="dashBox" class="dashboard">
            <div id="dBanner" class="channel-banner"></div>
            <div class="profile-area">
                <div id="dFoto" class="profile-avatar"></div>
                <div class="profile-titles">
                    <h2 id="dNome">Nome</h2>
                    <span id="dRanking" class="ranking-badge">Análise</span>
                </div>
            </div>

            <div class="bio-card">
                <label>Bio / Descrição</label>
                <p id="dDesc">Carregando dados...</p>
            </div>
            
            <div class="dash-tabs">
                <button class="sub-tab-btn active" onclick="switchSubTab(event, 'tabGeral')">📊 Geral</button>
                <button class="sub-tab-btn" onclick="switchSubTab(event, 'tabVideos')">🎬 Linha do Tempo & Lucro</button>
            </div>

            <div id="tabGeral" class="dash-content active">
                <div class="metric-card"><label>Inscritos</label><span id="mSubs">0</span></div>
                <div class="metric-card"><label>Views Totais</label><span id="mViews">0</span></div>
                <div class="metric-card"><label>Total de Vídeos</label><span id="mVideos">0</span></div>
                <div class="metric-card"><label>Conta Criada Em</label><span id="mCriacao">0</span></div>
                <div class="metric-card full-width"><label>Tempo de Plataforma</label><span id="mIdade">0</span></div>
            </div>

            <div id="tabVideos" class="dash-content">
                <div class="metric-card full-width" style="background: rgba(0, 255, 136, 0.02); border-color: rgba(0, 255, 136, 0.1);"><label style="color:#00ff88; font-weight: bold;">Ganho Mensal Estimado (AdSense)</label><span id="mGanho" style="color:#00ff88; font-size:1.4rem;">$0.00</span></div>
                <div class="metric-card full-width"><label>Média Views (Últimos Envios)</label><span id="mMediaViews">0</span></div>
                
                <div class="metric-card full-width">
                    <label style="color: var(--accent);">Último Lançamento</label>
                    <span id="mUltimo" style="font-size: 0.95rem; display: block; color: #fff; font-weight:bold;">Título</span>
                    <div style="display: flex; gap: 15px; font-size: 0.8rem; color: var(--text-muted); margin-top:4px;">
                        <div>📅 Data: <strong id="mUltimoData" style="color:#fff;">0</strong></div>
                        <div>👁️ <strong id="mUltimoViews" style="color:#fff;">0</strong> Views</div>
                        <div>👍 <strong id="mUltimoLikes" style="color:#fff;">0</strong> Likes</div>
                    </div>
                </div>
                
                <div class="metric-card full-width">
                    <label style="color: #ffaa00;">Primeiro Vídeo Histórico (Origem)</label>
                    <span id="mPrimeiro" style="font-size: 0.95rem; display: block; color: #fff; font-weight:bold;">Título</span>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top:4px;">
                        📅 Publicado em: <strong id="mPrimeiroData" style="color:#fff;">0</strong>
                    </div>
                </div>
            </div>

            <div id="graphHolder" class="chart-holder">
                <div class="chart-container-box">
                    <div><canvas id="subsChart"></canvas></div>
                    <hr style="border: 0; border-top: 1px solid var(--border); margin: 5px 0;">
                    <div><canvas id="viewsChart"></canvas></div>
                </div>
            </div>
        </div>

        <div class="ranking-box">
            <div class="main-tabs">
                <button class="main-tab-btn active" onclick="switchMainTab(event, 'br')">🇧🇷 Top Brasil</button>
                <button class="main-tab-btn" onclick="switchMainTab(event, 'wd')">🌐 Top Mundo</button>
            </div>
            <div id="br" class="list-container active"></div>
            <div id="wd" class="list-container"></div>
        </div>
    </div>

    <script>
        let graficoSubs = null;
        let graficoViews = null;
        let loadingInterval = null;
        let debounceTimer = null;

        function renderRankings(data, targetId) {
            const el = document.getElementById(targetId);
            el.innerHTML = "";
            data.forEach((item, i) => {
                el.innerHTML += `
                    <div class="channel-row" onclick="pesquisarTop('${item.handle}')">
                        <div style="display:flex; align-items:center;">
                            <span class="rank-index">${i+1}º</span>
                            <span class="channel-name">${item.name}</span>
                        </div>
                        <span class="channel-badge">${item.subs}</span>
                    </div>
                `;
            });
        }

        function startLoadingAnimation() {
            const phrases = ["Conectando à API Global...", "Filtrando Linha do Tempo...", "Rastreando Primeiro Vídeo...", "Calculando Lucros..."];
            let idx = 0;
            const el = document.getElementById("loadingBox");
            el.innerText = phrases[0];
            el.style.display = "block";
            loadingInterval = setInterval(() => {
                idx = (idx + 1) % phrases.length;
                el.innerText = phrases[idx];
            }, 1000);
        }

        function stopLoadingAnimation() {
            clearInterval(loadingInterval);
            document.getElementById("loadingBox").style.display = "none";
        }

        // ⚡ AUTO-COMPLETAR GLOBAL REAL-TIME (Busca automática de qualquer canal do mundo)
        document.getElementById("channelInput").addEventListener("input", function(e) {
            clearTimeout(debounceTimer);
            const val = e.target.value.trim();
            const box = document.getElementById("autocompleteList");
            
            if(!val || val.length < 2) { box.style.display = "none"; return; }
            
            debounceTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/sugerir?q=${encodeURIComponent(val)}`);
                    const dados = await res.json();
                    
                    if(dados.length > 0) {
                        box.innerHTML = "";
                        dados.forEach(item => {
                            box.innerHTML += `<div class="autocomplete-item" onclick="selecionarSugestao('id:${item.id_canal}')">🌐 <strong>${item.name}</strong></div>`;
                        });
                        box.style.display = "block";
                    } else {
                        box.style.display = "none";
                    }
                } catch(e) { console.error(e); }
            }, 400); // 400ms protege sua cota de requisições excessivas
        });

        function selecionarSugestao(identificador) {
            document.getElementById("autocompleteList").style.display = "none";
            buscarCanal(identificador);
        }

        function switchMainTab(e, id) {
            document.querySelectorAll('.main-tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.list-container').forEach(l => l.classList.remove('active'));
            e.currentTarget.classList.add('active');
            document.getElementById(id).classList.add('active');
        }

        function switchSubTab(e, id) {
            document.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.dash-content').forEach(c => c.classList.remove('active'));
            e.currentTarget.classList.add('active');
            document.getElementById(id).classList.add('active');
        }

        async function buscarCanal(termo = null) {
            document.getElementById("autocompleteList").style.display = "none";
            let query = termo || document.getElementById('channelInput').value.trim();
            if(!query) return alert("Digite o canal.");

            document.getElementById('dashBox').style.display = "none";
            document.getElementById('graphHolder').style.display = "none";
            startLoadingAnimation();

            try {
                const res = await fetch(`/api/analisar?handle=${encodeURIComponent(query)}`);
                const d = await res.json();
                stopLoadingAnimation();

                if(!res.ok) return alert(d.error || "Erro.");

                document.getElementById('dNome').innerText = d.nome;
                document.getElementById('dDesc').innerText = d.descricao;
                document.getElementById('dFoto').style.backgroundImage = `url('${d.foto}')`;
                
                if(d.banner) {
                    document.getElementById('dBanner').style.backgroundImage = `url('${d.banner}')`;
                    document.getElementById('dBanner').style.display = 'block';
                } else {
                    document.getElementById('dBanner').style.display = 'none';
                }

                document.getElementById('dRanking').innerText = d.ranking;
                document.getElementById('mSubs').innerText = d.inscritos;
                document.getElementById('mViews').innerText = d.views_totais;
                document.getElementById('mVideos').innerText = d.total_videos;
                document.getElementById('mCriacao').innerText = d.criacao;
                document.getElementById('mIdade').innerText = d.idade;
                document.getElementById('mMediaViews').innerText = d.media_views_recente;
                document.getElementById('mGanho').innerText = d.ganho_mensal_estimado;
                
                document.getElementById('mUltimo').innerText = d.ultimo_video;
                document.getElementById('mUltimoData').innerText = d.ultimo_video_data;
                document.getElementById('mUltimoViews').innerText = d.ultimo_video_views;
                document.getElementById('mUltimoLikes').innerText = d.ultimo_video_likes;
                
                document.getElementById('mPrimeiro').innerText = d.primeiro_video;
                document.getElementById('mPrimeiroData').innerText = d.primeiro_video_data;

                document.getElementById('dashBox').style.display = "block";
                document.getElementById('graphHolder').style.display = "block";

                const ctxSubs = document.getElementById('subsChart').getContext('2d');
                if(graficoSubs) graficoSubs.destroy();
                graficoSubs = new Chart(ctxSubs, {
                    type: 'line',
                    data: {
                        labels: d.grafico_anos,
                        datasets: [{ label: 'Inscritos', data: d.grafico_subs, borderColor: '#00ff88', borderWidth: 2, fill: false }]
                    }
                });

                const ctxViews = document.getElementById('viewsChart').getContext('2d');
                if(graficoViews) graficoViews.destroy();
                graficoViews = new Chart(ctxViews, {
                    type: 'line',
                    data: {
                        labels: d.grafico_anos,
                        datasets: [{ label: 'Views', data: d.grafico_views, borderColor: '#ff004c', borderWidth: 2, fill: false }]
                    }
                });

            } catch(err) {
                stopLoadingAnimation();
                alert("Erro ao processar dados de produção.");
            }
        }

        function pesquisarTop(handle) {
            buscarCanal(handle);
        }

        async function inicializarRankings() {
            try {
                const res = await fetch('/api/rankings');
                const data = await res.json();
                renderRankings(data.brasil, 'br');
                renderRankings(data.mundo, 'wd');
            } catch(err) {
                console.error("Erro.");
            }
        }

        window.onload = inicializarRankings;
    </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
