-- As tabelas vivem no schema padrão 'public' (o PDF do desafio não define
-- um schema próprio para Raw/Silver — apenas os nomes raw_* e silver_*).

-- Permite reexecutar este script do zero sem erro de "tabela já existe".
-- Ordem: filhas primeiro (por causa das FOREIGN KEYs), depois as tabelas pai.
DROP TABLE IF EXISTS silver_pagamento;
DROP TABLE IF EXISTS silver_passagem;
DROP TABLE IF EXISTS silver_trecho;
DROP TABLE IF EXISTS silver_viagem;
DROP TABLE IF EXISTS raw_viagem;
DROP TABLE IF EXISTS raw_passagem;
DROP TABLE IF EXISTS raw_pagamento;
DROP TABLE IF EXISTS raw_trecho;

-- ==============================================================
-- CAMADA RAW (Cópia fiel do CSV - Tudo VARCHAR e sem restrições)
-- ==============================================================

CREATE TABLE raw_viagem (
    id_viagem VARCHAR,
    num_proposta VARCHAR,
    situacao VARCHAR,
    viagem_urgente VARCHAR,
    justificativa_urgencia VARCHAR,
    cod_orgao_superior VARCHAR,
    nome_orgao_superior VARCHAR,
    cod_orgao_solicitante VARCHAR,
    nome_orgao_solicitante VARCHAR,
    cpf_viajante VARCHAR,        -- Coluna extra do CSV original (não vai para a Silver)
    nome_viajante VARCHAR,
    cargo VARCHAR,
    funcao VARCHAR,              -- Coluna extra do CSV original (não vai para a Silver)
    descricao_funcao VARCHAR,    -- Coluna extra do CSV original (não vai para a Silver)
    data_inicio VARCHAR,
    data_fim VARCHAR,
    destinos VARCHAR,
    motivo VARCHAR,
    valor_diarias VARCHAR,
    valor_passagens VARCHAR,
    valor_devolucao VARCHAR,
    valor_outros_gastos VARCHAR
);

CREATE TABLE raw_passagem (
    id_viagem VARCHAR,
    num_proposta VARCHAR,
    meio_transporte VARCHAR,
    pais_origem_ida VARCHAR,
    uf_origem_ida VARCHAR,
    cidade_origem_ida VARCHAR,
    pais_destino_ida VARCHAR,
    uf_destino_ida VARCHAR,
    cidade_destino_ida VARCHAR,
    pais_origem_volta VARCHAR,   -- Coluna extra do CSV original (não vai para a Silver)
    uf_origem_volta VARCHAR,     -- Coluna extra do CSV original (não vai para a Silver)
    cidade_origem_volta VARCHAR, -- Coluna extra do CSV original (não vai para a Silver)
    pais_destino_volta VARCHAR,  -- Coluna extra do CSV original (não vai para a Silver)
    uf_destino_volta VARCHAR,    -- Coluna extra do CSV original (não vai para a Silver)
    cidade_destino_volta VARCHAR,-- Coluna extra do CSV original (não vai para a Silver)
    valor_passagem VARCHAR,
    taxa_servico VARCHAR,
    data_emissao VARCHAR,
    hora_emissao VARCHAR         -- Coluna extra do CSV original (não vai para a Silver)
);

CREATE TABLE raw_pagamento (
    id_viagem VARCHAR,
    num_proposta VARCHAR,
    cod_orgao_superior VARCHAR,  -- Coluna extra do CSV original (não vai para a Silver)
    nome_orgao_superior VARCHAR, -- Coluna extra do CSV original (não vai para a Silver)
    cod_orgao_pagador VARCHAR,   -- Coluna extra do CSV original (não vai para a Silver)
    nome_orgao_pagador VARCHAR,
    cod_ug_pagadora VARCHAR,     -- Coluna extra do CSV original (não vai para a Silver)
    nome_ug_pagadora VARCHAR,
    tipo_pagamento VARCHAR,
    valor VARCHAR
);

