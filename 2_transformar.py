"""
2_transformar.py
-----------------
Fase 2 do pipeline (Arquitetura Medallion): Transformação e camada Silver.
 
- Lê os dados brutos das tabelas Raw (tudo como texto).
- Converte texto -> DECIMAL (campos de valores/taxas) e texto -> DATE
  (campos de data), usando as funções de conversão abaixo.
- Calcula as colunas derivadas 'valor_total' (silver_viagem) e
  'duracao_dias' (silver_viagem).
- Carrega a camada Silver respeitando a integridade referencial: a tabela
  pai (silver_viagem) é populada antes das tabelas filhas
  (silver_passagem, silver_pagamento, silver_trecho).
- Idempotente: faz TRUNCATE (com CASCADE) em todas as tabelas Silver antes
  da carga, para que reexecuções não dupliquem registros.
- Resiliente: cada etapa é protegida por try/except.
"""
 
from datetime import datetime
 
import banco
import config
 
 
# ---------------------------------------------------------------------------
# Funções de conversão (texto -> tipo real), citadas na seção 5.6 do PDF
# ---------------------------------------------------------------------------
def texto_para_decimal(valor):
    """Converte texto no padrão brasileiro ('1.272,97') para float."""
    if valor is None or str(valor).strip() == "":
        return None
    texto = str(valor).strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None
 
 
def texto_para_data(valor):
    """Converte texto 'DD/MM/AAAA' para um objeto date."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return datetime.strptime(str(valor).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None
 
 
def texto_para_inteiro(valor):
    """Converte texto para int (usado em colunas INT, ex.: sequencia_trecho)."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return int(float(str(valor).strip()))
    except ValueError:
        return None
 
 
# ---------------------------------------------------------------------------
# ATENÇÃO: ajuste este mapeamento com os nomes REAIS das colunas das suas
# tabelas Raw (elas seguem o cabeçalho original do CSV, que não temos aqui).
# A chave é a coluna em raw_*, o valor é a coluna correspondente em silver_*.
# ---------------------------------------------------------------------------
MAPEAMENTO_VIAGEM = {
    "id_viagem": "id_viagem",
    "num_proposta": "num_proposta",
    "situacao": "situacao",
    "viagem_urgente": "viagem_urgente",
    "cod_orgao_superior": "cod_orgao_superior",
    "nome_orgao_superior": "nome_orgao_superior",
    "nome_viajante": "nome_viajante",
    "cargo": "cargo",
    "data_inicio": "data_inicio",
    "data_fim": "data_fim",
    "destinos": "destinos",
    "motivo": "motivo",
    "valor_diarias": "valor_diarias",
    "valor_passagens": "valor_passagens",
    "valor_devolucao": "valor_devolucao",
    "valor_outros_gastos": "valor_outros_gastos",
}
 
MAPEAMENTO_PASSAGEM = {
    "id_viagem": "id_viagem",
    "meio_transporte": "meio_transporte",
    "pais_origem_ida": "pais_origem_ida",
    "uf_origem_ida": "uf_origem_ida",
    "cidade_origem_ida": "cidade_origem_ida",
    "pais_destino_ida": "pais_destino_ida",
    "uf_destino_ida": "uf_destino_ida",
    "cidade_destino_ida": "cidade_destino_ida",
    "valor_passagem": "valor_passagem",
    "taxa_servico": "taxa_servico",
    "data_emissao": "data_emissao",
}
 
MAPEAMENTO_PAGAMENTO = {
    "id_viagem": "id_viagem",
    "num_proposta": "num_proposta",
    "nome_orgao_pagador": "nome_orgao_pagador",
    "nome_ug_pagadora": "nome_ug_pagadora",
    "tipo_pagamento": "tipo_pagamento",
    "valor": "valor",
}
 
