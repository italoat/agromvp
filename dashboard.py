import streamlit as st
import requests
import pandas as pd

# --- CONFIGURAÇÃO DA API ---
# IMPORTANTE: Como o Dashboard e a API rodam juntos no mesmo servidor do Render,
# usamos o endereço interno (localhost) para garantir que a comunicação seja rápida e direta.
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AgroCredit System", page_icon="🌽", layout="wide")

# Estilização simples para métricas
st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

st.title("🌽 AgroCredit | Inteligência de Mercado")
st.markdown("**Base:** Goiás (GO) | **Visão:** Risco & Oportunidade")
st.markdown("---")

# Menu Lateral
opcao = st.sidebar.radio("Navegação:", ["🗺️ Radar de Mercado (Mapa)", "💰 Simulador de Crédito"])

# --- MÓDULO 1: RADAR DE MERCADO (MAPA UNIFICADO) ---
if opcao == "🗺️ Radar de Mercado (Mapa)":
    st.subheader("📍 Monitoramento Territorial")
    
    col_btn1, col_btn2 = st.columns([1, 4])
    if col_btn1.button("🔄 Atualizar Mapa (Riscos + Oportunidades)"):
        with st.spinner('Conectando ao satélite e cruzando bases...'):
            try:
                # 1. Busca FAZENDAS COM RISCO (Pontos Vermelhos)
                try:
                    res_risco = requests.get(f"{API_URL}/analise/risco-imediato").json()
                    df_risco = pd.DataFrame(res_risco.get("ocorrencias", []))
                except:
                    df_risco = pd.DataFrame() # Se falhar, cria vazio

                # 2. Busca OPORTUNIDADES (Pontos Verdes)
                try:
                    res_green = requests.get(f"{API_URL}/analise/oportunidades").json()
                    df_green = pd.DataFrame(res_green.get("dados", []))
                except:
                    df_green = pd.DataFrame()

                # 3. Processamento das Cores e Tipos
                if not df_risco.empty:
                    df_risco["cor"] = "#FF0044" # Vermelho Alerta
                    df_risco["tipo"] = "Risco Ambiental (Embargada)"
                    
                if not df_green.empty:
                    df_green["cor"] = "#00CC66" # Verde Oportunidade
                    df_green["tipo"] = "Aprovada (Sem Restrições)"
                    # Ajusta colunas para baterem com o dataframe de risco
                    cols_comuns = ["car_codigo", "municipio", "lat", "lon", "cor", "tipo"]
                    # Garante que só pegamos as colunas que existem
                    df_green = df_green[[c for c in cols_comuns if c in df_green.columns]]

                # 4. Unificação
                df_final = pd.concat([df_risco, df_green], ignore_index=True)
                
                # Salva na memória do navegador (Session State)
                st.session_state['mapa_dados'] = df_final
                
                total_r = len(df_risco)
                total_v = len(df_green)
                st.success(f"Radar Atualizado: {total_r} Riscos Detectados | {total_v} Oportunidades Encontradas.")
                
            except Exception as e:
                st.error(f"Erro crítico ao processar dados: {e}")

    # Renderiza o Mapa e a Lista se houver dados
    if 'mapa_dados' in st.session_state:
        df = st.session_state['mapa_dados']
        
        # --- ÁREA DE FILTROS ---
        st.markdown("### Filtros de Visualização")
        c1, c2 = st.columns(2)
        
        # Filtro 1: Município
        cidades = ["Todos"] + sorted(df['municipio'].unique().tolist())
        filtro_cidade = c1.selectbox("📍 Filtrar por Município:", cidades)
        
        # Filtro 2: Status (Risco / Oportunidade) - Multiselect
        opcoes_tipo = df['tipo'].unique().tolist()
        filtro_tipo = c2.multiselect(
            "📊 Filtrar por Status:", 
            options=opcoes_tipo, 
            default=opcoes_tipo # Começa com todos marcados
        )
        
        # Aplica os filtros no DataFrame
        df_view = df.copy()
        
        if filtro_cidade != "Todos":
            df_view = df_view[df_view['municipio'] == filtro_cidade]
            
        if filtro_tipo:
            df_view = df_view[df_view['tipo'].isin(filtro_tipo)]

        # --- EXIBIÇÃO DO MAPA ---
        st.map(df_view, latitude="lat", longitude="lon", color="cor", size=20, zoom=6)
        st.caption("Legenda: 🔴 Vermelho = Fazenda Embargada | 🟢 Verde = Fazenda Aprovada para Crédito")
        
        # --- EXIBIÇÃO DA LISTA DETALHADA ---
        st.markdown("---")
        st.subheader("📋 Lista Detalhada")
        
        if not df_view.empty:
            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                # Ordem das colunas: Cor primeiro
                column_order=["cor", "tipo", "municipio", "car_codigo"],
                column_config={
                    "cor": st.column_config.ColorColumn(
                        "Indicador", # Cabeçalho da coluna
                        width="small",
                        help="Vermelho: Risco | Verde: Oportunidade"
                    ),
                    "tipo": st.column_config.TextColumn(
                        "Classificação",
                        width="medium"
                    ),
                    "municipio": st.column_config.TextColumn(
                        "Município"
                    ),
                    "car_codigo": st.column_config.TextColumn(
                        "Código CAR",
                        help="Cadastro Ambiental Rural"
                    )
                }
            )
        else:
            st.warning("Nenhum dado encontrado com os filtros selecionados.")

# --- MÓDULO 2: SIMULADOR DE CRÉDITO ---
elif opcao == "💰 Simulador de Crédito":
    st.subheader("🏦 Análise Financeira Individual")
    
    st.info("Insira o CAR da fazenda para calcular o Score de Crédito em tempo real.")
    cod = st.text_input("Código CAR:", "GO-5200050-5A317EC9392D475B8646E5BB494C262A")
    
    if st.button("Calcular Score e Limites"):
        with st.spinner('Calculando potencial produtivo...'):
            try:
                # Chama a API interna
                url = f"{API_URL}/consultar_credito?codigo_car={cod}"
                response = requests.get(url)
                
                # Verifica se a API respondeu 200 OK
                if response.status_code == 200:
                    res = response.json()
                    
                    if res.get("status") == "ERRO":
                        st.warning(res["mensagem"])
                    else:
                        fin = res["analise_financeira"]
                        dados = res["dados_cliente"]
                        
                        # Exibição dos Cartões (KPIs)
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Área Produtiva", dados["area_total_registrada"])
                        col2.metric("Score de Crédito", fin["score_calculado"], delta=fin["parecer_final"])
                        col3.metric("Potencial Receita", fin["capacidade_pagamento_estimada"])
                        
                        st.markdown("### 📋 Parecer Técnico")
                        st.write(f"**Resultado:** {fin['parecer_final']}")
                        st.write(f"**Lucro Estimado da Safra:** {fin['lucro_potencial_safra']}")
                        
                        if fin["fatores_de_risco"]:
                            st.error(f"Fatores de Risco: {', '.join(fin['fatores_de_risco'])}")
                        else:
                            st.success("Nenhum fator de risco ambiental ou financeiro identificado.")
                else:
                    st.error("Erro ao comunicar com o servidor de análise.")
                    
            except Exception as e: 
                st.error(f"Erro de conexão: {e}")