CREATE TABLE raw_trecho (
    id_viagem VARCHAR,
    num_proposta VARCHAR,
    sequencia_trecho VARCHAR,
    origem_data VARCHAR,
    origem_pais VARCHAR,         -- Coluna extra do CSV original (não vai para a Silver)
    origem_uf VARCHAR,
    origem_cidade VARCHAR,
    destino_data VARCHAR,
    destino_pais VARCHAR,        -- Coluna extra do CSV original (não vai para a Silver)
    destino_uf VARCHAR,
    destino_cidade VARCHAR,
    meio_transporte VARCHAR,
    numero_diarias VARCHAR,
    missao VARCHAR               -- Coluna extra do CSV original (não vai para a Silver)
);


-- =============================================================
-- CAMADA SILVER (Dados limpos, tipados e com as 8 Constraints)
-- =============================================================

-- TABELA 1: VIAGEM
CREATE TABLE silver_viagem (
    id_viagem VARCHAR(20) PRIMARY KEY NOT NULL,
    num_proposta VARCHAR(20),
    situacao VARCHAR(50),
    viagem_urgente VARCHAR(5),
    cod_orgao_superior VARCHAR(20),
    nome_orgao_superior VARCHAR(255) NOT NULL, -- [CONSTRAINT 1]: NOT NULL
    nome_viajante VARCHAR(255),
    cargo VARCHAR(255),
    data_inicio DATE,
    data_fim DATE,
    destinos VARCHAR(4000),
    motivo VARCHAR(4000),
    valor_diarias DECIMAL(10,2) CHECK (valor_diarias >= 0), -- [CONSTRAINT 2]: CHECK
    valor_passagens DECIMAL(10,2),
    valor_devolucao DECIMAL(10,2),
    valor_outros_gastos DECIMAL(10,2),
    valor_total DECIMAL(12,2), -- Campo calculado na Fase 2
    duracao_dias INT           -- Campo calculado na Fase 2
);

-- TABELA 2: PAGAMENTO
CREATE TABLE silver_pagamento (
    id_pagamento SERIAL PRIMARY KEY, -- SERIAL gera o AUTO_INCREMENT no PostgreSQL
    id_viagem VARCHAR(20) NOT NULL,
    num_proposta VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora VARCHAR(255),
    tipo_pagamento VARCHAR(50) NOT NULL, -- [CONSTRAINT 3]: NOT NULL
    valor DECIMAL(10,2) CHECK (valor >= 0), -- [CONSTRAINT 4]: CHECK
    CONSTRAINT fk_viagem_pagamento FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem)
);

-- TABELA 3: PASSAGEM
CREATE TABLE silver_passagem (
    id_passagem SERIAL PRIMARY KEY,
    id_viagem VARCHAR(20) NOT NULL,
    meio_transporte VARCHAR(50),
    pais_origem_ida VARCHAR(60),
    uf_origem_ida VARCHAR(40),
    cidade_origem_ida VARCHAR(80),
    pais_destino_ida VARCHAR(60),
    uf_destino_ida VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem DECIMAL(10,2) CHECK (valor_passagem >= 0), -- [CONSTRAINT 5]: CHECK
    taxa_servico DECIMAL(10,2) CHECK (taxa_servico >= 0),     -- [CONSTRAINT 6]: CHECK
    data_emissao DATE,
    CONSTRAINT fk_viagem_passagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem)
);

-- TABELA 4: TRECHO
CREATE TABLE silver_trecho (
    id_trecho SERIAL PRIMARY KEY,
    id_viagem VARCHAR(20) NOT NULL,
    sequencia_trecho INT,
    origem_data DATE,
    origem_uf VARCHAR(40),
    origem_cidade VARCHAR(80),
    destino_data DATE,
    destino_uf VARCHAR(40),
    destino_cidade VARCHAR(80),
    meio_transporte VARCHAR(50),
    numero_diarias DECIMAL(10,2) CHECK (numero_diarias >= 0), -- [CONSTRAINT 7]: CHECK
    CONSTRAINT fk_viagem_trecho FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem),
    CONSTRAINT unique_viagem_sequencia UNIQUE (id_viagem, sequencia_trecho) -- [CONSTRAINT 8]: UNIQUE
);