MAPEAMENTO_TRECHO = {
    "id_viagem": "id_viagem",
    "sequencia_trecho": "sequencia_trecho",
    "origem_data": "origem_data",
    "origem_uf": "origem_uf",
    "origem_cidade": "origem_cidade",
    "destino_data": "destino_data",
    "destino_uf": "destino_uf",
    "destino_cidade": "destino_cidade",
    "meio_transporte": "meio_transporte",
    "numero_diarias": "numero_diarias",
}
 
# Colunas de cada tabela Silver que recebem conversão texto -> DECIMAL / DATE / INT
COLUNAS_DECIMAL = {
    "silver_viagem": ["valor_diarias", "valor_passagens", "valor_devolucao", "valor_outros_gastos"],
    "silver_passagem": ["valor_passagem", "taxa_servico"],
    "silver_pagamento": ["valor"],
    "silver_trecho": ["numero_diarias"],
}
COLUNAS_DATA = {
    "silver_viagem": ["data_inicio", "data_fim"],
    "silver_passagem": ["data_emissao"],
    "silver_pagamento": [],
    "silver_trecho": ["origem_data", "destino_data"],
}
COLUNAS_INTEIRO = {
    "silver_viagem": [],
    "silver_passagem": [],
    "silver_pagamento": [],
    "silver_trecho": ["sequencia_trecho"],
}
 
 
# ---------------------------------------------------------------------------
# Leitura da Raw em blocos (evita carregar a tabela inteira na memória)
# ---------------------------------------------------------------------------
def buscar_em_lotes(conexao, sql_select, tamanho_bloco):
    """Gera blocos (listas de tuplas) a partir de um SELECT, sem esgotar a memória."""
    cursor = conexao.cursor()
    cursor.execute(sql_select)
    try:
        while True:
            bloco = cursor.fetchmany(tamanho_bloco)
            if not bloco:
                break
            yield bloco
    finally:
        cursor.close()
 
 
def transformar_linha(linha, colunas_raw, mapeamento, tabela_silver):
    """Converte uma linha bruta (tupla) num dicionário já tipado para a Silver."""
    bruto = dict(zip(colunas_raw, linha))
    registro = {}
 
    for col_raw, col_silver in mapeamento.items():
        valor = bruto.get(col_raw)
 
        if col_silver in COLUNAS_DECIMAL.get(tabela_silver, []):
            valor = texto_para_decimal(valor)
        elif col_silver in COLUNAS_DATA.get(tabela_silver, []):
            valor = texto_para_data(valor)
        elif col_silver in COLUNAS_INTEIRO.get(tabela_silver, []):
            valor = texto_para_inteiro(valor)
 
        registro[col_silver] = valor
 
    return registro
 
 
def inserir_registros(conexao, tabela, registros):
    """Monta o INSERT dinamicamente a partir das chaves do dicionário e insere em lote."""
    if not registros:
        return
 
    colunas = list(registros[0].keys())
    tabela_qualificada = f"{config.SILVER_SCHEMA}.{tabela}"
    sql_insert = (
        f"INSERT INTO {tabela_qualificada} ({', '.join(colunas)}) "
        f"VALUES ({', '.join(['%s'] * len(colunas))})"
    )
    linhas = [tuple(registro[c] for c in colunas) for registro in registros]
    banco.inserir_em_lote(conexao, sql_insert, linhas)
 
 
# ---------------------------------------------------------------------------
# Truncamento idempotente de toda a camada Silver
# ---------------------------------------------------------------------------
def truncar_silver(conexao):
    """
    Esvazia as 4 tabelas Silver antes da carga. O CASCADE evita erro de FK
    ao truncar a tabela pai (silver_viagem) enquanto as filhas ainda têm dados.
    """
    schema = config.SILVER_SCHEMA
    banco.executar(
        conexao,
        f"TRUNCATE TABLE {schema}.silver_viagem, {schema}.silver_passagem, "
        f"{schema}.silver_pagamento, {schema}.silver_trecho RESTART IDENTITY CASCADE;",
    )
    print("Camada Silver truncada (silver_viagem, silver_passagem, "
          "silver_pagamento, silver_trecho).")
 
 
