from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Optional

app = FastAPI(
    title="AgroCredit Engine", 
    description="Motor de Análise de Crédito e Risco Socioambiental (Goiás)", 
    version="3.4 Production"
)

# --- 0. CONFIGURAÇÃO DE SEGURANÇA (CORS) ---
# Permite que seu Dashboard acesse a API sem bloqueios
origins = [
    "http://localhost",
    "http://localhost:8501",
    "https://agromvp.onrender.com",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. CONFIGURAÇÃO DO BANCO DE DADOS (NEON) ---
DB_USER = "neondb_owner"
DB_PASS = "npg_ZL2qeh4yHGSm"
DB_HOST = "ep-curly-boat-ac2r3idj-pooler.sa-east-1.aws.neon.tech"
DB_NAME = "neondb"

# Conexão segura SSL
db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?sslmode=require"

try:
    engine = create_engine(db_url, client_encoding='utf8', pool_pre_ping=True)
except Exception as e:
    print(f"Erro ao configurar banco: {e}")

# --- 2. PARÂMETROS DE MERCADO ---
PRECO_SACA = 115.00
PRODUTIVIDADE_HA = 60
CUSTO_PRODUCAO_HA = 4500.00

# --- 3. FUNÇÕES AUXILIARES ---
def corrigir_acentos(df):
    cols_texto = ['municipio', 'infrator', 'motivo', 'car_codigo']
    for col in cols_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).apply(
                lambda x: x.encode('utf-8', 'ignore').decode('utf-8') if x != 'None' else None
            )
    return df

@app.get("/")
def home():
    return {"mensagem": "AgroCredit Engine Online! Rodando na Nuvem ☁️"}

# --- ROTA 4: RISCOS (PONTOS VERMELHOS) ---
@app.get("/analise/risco-imediato")
def verificar_todos_riscos():
    sql_query = """
    SELECT 
        f.cod_imovel as car_codigo,
        f.municipio,
        ST_Y(ST_Centroid(f.geometry::geometry)) as lat,
        ST_X(ST_Centroid(f.geometry::geometry)) as lon,
        e.nome_embar as infrator,
        e.des_infrac as motivo,
        (ST_Area(ST_Intersection(f.geometry, e.geometry)::geography) / 10000)::numeric(10,2) as area_contaminada_ha
    FROM fazendas_goias f
    JOIN embargos_ibama e ON ST_Intersects(f.geometry, e.geometry)
    ORDER BY area_contaminada_ha DESC
    LIMIT 500;
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql_query), conn)
        if df.empty: return {"status": "Nenhum risco", "ocorrencias": []}
        return {"status": "ALERTA", "total_encontrado": len(df), "ocorrencias": corrigir_acentos(df).to_dict(orient="records")}
    except Exception as e: return {"erro_interno": str(e)}

# --- ROTA 5: OPORTUNIDADES (PONTOS VERDES - NOVA) ---
@app.get("/analise/oportunidades")
def listar_oportunidades():
    """Retorna fazendas SEM embargos (Pontos Verdes)"""
    sql_query = """
    SELECT 
        f.cod_imovel as car_codigo,
        f.municipio,
        ST_Y(ST_Centroid(f.geometry::geometry)) as lat,
        ST_X(ST_Centroid(f.geometry::geometry)) as lon,
        (ST_Area(f.geometry::geography) / 10000)::numeric(10,2) as area_ha
    FROM fazendas_goias f
    LEFT JOIN embargos_ibama e ON ST_Intersects(f.geometry, e.geometry)
    WHERE e.geometry IS NULL
    LIMIT 500;
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql_query), conn)
        if df.empty: return {"status": "Nenhuma oportunidade", "dados": []}
        return {"status": "Oportunidades", "total": len(df), "dados": corrigir_acentos(df).to_dict(orient="records")}
    except Exception as e: return {"erro_interno": str(e)}

# --- ROTA 6: CONSULTA SIMPLES ---
@app.get("/consultar")
def consultar_por_car(codigo_car: Optional[str] = None):
    if not codigo_car: return {"erro": "Forneça um código."}
    sql_query = text("""
    SELECT f.cod_imovel as car_codigo, f.municipio, e.nome_embar as infrator, e.des_infrac as motivo,
    (ST_Area(ST_Intersection(f.geometry, e.geometry)::geography) / 10000)::numeric(10,2) as area_contaminada_ha
    FROM fazendas_goias f JOIN embargos_ibama e ON ST_Intersects(f.geometry, e.geometry)
    WHERE f.cod_imovel ILIKE :filtro
    """)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"filtro": f"%{codigo_car}%"})
        if df.empty: return {"status": "NADA CONSTA", "mensagem": "Fazenda Limpa."}
        return {"status": "ALERTA VERMELHO", "detalhes": corrigir_acentos(df).to_dict(orient="records")}
    except Exception as e: return {"erro": str(e)}

# --- ROTA 7: ANÁLISE DE CRÉDITO COMPLETA ---
@app.get("/consultar_credito")
def consultar_credito(codigo_car: str):
    sql_query = text("""
    SELECT f.cod_imovel as car_codigo, f.municipio,
    (ST_Area(f.geometry::geography) / 10000)::numeric(10,2) as area_total_ha,
    CASE WHEN e.geometry IS NOT NULL THEN TRUE ELSE FALSE END as tem_embargo,
    e.nome_embar as infrator, e.des_infrac as motivo
    FROM fazendas_goias f LEFT JOIN embargos_ibama e ON ST_Intersects(f.geometry, e.geometry)
    WHERE f.cod_imovel ILIKE :filtro LIMIT 1
    """)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"filtro": f"%{codigo_car}%"})
        if df.empty: return {"status": "ERRO", "mensagem": "Não encontrado."}
        
        row = corrigir_acentos(df).iloc[0]
        area_ha = float(row['area_total_ha']) if row['area_total_ha'] else 0.0
        tem_embargo = row['tem_embargo']
        
        # Financeiro
        receita = area_ha * PRODUTIVIDADE_HA * PRECO_SACA
        lucro = receita - (area_ha * CUSTO_PRODUCAO_HA)
        
        # Score
        score = 1000; parecer = "🟢 APROVADO"; fatores = []
        if tem_embargo: score=0; parecer="🔴 REPROVADO (Compliance)"; fatores.append("Embargo Ibama")
        elif area_ha < 50: score=750; parecer="🟡 APROVADO C/ RESTRIÇÕES"; fatores.append("Pequeno Porte")
        
        return {
            "protocolo": "AGRO-2025-CLOUD",
            "dados_cliente": {"car": row['car_codigo'], "municipio": row['municipio'], "area_total_registrada": f"{area_ha:.2f} ha"},
            "analise_financeira": {
                "score_calculado": score, "parecer_final": parecer,
                "capacidade_pagamento_estimada": f"R$ {receita:,.2f}",
                "lucro_potencial_safra": f"R$ {lucro:,.2f}", "fatores_de_risco": fatores
            },
            "analise_ambiental": {"status": "IRREGULAR" if tem_embargo else "REGULAR", "detalhes": row['motivo'] if tem_embargo else "OK"}
        }
    except Exception as e: return {"erro": str(e)}