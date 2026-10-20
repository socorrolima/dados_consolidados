# Painel SUAS — piloto BA/PE/RN

Dashboard de indicadores de assistência social (SUAS) para gestores
municipais, com dados do MDS (API SAGI). Piloto cobrindo Bahia,
Pernambuco e Rio Grande do Norte (769 municípios) antes de expandir
para o Nordeste inteiro.

## Stack

Flask + SQLAlchemy + Alembic · PostgreSQL (produção, via Supabase) /
SQLite (dev e CI) · Supabase Auth (JWKS) · GitHub Actions · JS vanilla +
Chart.js no front.

## Setup local

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; source .venv/bin/activate no Linux/Mac
pip install -r requirements-dev.txt
cp .env.example .env          # preencha DATABASE_URL/SECRET_KEY/SUPABASE_*
alembic upgrade head
python -m scripts.seed_municipios
python -m scripts.seed_indicadores
```

Rodar os testes: `pytest`. Lint/formatação: `ruff check .` e `black .`.

Subir o servidor de dev: `python wsgi.py` (lê `.env` automaticamente via
`python-dotenv`; porta configurável por `PORT`, padrão 5000).

## Configurando o Supabase

O app precisa de um projeto Supabase pra autenticação (`SUPABASE_URL` e
`SUPABASE_ANON_KEY` no `.env`):

1. Crie um projeto em [supabase.com](https://supabase.com) (gratuito).
2. Em **Settings > API**, copie a **Project URL** (`SUPABASE_URL`) e a
   chave **anon/public** (`SUPABASE_ANON_KEY`) — essa chave é pública por
   design, não é segredo; quem protege o dado é a verificação do JWT no
   backend (`app/services/auth_service.py`), não o sigilo dela.
3. Confirme que o projeto usa chaves de assinatura assimétricas (JWKS) —
   é o padrão pra projeto novo desde 2025; o backend não suporta o modo
   antigo de segredo compartilhado (HS256).
4. Em **Authentication > Users**, crie manualmente o primeiro usuário
   (e-mail/senha) de cada gestor. Não há auto-cadastro — o universo de
   gestores é pequeno e conhecido.
5. Copie o UUID do usuário criado e rode `scripts.create_admin_user`
   (abaixo) pra vincular o papel e o(s) município(s) dele — sem isso, o
   login funciona mas a API devolve 403 (autenticado, sem cadastro de
   negócio).

## Operação

### Rodar a ingestão manualmente

```bash
python -m ingestion.run_ingestion --dataset misocial --uf BA,PE,RN --competencia latest
python -m ingestion.run_ingestion --dataset misocial_mes_estado --uf BA,PE,RN --competencia 202509
python -m ingestion.run_ingestion --dataset misocial_mes_equipamento --uf BA,PE,RN --competencia latest
```

`--competencia` aceita `AAAAMM` exato ou `latest` (mês corrente). É
idempotente: reexecutar a mesma competência atualiza em vez de duplicar.
O cron do `ingest.yml` já roda os três datasets diariamente; use o
`workflow_dispatch` manual no GitHub Actions pra backfill de um mês
específico.

### Revisar o histórico de ingestões

```bash
python -m scripts.relatorio_ingestoes              # últimas 20 execuções
python -m scripts.relatorio_ingestoes --so-falhas   # só as que falharam
```

### Provisionar um gestor novo

Depois de criar a conta no painel da Supabase (passo 4 acima):

```bash
python -m scripts.create_admin_user \
  --id <uuid-do-usuario-no-supabase> \
  --email gestora@municipio.ba.gov.br \
  --nome "Nome da Gestora" \
  --municipio-ibge 2927408
```

`--municipio-ibge` aceita o código de 7 dígitos do IBGE (repita a flag
para vincular mais de um município) e `--papel admin` cria um admin
(vê qualquer município, sem precisar de `--municipio-ibge`).

## Arquitetura (resumo)

- `app/routes` → `app/services` → `app/repositories`: rota nunca tem SQL
  nem cálculo direto.
- `ingestion/`: pipeline batch (sagi_client, normalizers, validators,
  loader, `datasets/*`), separado do `app/` porque não depende de
  request/response Flask.
- `scripts/`: CLIs de operação (seed, provisionamento, relatório).
- 3 tabelas fato por granularidade real da API (`fato_indicador_municipio_mes`,
  `fato_indicador_estado_mes`, `fato_indicador_municipio_ano` — essa
  última ainda sem nenhum indicador cadastrado), catalogadas em
  `dim_indicador`.

## O que está fora do escopo do piloto (documentado, não esquecido)

- **CadÚnico, SICON**: não catalogados — formato não confirmado contra a
  API real ainda.
- **CNEAS detalhado**: só contagem agregada de entidades por
  município/mês (`misocial_mes_equipamento.cneas_qtd_entidades_cadastradas`).
  O recurso real é um registro por entidade (CNPJ, razão social,
  endereço) — decisão consciente de não guardar esse detalhe por
  enquanto (ver `scripts/seed_indicadores.py`).
- **Dezenas de campos de `misocial_mes_estado`** fora do catálogo
  (Academia do Futebol, Alimenta Brasil, Brasil Fraterno, CEBAS,
  variantes do ADA por tipo de família) — mesmo motivo: só catalogamos o
  que foi confirmado e aprovado explicitamente.
- **Expansão pro Nordeste inteiro**: a média "Brasil" já usa as 27 UFs
  (indicadores `estado_mes`), mas indicadores `municipio_mes` (SUASWEB,
  CNEAS) só têm BA/PE/RN — expandir exige reingerir município/mês pros
  outros 6 estados.

## Checklist antes de liberar pros ~768 municípios

- [ ] Projeto Supabase criado e configurado (`SUPABASE_URL`/`SUPABASE_ANON_KEY`
      em produção, não só local).
- [ ] `DATABASE_URL`/`SECRET_KEY` de produção configurados como secret no
      GitHub Actions (`ingest.yml`) e no host da aplicação.
- [ ] Ao menos um gestor de cada estado provisionado e testado (login +
      dashboard carregando dado real).
- [ ] Rodar `python -m scripts.relatorio_ingestoes` e confirmar 0 falhas
      recentes antes do anúncio de lançamento.
- [ ] CI (`ci.yml`) obrigatório antes de merge — branch protection ainda
      não configurada em Settings > Branches (ver observação abaixo).
- [ ] Revisar se o volume de `ingestao_execucao` acumulado não está
      crescendo sem limite (sem rotina de limpeza nesta fase).

### Sobre CI obrigatório em PR

Repositório: https://github.com/socorrolima/dados_consolidados (privado).
"CI obrigatório" (branch protection exigindo os checks do `ci.yml` antes
de merge) ainda falta configurar em Settings > Branches do repositório —
é uma configuração do GitHub, não deste código.
