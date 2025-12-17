import geopandas as gpd
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO DA CONEXÃO (NEON) ---
# Sua string de conexão com o banco na nuvem
DB_CONNECTION = "postgresql+psycopg2://neondb_owner:npg_ZL2qeh4yHGSm@ep-curly-boat-ac2r3idj-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

print("📡 Conectando ao Banco Neon na Nuvem...")
engine = create_engine(DB_CONNECTION, echo=False)

# --- 2. PREPARAÇÃO DO BANCO ---
def preparar_banco():
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
        print("✅ Extensão PostGIS verificada.")
    except Exception as e:
        print(f"❌ Erro ao ativar PostGIS: {e}")

# --- 3. FUNÇÃO DE CARGA ---
def subir_shapefile(caminho_arquivo, nome_tabela):
    # Verifica se o arquivo existe antes de tentar ler
    if not os.path.exists(caminho_arquivo):
        print(f"❌ ARQUIVO NÃO ENCONTRADO: {caminho_arquivo}")
        print(f"   Dica: Verifique se o arquivo .shp está na pasta {os.getcwd()}")
        return

    print(f"📂 Lendo arquivo: {caminho_arquivo}...")
    try:
        gdf = gpd.read_file(caminho_arquivo)
        gdf.columns = [col.lower() for col in gdf.columns]
        
        if gdf.crs is None:
            gdf.set_crs(epsg=4674, inplace=True)
        else:
            gdf.to_crs(epsg=4674, inplace=True)

        print(f"🚀 Enviando {len(gdf)} registros para tabela '{nome_tabela}'...")
        
        gdf.to_postgis(
            name=nome_tabela,
            con=engine,
            if_exists='replace',
            index=False,
            chunksize=1000 
        )
        print(f"✅ Tabela '{nome_tabela}' carregada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro crítico ao subir {nome_tabela}: {e}")

# --- 4. EXECUÇÃO ---
if __name__ == "__main__":
    preparar_banco()
    
    # --- CORREÇÃO AQUI: REMOVEMOS AS PASTAS ---
    # Usando os nomes que apareceram no seu 'git ls-files'
    caminho_fazendas = "AREA_IMOVEL_1.shp" 
    caminho_embargos = "adm_embargo_ibama_a.shp"
    
    subir_shapefile(caminho_fazendas, "fazendas_goias")
    subir_shapefile(caminho_embargos, "embargos_ibama")
    
    print("\n🏁 Processo Finalizado!")