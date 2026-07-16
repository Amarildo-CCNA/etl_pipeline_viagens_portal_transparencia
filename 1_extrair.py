"""
1_extrair.py
------------
Fase 1 do pipeline (Arquitetura Medallion): Extração e camada Raw.

- Baixa o .zip de origem do Google Drive (DRIVE_FILE_ID em config.py).
- Descompacta os 4 CSVs em PASTA_DADOS.
- Lê cada CSV em blocos (chunks) preservando o conteúdo original como texto
  (sem nenhuma conversão de tipo — isso é responsabilidade da camada Silver).
- Carrega cada bloco na respectiva tabela Raw, previamente criada pelo
  '0_criar_banco.sql'.
- Idempotente: faz TRUNCATE na tabela Raw antes de carregar (reexecuções não
  duplicam registros).
- Resiliente: cada etapa (download, extração, carga por tabela) é protegida
  por try/except, sem interromper silenciosamente o restante do pipeline.
"""

import zipfile

import gdown
import pandas as pd

import banco
import config


def baixar_zip():
    """Baixa o .zip de origem do Google Drive para a raiz do projeto."""
    zip_path = config.PASTA_RAIZ / f"{config.ANO}_viagens.zip"
    try:
        print(f"Baixando arquivo do Google Drive (ID: {config.DRIVE_FILE_ID})...")
        gdown.download(
            f"https://drive.google.com/uc?id={config.DRIVE_FILE_ID}",
            str(zip_path),
            quiet=False,
        )
        print(f"Download concluído: {zip_path}")
        return zip_path
    except Exception as erro:
        print(f"Erro ao baixar o arquivo do Google Drive: {erro}")
        return None


def descompactar_zip(zip_path):
    """Extrai os CSVs do .zip para a pasta de dados (config.PASTA_DADOS)."""
    config.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    try:
        print(f"Descompactando '{zip_path.name}' em '{config.PASTA_DADOS}'...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(config.PASTA_DADOS)
        print("CSVs extraídos com sucesso.")
        return True
    except FileNotFoundError:
        print(f"Erro: o arquivo '{zip_path}' não foi encontrado.")
        return False
    except zipfile.BadZipFile:
        print(f"Erro: '{zip_path}' não é um .zip válido (download pode ter falhado).")
        return False
    except Exception as erro:
        print(f"Erro inesperado ao descompactar: {erro}")
        return False


def truncar_tabela(conexao, tabela):
    """Esvazia a tabela Raw antes da carga, garantindo idempotência."""
    tabela_qualificada = f"{config.RAW_SCHEMA}.{tabela}"
    banco.executar(conexao, f"TRUNCATE TABLE {tabela_qualificada};")
    print(f"Tabela '{tabela_qualificada}' truncada.")


def carregar_csv_em_blocos(conexao, csv_nome, tabela):
    """
    Lê um CSV em blocos (chunks) e insere cada bloco na tabela Raw
    correspondente, sem alterar o conteúdo original (tudo como texto).
    """
    caminho_csv = config.PASTA_DADOS / csv_nome

    if not caminho_csv.exists():
        print(f"Aviso: '{csv_nome}' não encontrado em '{config.PASTA_DADOS}'. Pulando...")
        return

    try:
        truncar_tabela(conexao, tabela)

        tabela_qualificada = f"{config.RAW_SCHEMA}.{tabela}"
        total_linhas = 0
        leitor = pd.read_csv(
            caminho_csv,
            sep=config.CSV_SEPARADOR,
            encoding=config.CSV_ENCODING,
            dtype=str,
            chunksize=config.TAMANHO_BLOCO,
        )

        for numero_bloco, bloco in enumerate(leitor, start=1):
            # remove espaços nas pontas dos cabeçalhos (ex.: CSV de Trecho
            # vem com "Identificador do processo de viagem " com espaço extra).
            bloco.columns = [str(c).strip() for c in bloco.columns]

            # renomeia as colunas do CSV para os nomes reais da tabela Raw.
            mapa_colunas = config.COLUNAS_RAW[tabela]
            bloco = bloco.rename(columns=mapa_colunas)
            bloco = bloco[list(mapa_colunas.values())]  # garante ordem e remove colunas não mapeadas.

            # troca NaN por None (NULL no banco); mantém tudo mais como string.
            bloco = bloco.where(pd.notnull(bloco), None)

            colunas = ", ".join(bloco.columns)
            marcadores = ", ".join(["%s"] * len(bloco.columns))
            sql_insert = f"INSERT INTO {tabela_qualificada} ({colunas}) VALUES ({marcadores})"

            linhas = list(bloco.itertuples(index=False, name=None))
            banco.inserir_em_lote(conexao, sql_insert, linhas)

            total_linhas += len(linhas)
            print(f"  bloco {numero_bloco}: {len(linhas)} linhas inseridas em '{tabela_qualificada}'.")

        print(f"Sucesso: '{tabela_qualificada}' populada com {total_linhas} linhas no total.")

    except Exception as erro:
        print(f"Erro ao carregar '{csv_nome}' em '{tabela}': {erro}")
        conexao.rollback()  
        # desfaz a transação abortada, liberando a conexão
        # para as próximas tabelas (sem isso, o Postgres rejeita todo comando
        # seguinte com "current transaction is aborted").


def extrair_e_carregar():
    """Orquestra a Fase 1 do pipeline: download, extração e carga na Raw."""
    zip_path = baixar_zip()
    if zip_path is None:
        return

    if not descompactar_zip(zip_path):
        return

    try:
        conexao = banco.conectar()
    except RuntimeError as erro:
        print(erro)
        return

    try:
        for info in config.ARQUIVOS.values():
            carregar_csv_em_blocos(conexao, info["csv"], info["tabela_raw"])
    finally:
        conexao.close()
        print("Conexão com o PostgreSQL encerrada.")


if __name__ == "__main__":
    extrair_e_carregar()
