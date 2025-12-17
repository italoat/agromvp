import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="AgroCredit System", page_icon="🌽", layout="wide")

# CSS para métricas
st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

st.title("🌽 AgroCredit | Inteligência Geográfica")
st.markdown("**Base:** Goiás (GO) | **Módulo:** Análise Geoespacial & Crédito")
st.markdown("---")

# Menu
opcao = st.sidebar.radio("Navegação:", ["🗺️ Mapa de Risco (Heatmap)", "💰 Simulador de Crédito"])

# --- MÓDULO 1: MAPA E FILTROS ---
if opcao == "🗺️ Mapa de Risco (Heatmap)":
    st.subheader("📍 Monitoramento Territorial")
    
    # Botão de Carga
    if st.button("🔄 Carregar Dados de Goiás"):
        with st.spinner('Baixando dados do servidor...'):
            try:
                # 1. Busca os dados na API
                response = requests.get("http://127.0.0.1:8000/analise/risco-imediato")
                dados = response.json()
                
                if "ocorrencias" in dados:
                    df = pd.DataFrame(dados["ocorrencias"])
                    
                    # Salva na sessão para não perder ao filtrar
                    st.session_state['dados_risco'] = df
                    st.success(f"Base carregada: {len(df)} fazendas com problemas.")
                else:
                    st.warning("Nenhum dado encontrado.")
            except Exception as e:
                st.error(f"Erro ao conectar: {e}")

    # Se já tiver dados carregados, mostra o Dashboard
    if 'dados_risco' in st.session_state:
        df = st.session_state['dados_risco']
        
        # --- FILTROS INTELIGENTES ---
        col_filtro1, col_filtro2 = st.columns(2)
        
        # Filtro de Município
        lista_cidades = ["Todos"] + sorted(df['municipio'].unique().tolist())
        cidade_escolhida = col_filtro1.selectbox("Filtrar por Município:", lista_cidades)
        
        # Aplica o Filtro
        if cidade_escolhida != "Todos":
            df_view = df[df['municipio'] == cidade_escolhida]
        else:
            df_view = df
            
        # --- MÉTRICAS ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Fazendas Irregulares", len(df_view))
        m2.metric("Área Total Embargada", f"{df_view['area_contaminada_ha'].sum():,.0f} ha")
        m3.metric("Cidade", cidade_escolhida)
        
        # --- O MAPA (AQUI É A MÁGICA) ---
        st.subheader(f"🗺️ Mancha de Risco em {cidade_escolhida}")
        
        # O Streamlit precisa de colunas chamadas 'lat' e 'lon' (que criamos no main.py)
        if not df_view.empty:
            st.map(df_view[['lat', 'lon']], zoom=6 if cidade_escolhida == "Todos" else 9)
            
            # Tabela de Detalhes
            with st.expander("Ver Lista Detalhada"):
                st.dataframe(df_view[['car_codigo', 'municipio', 'infrator', 'area_contaminada_ha']])
        else:
            st.warning("Nenhuma ocorrência para este filtro.")

# --- MÓDULO 2: CRÉDITO (Mantido igual) ---
elif opcao == "💰 Simulador de Crédito":
    st.subheader("🏦 Análise Financeira Individual")
    cod = st.text_input("Código CAR:", "GO-5200050-5A317EC9392D475B8646E5BB494C262A")
    if st.button("Calcular"):
        try:
            res = requests.get(f"http://127.0.0.1:8000/consultar_credito?codigo_car={cod}").json()
            if "status" in res and res["status"] == "ERRO":
                st.warning(res["mensagem"])
            else:
                fin = res["analise_financeira"]
                st.metric("Score", fin["score_calculado"], delta=fin["parecer_final"])
                st.metric("Capacidade Pagamento", fin["capacidade_pagamento_estimada"])
        except: st.error("Erro na API")