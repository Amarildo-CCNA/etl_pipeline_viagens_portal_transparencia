"""
config.py
---------
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------
# PASTA_RAIZ = .../desafio_transparencia (a pasta deste arquivo)
PASTA_RAIZ = Path(__file__).resolve().parent
# onde o .zip e os .csv ficam (ignorada pelo Git)
PASTA_DADOS = PASTA_RAIZ / "data"


# ---------------------------------------------------------------------------
# Leitura simples do arquivo .env (sem biblioteca externa)
# ---------------------------------------------------------------------------
def carregar_env():
    """Le o arquivo .env (se existir) e joga as variaveis para os.environ."""
    arquivo_env = PASTA_RAIZ / ".env"
    if not arquivo_env.exists():
        return
    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        # ignora linhas vazias e comentarios
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


carregar_env()


# ---------------------------------------------------------------------------
# Credenciais do PostgreSQL (vem do .env)
# ---------------------------------------------------------------------------
POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
    "dbname": os.environ.get("POSTGRES_DATABASE", "transparencia"),
}


# ---------------------------------------------------------------------------
# Schema onde as tabelas Raw vivem no PostgreSQL. O PDF do desafio não define
# um schema próprio para a Raw, então usamos 'public' (padrão), igual à Silver.
# ---------------------------------------------------------------------------
RAW_SCHEMA = "public"

# Ajuste aqui se suas tabelas Silver estiverem em um schema próprio.
SILVER_SCHEMA = "public"


# ---------------------------------------------------------------------------
# O que vamos baixar e processar
# ---------------------------------------------------------------------------
ANO = "2025"

# ---- De onde baixar o .zip ----
# O arquivo (enxuto, so com jan-jun de 2025) fica no Google Drive da escola.
# ID do arquivo no Google Drive:
# Como obter: no Drive clique em "Compartilhar" -> "Qualquer pessoa com o link";
# o link fica .../file/d/ESTE_TRECHO_E_O_ID/view -> copie o ID e cole abaixo.
DRIVE_FILE_ID = "15vGhmvT0Ux2crqHy_YeRoRiaiCkdB88A"

# Tamanho do bloco de leitura/insercao (numero de linhas por vez).
# Ler tudo de uma vez estouraria a memoria; por isso lemos em "pedacos".
TAMANHO_BLOCO = 50_000


# ---------------------------------------------------------------------------
# Mapeamento: nome da coluna no CSV real -> nome da coluna na tabela Raw.
# Necessário porque os CSVs do Portal da Transparência usam nomes de coluna
# com espaços/acentos (ex.: "Identificador do processo de viagem"), que não
# podem ser usados diretamente num INSERT SQL. As chaves já vêm sem espaços
# nas pontas (o código faz .strip() antes de aplicar o mapeamento, pois o
# CSV de Trecho tem um espaço sobrando no primeiro cabeçalho).
# ---------------------------------------------------------------------------
COLUNAS_RAW = {
    "raw_viagem": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Situação": "situacao",
        "Viagem Urgente": "viagem_urgente",
        "Justificativa Urgência Viagem": "justificativa_urgencia",
        "Código do órgão superior": "cod_orgao_superior",
        "Nome do órgão superior": "nome_orgao_superior",
        "Código órgão solicitante": "cod_orgao_solicitante",
        "Nome órgão solicitante": "nome_orgao_solicitante",
        "CPF viajante": "cpf_viajante",
        "Nome": "nome_viajante",
        "Cargo": "cargo",
        "Função": "funcao",
        "Descrição Função": "descricao_funcao",
        "Período - Data de início": "data_inicio",
        "Período - Data de fim": "data_fim",
        "Destinos": "destinos",
        "Motivo": "motivo",
        "Valor diárias": "valor_diarias",
        "Valor passagens": "valor_passagens",
        "Valor devolução": "valor_devolucao",
        "Valor outros gastos": "valor_outros_gastos",
    },
    "raw_passagem": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Meio de transporte": "meio_transporte",
        "País - Origem ida": "pais_origem_ida",
        "UF - Origem ida": "uf_origem_ida",
        "Cidade - Origem ida": "cidade_origem_ida",
        "País - Destino ida": "pais_destino_ida",
        "UF - Destino ida": "uf_destino_ida",
        "Cidade - Destino ida": "cidade_destino_ida",
        "País - Origem volta": "pais_origem_volta",
        "UF - Origem volta": "uf_origem_volta",
        "Cidade - Origem volta": "cidade_origem_volta",
        "Pais - Destino volta": "pais_destino_volta",
        "UF - Destino volta": "uf_destino_volta",
        "Cidade - Destino volta": "cidade_destino_volta",
        "Valor da passagem": "valor_passagem",
        "Taxa de serviço": "taxa_servico",
        "Data da emissão/compra": "data_emissao",
        "Hora da emissão/compra": "hora_emissao",
    },
    "raw_pagamento": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Código do órgão superior": "cod_orgao_superior",
        "Nome do órgão superior": "nome_orgao_superior",
        "Codigo do órgão pagador": "cod_orgao_pagador",
        "Nome do órgao pagador": "nome_orgao_pagador",
        "Código da unidade gestora pagadora": "cod_ug_pagadora",
        "Nome da unidade gestora pagadora": "nome_ug_pagadora",
        "Tipo de pagamento": "tipo_pagamento",
        "Valor": "valor",
    },
    "raw_trecho": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Sequência Trecho": "sequencia_trecho",
        "Origem - Data": "origem_data",
        "Origem - País": "origem_pais",
        "Origem - UF": "origem_uf",
        "Origem - Cidade": "origem_cidade",
        "Destino - Data": "destino_data",
        "Destino - País": "destino_pais",
        "Destino - UF": "destino_uf",
        "Destino - Cidade": "destino_cidade",
        "Meio de transporte": "meio_transporte",
        "Número Diárias": "numero_diarias",
        "Missao?": "missao",
    },
}


# ---------------------------------------------------------------------------
# Mapeamento: cada arquivo CSV dentro do .zip -> tabela RAW correspondente
# (o nome do CSV usa o ANO como prefixo, ex.: 2025_Viagem.csv)
# ---------------------------------------------------------------------------
ARQUIVOS = {
    "viagem":     {"csv": f"{ANO}_Viagem.csv",     "tabela_raw": "raw_viagem"},
    "pagamento":  {"csv": f"{ANO}_Pagamento.csv",  "tabela_raw": "raw_pagamento"},
    "passagem":   {"csv": f"{ANO}_Passagem.csv",   "tabela_raw": "raw_passagem"},
    "trecho":     {"csv": f"{ANO}_Trecho.csv",     "tabela_raw": "raw_trecho"},
}

# Caracteristicas dos arquivos CSV do Portal da Transparencia:
CSV_SEPARADOR = ";"
CSV_ENCODING = "latin-1"   # acentuacao no padrao ISO-8859-1
