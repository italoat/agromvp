import streamlit as st
import requests
import pandas as pd

# --- CONFIGURAÇÃO DA API ---
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AgroCredit System", page_icon="🌽", layout="wide")

# Estilização simples
st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

st.title("🌽 AgroCredit | Inteligência de Mercado")
st.markdown("**Base:** Goiás (GO) | **Visão:** Risco & Oportunidade")
st.markdown("---")

opcao = st.sidebar.radio("Navegação:", ["🗺️ Radar de Mercado (Mapa)", "💰 Simulador de Crédito"])

# --- MÓDULO 1: RADAR DE MERCADO ---
if opcao == "🗺️ Radar de Mercado (Mapa)":
    st.subheader("📍 Monitoramento Territorial")
    
    col_btn1, col_btn2 = st.columns([1, 4])
    if col_btn1.button("🔄 Atualizar Mapa"):
        with st.spinner('Conectando ao satélite...'):
            try:
                # 1. Busca RISCOS
                try:
                    res_risco = requests.get(f"{API_URL}/analise/risco-imediato").json()
                    df_risco = pd.DataFrame(res_risco.get("ocorrencias", []))
                except:
                    df_risco = pd.DataFrame()

                # 2. Busca OPORTUNIDADES
                try:
                    res_green = requests.get(f"{API_URL}/analise/oportunidades").json()
                    df_green = pd.DataFrame(res_green.get("dados", []))
                except:
                    df_green = pd.DataFrame()

                # 3. Processamento (Criação de colunas visuais)
                if not df_risco.empty:
                    df_risco["cor"] = "#FF0044" # Para o MAPA (Hex)
                    df_risco["tipo"] = "Risco Ambiental (Embargada)"
                    df_risco["status_visual"] = "🔴 Risco (Embargo)" # Para a TABELA (Emoji)
                    
                if not df_green.empty:
                    df_green["cor"] = "#00CC66" # Para o MAPA (Hex)
                    df_green["tipo"] = "Aprovada (Sem Restrições)"
                    df_green["status_visual"] = "🟢 Oportunidade (Crédito)" # Para a TABELA (Emoji)
                    
                    # Filtra colunas comuns
                    cols_comuns = ["car_codigo", "municipio", "lat", "lon", "cor", "tipo", "status_visual"]
                    df_green = df_green[[c for c in cols_comuns if c in df_green.columns]]

                # 4. Unificação
                df_final = pd.concat([df_risco, df_green], ignore_index=True)
                
                st.session_state['mapa_dados'] = df_final
                
                total_r = len(df_risco)
                total_v = len(df_green)
                st.success(f"Radar Atualizado: {total_r} Riscos | {total_v} Oportunidades.")
                
            except Exception as e:
                st.error(f"Erro ao processar dados: {e}")

    # Renderiza Mapa e Lista
    if 'mapa_dados' in st.session_state:
        df = st.session_state['mapa_dados']
        
        # --- FILTROS ---
        c1, c2 = st.columns(2)
        
        cidades = ["Todos"] + sorted(df['municipio'].unique().tolist())
        filtro_cidade = c1.selectbox("📍 Município:", cidades)
        
        opcoes_tipo = df['tipo'].unique().tolist()
        filtro_tipo = c2.multiselect("📊 Status:", opcoes_tipo, default=opcoes_tipo)
        
        # Aplica filtros
        df_view = df.copy()
        if filtro_cidade != "Todos":
            df_view = df_view[df_view['municipio'] == filtro_cidade]
        if filtro_tipo:
            df_view = df_view[df_view['tipo'].isin(filtro_tipo)]

        # MAPA (Usa a coluna 'cor' com código Hex)
        st.map(df_view, latitude="lat", longitude="lon", color="cor", size=20, zoom=6)
        
        # LISTA DETALHADA (Usa Emojis para evitar erro de versão)
        st.markdown("---")
        st.subheader("📋 Lista Detalhada")
        
        if not df_view.empty:
            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                column_order=["status_visual", "municipio", "car_codigo"], # Ordem das colunas
                column_config={
                    "status_visual": st.column_config.TextColumn("Status"),
                    "municipio": st.column_config.TextColumn("Município"),
                    "car_codigo": st.column_config.TextColumn("Código CAR")
                }
            )
        else:
            st.warning("Sem dados para exibir.")

# --- MÓDULO 2: SIMULADOR ---
elif opcao == "💰 Simulador de Crédito":
    st.subheader("🏦 Análise Financeira")
    cod = st.text_input("Código CAR:", "GO-5200050-5A317EC9392D475B8646E5BB494C262A")
    
    if st.button("Calcular Score"):
        with st.spinner('Calculando...'):
            try:
                res = requests.get(f"{API_URL}/consultar_credito?codigo_car={cod}").json()
                if res.get("status") == "ERRO":
                    st.warning(res["mensagem"])
                else:
                    fin = res["analise_financeira"]
                    dados = res["dados_cliente"]
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Área Total", dados["area_total_registrada"])
                    c2.metric("Score", fin["score_calculado"], delta=fin["parecer_final"])
                    c3.metric("Receita Est.", fin["capacidade_pagamento_estimada"])
                    
                    st.success(f"Parecer: {fin['parecer_final']}")
                    if fin["fatores_de_risco"]:
                        st.error(f"Riscos: {fin['fatores_de_risco']}")
            except Exception as e: 
                st.error(f"Erro de conexão: {e}")