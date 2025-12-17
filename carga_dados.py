import geopandas as gpd
from sqlalchemy import create_engine

# --- CONFIGURAÇÕES ---
# Substitua 'sua_senha_aqui' pela senha que você definiu na instalação do Windows
DB_USER = 'postgres'
DB_PASS = 'mysecretpassword' 
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'agro_db'  # O nome que criamos no pgAdmin

# Caminhos dos arquivos (Use o r"..." para o Windows não confundir as barras)
# Exemplo: r"C:\Users\SeuNome\Downloads\sorriso_area_imovel.shp"
path_fazendas = r"D:\AgroMVP\AREA_IMOVEL_1.shp" 
path_embargos = r"D:\AgroMVP\adm_embargo_ibama_a.shp" 

# --- CONEXÃO ---
# String de conexão ajustada para o banco nativo
db_connection_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_connection_url)

print("1. Lendo arquivos Shapefile (Isso pode demorar dependendo do tamanho)...")
try:
    gdf_fazendas = gpd.read_file(path_fazendas)
    gdf_embargos = gpd.read_file(path_embargos)
    
    print(f"   -> Fazendas carregadas: {len(gdf_fazendas)} registros")
    print(f"   -> Embargos carregados: {len(gdf_embargos)} registros")

    # --- PADRONIZAÇÃO (CRÍTICO) ---
    # Convertendo para SIRGAS 2000 (EPSG:4674) para garantir que os mapas se alinhem
    print("2. Convertendo sistema de coordenadas...")
    gdf_fazendas = gdf_fazendas.to_crs(epsg=4674)
    gdf_embargos = gdf_embargos.to_crs(epsg=4674)

    # --- CARGA NO BANCO ---
    print("3. Enviando para o PostgreSQL/PostGIS...")
    # chunksize ajuda a não travar o PC se o arquivo for gigante
    gdf_fazendas.to_postgis('fazendas_goias', engine, if_exists='replace', chunksize=1000)
    gdf_embargos.to_postgis('embargos_ibama', engine, if_exists='replace', chunksize=1000)

    print("\nSUCESSO! Dados carregados.")
    print("Agora volte ao pgAdmin para rodar a consulta SQL de cruzamento.")

except Exception as e:
    print(f"\nERRO: {e}")
    print("Dica: Verifique se o caminho do arquivo está certo e se a senha do banco está correta.")