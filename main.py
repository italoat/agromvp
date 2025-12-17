from fastapi import FastAPI
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Optional

app = FastAPI(
    title="AgroCredit Engine", 
    description="Motor de Análise de Crédito e Risco Socioambiental (Goiás)", 
    version="3.2"
)

# --- 1. CONFIGURAÇÃO ---
DB_USER = 'postgres'
DB_PASS = 'mysecretpassword' # <--- CONFIRA A SENHA
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'agro_db'

db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url, client_encoding='utf8')

# --- 2. PARÂMETROS ---
PRECO_SACA = 115.00
PRODUTIVIDADE_HA = 60
CUSTO_PRODUCAO_HA = 4500.00

# --- 3. AUXILIARES ---
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
    return {"mensagem": "AgroCredit Engine V3.2 Online!"}

# --- ROTA 4: RELATÓRIO GERAL (COM GPS) ---
@app.get("/analise/risco-imediato")
def verificar_todos_riscos():
    """
    Retorna Lista Negra com Coordenadas para Mapa.
    """
    # NOVIDADE: Calculamos ST_X (Lon) e ST_Y (Lat) do centro da fazenda
    sql_query = """
    SELECT 
        f.cod_imovel as car_codigo,
        f.municipio,
        ST_Y(ST_Centroid(f.geometry::geometry)) as lat,
        ST_X(ST_Centroid(f.geometry::geometry)) as lon,
        e.nome_embar as infrator,
        e.des_infrac as motivo,
        (ST_Area(ST_Intersection(f.geometry, e.geometry)::geography) / 10000)::numeric(10,2) as area_contaminada_ha
    FROM 
        fazendas_goias f
    JOIN 
        embargos_ibama e 
        ON ST_Intersects(f.geometry, e.geometry)
    ORDER BY 
        area_contaminada_ha DESC;
    """
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql_query), conn)
        
        if df.empty:
            return {"status": "Nenhum risco detectado", "ocorrencias": []}
            
        df = corrigir_acentos(df)
        
        return {
            "status": "ALERTA: Riscos Detectados", 
            "total_encontrado": len(df),
            "ocorrencias": df.to_dict(orient="records")
        }

    except Exception as e:
        return {"erro_interno": str(e)}

# --- ROTA 5: BUSCA SIMPLES ---
@app.get("/consultar")
def consultar_por_car(codigo_car: Optional[str] = None):
    if not codigo_car: return {"erro": "Forneça um código."}
    
    sql_query = text("""
    SELECT 
        f.cod_imovel as car_codigo,
        f.municipio,
        e.nome_embar as infrator,
        e.des_infrac as motivo,
        (ST_Area(ST_Intersection(f.geometry, e.geometry)::geography) / 10000)::numeric(10,2) as area_contaminada_ha
    FROM 
        fazendas_goias f
    JOIN 
        embargos_ibama e 
        ON ST_Intersects(f.geometry, e.geometry)
    WHERE f.cod_imovel ILIKE :filtro
    """)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"filtro": f"%{codigo_car}%"})
        if df.empty: return {"status": "NADA CONSTA"}
        df = corrigir_acentos(df)
        return {"status": "ALERTA", "detalhes": df.to_dict(orient="records")}
    except Exception as e: return {"erro": str(e)}

# --- ROTA 6: ANÁLISE CRÉDITO ---
@app.get("/consultar_credito")
def consultar_credito(codigo_car: str):
    sql_query = text("""
    SELECT 
        f.cod_imovel as car_codigo,
        f.municipio,
        (ST_Area(f.geometry::geography) / 10000)::numeric(10,2) as area_total_ha,
        CASE WHEN e.geometry IS NOT NULL THEN TRUE ELSE FALSE END as tem_embargo,
        e.nome_embar as infrator,
        e.des_infrac as motivo,
        (ST_Area(ST_Intersection(f.geometry, e.geometry)::geography) / 10000)::numeric(10,2) as area_contaminada_ha
    FROM fazendas_goias f
    LEFT JOIN embargos_ibama e ON ST_Intersects(f.geometry, e.geometry)
    WHERE f.cod_imovel ILIKE :filtro
    LIMIT 1
    """)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"filtro": f"%{codigo_car}%"})
        if df.empty: return {"status": "ERRO", "mensagem": "Não encontrado."}
        
        df = corrigir_acentos(df)
        row = df.iloc[0]
        area_ha = float(row['area_total_ha']) if row['area_total_ha'] is not None else 0.0
        tem_embargo = row['tem_embargo']
        
        # Financeiro
        receita = area_ha * PRODUTIVIDADE_HA * PRECO_SACA
        lucro = receita - (area_ha * CUSTO_PRODUCAO_HA)
        
        # Score
        score = 1000
        parecer = "🟢 APROVADO"
        fatores = []
        if tem_embargo:
            score = 0; parecer = "🔴 REPROVADO (Compliance)"; fatores.append("Embargo Ibama")
        elif area_ha < 50:
            score = 750; parecer = "🟡 APROVADO C/ RESTRIÇÕES"; fatores.append("Pequeno Porte")
            
        return {
            "protocolo": "AGRO-V3",
            "dados_cliente": {"car": row['car_codigo'], "municipio": row['municipio'], "area_total_registrada": f"{area_ha:.2f} ha"},
            "analise_financeira": {
                "score_calculado": score, "parecer_final": parecer,
                "capacidade_pagamento_estimada": f"R$ {receita:,.2f}", "lucro_potencial_safra": f"R$ {lucro:,.2f}",
                "fatores_de_risco": fatores
            },
            "analise_ambiental": {"status": "IRREGULAR" if tem_embargo else "REGULAR", "detalhes": row['motivo'] if tem_embargo else "OK"}
        }
    except Exception as e: return {"erro": str(e)}