# ---------------------------------------------------------------------------
# silver_viagem (tabela pai — precisa ser carregada primeiro)
# ---------------------------------------------------------------------------
def transformar_viagem(conexao):
    colunas_raw = list(MAPEAMENTO_VIAGEM.keys())
    sql_select = f"SELECT {', '.join(colunas_raw)} FROM {config.RAW_SCHEMA}.raw_viagem"
 
    total = 0
    for bloco in buscar_em_lotes(conexao, sql_select, config.TAMANHO_BLOCO):
        registros = []
        for linha in bloco:
            registro = transformar_linha(linha, colunas_raw, MAPEAMENTO_VIAGEM, "silver_viagem")
 
            # --- colunas calculadas ---
            diarias = registro.get("valor_diarias") or 0
            passagens = registro.get("valor_passagens") or 0
            devolucao = registro.get("valor_devolucao") or 0
            outros = registro.get("valor_outros_gastos") or 0
            registro["valor_total"] = diarias + passagens - devolucao + outros
 
            data_inicio = registro.get("data_inicio")
            data_fim = registro.get("data_fim")
            if data_inicio and data_fim:
                registro["duracao_dias"] = (data_fim - data_inicio).days + 1
            else:
                registro["duracao_dias"] = None
 
            registros.append(registro)
 
        inserir_registros(conexao, "silver_viagem", registros)
        total += len(registros)
 
    print(f"'silver_viagem' carregada com {total} linhas.")
 
 
# ---------------------------------------------------------------------------
# Tabelas filhas (dependem da silver_viagem já estar populada)
# ---------------------------------------------------------------------------
def transformar_tabela_filha(conexao, tabela_raw, tabela_silver, mapeamento):
    colunas_raw = list(mapeamento.keys())
    sql_select = f"SELECT {', '.join(colunas_raw)} FROM {config.RAW_SCHEMA}.{tabela_raw}"
 
    total = 0
    for bloco in buscar_em_lotes(conexao, sql_select, config.TAMANHO_BLOCO):
        registros = [
            transformar_linha(linha, colunas_raw, mapeamento, tabela_silver)
            for linha in bloco
        ]
        inserir_registros(conexao, tabela_silver, registros)
        total += len(registros)
 
    print(f"'{tabela_silver}' carregada com {total} linhas.")
 
 
# ---------------------------------------------------------------------------
# Orquestração da Fase 2
# ---------------------------------------------------------------------------
def transformar_e_carregar():
    try:
        conexao = banco.conectar()
    except RuntimeError as erro:
        print(erro)
        return
 
    try:
        truncar_silver(conexao)
 
        # silver_viagem primeiro (tabela pai / integridade referencial).
        try:
            transformar_viagem(conexao)
        except Exception as erro:
            print(f"Erro ao transformar 'raw_viagem' -> 'silver_viagem': {erro}")
            conexao.rollback()
            return  # sem silver_viagem populada, as tabelas filhas não têm o que referenciar.
 
        # depois as tabelas filhas, cada uma com try/except isolado.
        tarefas = [
            ("raw_passagem", "silver_passagem", MAPEAMENTO_PASSAGEM),
            ("raw_pagamento", "silver_pagamento", MAPEAMENTO_PAGAMENTO),
            ("raw_trecho", "silver_trecho", MAPEAMENTO_TRECHO),
        ]
        for tabela_raw, tabela_silver, mapeamento in tarefas:
            try:
                transformar_tabela_filha(conexao, tabela_raw, tabela_silver, mapeamento)
            except Exception as erro:
                print(f"Erro ao transformar '{tabela_raw}' -> '{tabela_silver}': {erro}")
                conexao.rollback()  # libera a conexão para a próxima tabela
 
    except Exception as erro:
        print(f"Erro inesperado na transformação: {erro}")
    finally:
        conexao.close()
        print("Conexão com o PostgreSQL encerrada.")
 
 
if __name__ == "__main__":
    transformar_e_carregar()