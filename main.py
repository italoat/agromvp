from fastapi import FastAPI
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Optional
import os

app = FastAPI(
    title="AgroCredit Engine", 
    description="Motor de Análise de Crédito e Risco Socioambiental (Goiás)", 
    version="3.3 Production"
)

# --- 1. CONFIGURAÇÃO DO BANCO DE DADOS (NEON.TECH) ---
# Já configurei com os dados que você me passou
# Dica: Em um projeto real futuro, usamos variáveis de ambiente (os.getenv) para esconder a senha.
DB_USER = "neondb_owner"
DB_PASS = "npg_ZL2qeh4yHGSm"
DB_HOST = "ep-curly-boat-ac2r3idj-pooler.sa-east-1.aws.neon.tech"
DB_NAME = "neondb"

# Monta a URL de conexão segura
# Adicionamos '?sslmode=require' que é obrigatório para o Neon
db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?sslmode=require"

try:
    engine = create_engine(db_url, client_encoding='utf8', pool_pre_ping=True)
except Exception as e:
    print(f"Erro ao configurar banco: {e}")

# --- 2. PARÂMETROS DE MERCADO (SOJA - GOIÁS) ---
PRECO_SACA = 115.00       # R$ por saca
PRODUTIVIDADE_HA = 60     # Sacas por hectare
CUSTO_PRODUCAO_HA = 4500.00 # Custo médio por hectare

# --- 3. FUNÇÕES AUXILIARES ---
def corrigir_acentos(df):
    """Corrige codificação de texto vindo do banco"""
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

# --- ROTA 4: RELATÓRIO GERAL (MAPA DE CALOR) ---
@app.get("/analise/risco-imediato")
def verificar_todos_riscos():
    """
    Retorna Lista Negra com Lat/Lon para o Mapa.
    """
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
        area_contaminada_ha DESC
    LIMIT 500; -- Limitamos a 500 para não travar o mapa na nuvem
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
    if not codigo_car:
        return {"erro": "Forneça um código."}

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
    WHERE 
        f.cod_imovel ILIKE :filtro_usuario
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"filtro_usuario": f"%{codigo_car}%"})
        
        if df.empty:
            return {"status": "NADA CONSTA", "mensagem": "Fazenda Limpa de Embargos."}
        
        df = corrigir_acentos(df)

        return {
            "status": "ALERTA VERMELHO", 
            "risco": "Embargo Detectado",
            "detalhes": df.to_dict(orient="records")
        }

    except Exception as e:
        return {"erro_interno": str(e)}

# --- ROTA 6: ANÁLISE DE CRÉDITO (COM CÁLCULO FINANCEIRO) ---
@app.get("/consultar_credito")
def consultar_credito(codigo_car: str):
    # Usa ST_Area para calcular hectares reais via satélite
    sql_query = text("""
    SELECT 
        f.cod_imovel as car_codigo,
        f.municipio,
        (ST_Area(f.geometry::geography) / 10000)::numeric(10,2) as area_total_ha,
        
        CASE WHEN e.geometry IS NOT NULL THEN TRUE ELSE FALSE END as tem_embargo,
        e.nome_embar as infrator,
        e.des_infrac as motivo,
        (ST_Area(ST_Intersection(f.geometry, e.geometry)::geography) / 10000)::numeric(10,2) as area_contaminada_ha
        
    FROM 
        fazendas_goias f
    LEFT JOIN 
        embargos_ibama e 
        ON ST_Intersects(f.geometry, e.geometry)
    WHERE 
        f.cod_imovel ILIKE :filtro
    LIMIT 1
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"filtro": f"%{codigo_car}%"})
        
        if df.empty:
            return {"status": "ERRO", "mensagem": "Fazenda não encontrada na base de dados."}
        
        df = corrigir_acentos(df)
        row = df.iloc[0]
        
        # --- CÁLCULOS FINANCEIROS ---
        area_ha = float(row['area_total_ha']) if row['area_total_ha'] is not None else 0.0
        tem_embargo = row['tem_embargo']
        
        receita_potencial = area_ha * PRODUTIVIDADE_HA * PRECO_SACA
        custo_estimado = area_ha * CUSTO_PRODUCAO_HA
        lucro_operacional = receita_potencial - custo_estimado
        
        # --- SCORE DE CRÉDITO ---
        score = 1000
        parecer = "🟢 APROVADO"
        fatores = []
        
        if tem_embargo:
            score = 0
            parecer = "🔴 REPROVADO (Compliance Ambiental)"
            fatores.append("Sobreposição com Área Embargada pelo Ibama")
        elif area_ha < 50:
            score = 750
            parecer = "🟡 APROVADO COM RESTRIÇÕES"
            fatores.append("Pequeno Produtor (Área < 50ha)")
        elif area_ha > 1000:
            fatores.append("Grande Produtor (Alta Escala)")

        return {
            "protocolo": "AGRO-2025-CLOUD",
            "dados_cliente": {
                "car": row['car_codigo'],
                "municipio": row['municipio'],
                "area_total_calculada": f"{area_ha:.2f} ha"
            },
            "analise_financeira": {
                "score_calculado": score,
                "parecer_final": parecer,
                "capacidade_pagamento_estimada": f"R$ {receita_potencial:,.2f}",
                "lucro_potencial_safra": f"R$ {lucro_operacional:,.2f}",
                "fatores_de_risco": fatores
            },
            "analise_ambiental": {
                "status": "IRREGULAR" if tem_embargo else "REGULAR",
                "detalhes": row['motivo'] if tem_embargo else "Nenhuma restrição encontrada."
            }
        }

    except Exception as e:
        return {"erro_interno": str(e)}