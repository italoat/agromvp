import streamlit as st
import requests
import pandas as pd

# --- CONFIGURAÇÃO ---
# URL da sua API na Nuvem (Render)
API_URL = "https://agromvp.onrender.com"

st.set_page_config(page_title="AgroCredit System", page_icon="🌽", layout="wide")
st.markdown("<style>.stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 5px;}</style>", unsafe_allow_html=True)

st.title("🌽 AgroCredit | Inteligência de Mercado")
st.markdown("**Base:** Goiás (GO) | **Visão:** Risco & Oportunidade")
st.markdown("---")

opcao = st.sidebar.radio("Navegação:", ["🗺️ Radar de Mercado (Mapa)", "💰 Simulador de Crédito"])

# --- MÓDULO 1: MAPA (RISCO + OPORTUNIDADE) ---
if opcao == "🗺️ Radar de Mercado (Mapa)":
    st.subheader("📍 Monitoramento Territorial")
    
    if st.button("🔄 Atualizar Mapa (Riscos + Oportunidades)"):
        with st.spinner('Baixando dados do servidor...'):
            try:
                # 1. Busca RISCOS (Vermelhos)
                res_risco = requests.get(f"{API_URL}/analise/risco-imediato").json()
                df_risco = pd.DataFrame(res_risco.get("ocorrencias", []))
                
                # 2. Busca OPORTUNIDADES (Verdes)
                res_green = requests.get(f"{API_URL}/analise/oportunidades").json()
                df_green = pd.DataFrame(res_green.get("dados", []))
                
                # Prepara cores
                if not df_risco.empty:
                    df_risco["cor"] = "#FF0044" # Vermelho
                    df_risco["tipo"] = "Risco Ambiental"
                    
                if not df_green.empty:
                    df_green["cor"] = "#00CC66" # Verde
                    df_green["tipo"] = "Aprovada"
                    # Ajuste de colunas
                    cols = ["car_codigo", "municipio", "lat", "lon", "cor", "tipo"]
                    df_green = df_green[cols]

                # Junta tudo
                df_final = pd.concat([df_risco, df_green], ignore_index=True)
                st.session_state['mapa_dados'] = df_final
                st.success(f"Carregados: {len(df_risco)} Riscos e {len(df_green)} Oportunidades.")
                
            except Exception as e:
                st.error(f"Erro ao conectar na API: {e}")

    if 'mapa_dados' in st.session_state:
        df = st.session_state['mapa_dados']
        cidades = ["Todos"] + sorted(df['municipio'].unique().tolist())
        filtro = st.selectbox("Filtrar Cidade:", cidades)
        
        df_view = df if filtro == "Todos" else df[df['municipio'] == filtro]
        
        st.map(df_view, latitude="lat", longitude="lon", color="cor", size=20, zoom=6)
        st.caption("🔴 Vermelho: Embargo | 🟢 Verde: Aprovada")
        with st.expander("Ver Lista"): st.dataframe(df_view[["car_codigo", "municipio", "tipo"]])

# --- MÓDULO 2: CRÉDITO ---
elif opcao == "💰 Simulador de Crédito":
    st.subheader("🏦 Análise Financeira Individual")
    cod = st.text_input("Código CAR:", "GO-5200050-5A317EC9392D475B8646E5BB494C262A")
    if st.button("Calcular Score"):
        try:
            res = requests.get(f"{API_URL}/consultar_credito?codigo_car={cod}").json()
            if res.get("status") == "ERRO":
                st.warning(res["mensagem"])
            else:
                fin = res["analise_financeira"]
                st.metric("Score", fin["score_calculado"], delta=fin["parecer_final"])
                st.metric("Capacidade Pagamento", fin["capacidade_pagamento_estimada"])
        except Exception as e: st.error(f"Erro: {e}")