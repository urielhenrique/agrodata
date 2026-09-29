"""Script para executar a análise sobre o Parquet real."""

from __future__ import annotations

import pandas as pd

from agrodata.pipelines.ibge.analysis import (
    calcular_estatisticas,
    contar_municipios_por_produto_variavel,
    listar_produtos,
    listar_variaveis,
    ranking_municipios,
    verificar_duplicidades,
    verificar_unidades,
)

# Load real data
df = pd.read_parquet("data/processed/ibge/pam/pam_5457_2023_mg_soja_milho.parquet")
print("Dataset carregado:", df.shape)
print()

# 1. Variaveis
print("=== VARIAVEIS ===")
variaveis = listar_variaveis(df)
for v in variaveis:
    print(f"  {v['id']}: {v['nome']} ({v['unidade']})")
print()

# 2. Produtos
print("=== PRODUTOS ===")
produtos = listar_produtos(df)
for p in produtos:
    print(f"  {p['codigo']}: {p['nome']}")
print()

# 3. Municipios por produto x variavel
print("=== MUNICIPIOS POR PRODUTO x VARIAVEL ===")
contagem = contar_municipios_por_produto_variavel(df)
print(contagem.to_string(index=False))
print()

# 4. Estatisticas
print("=== ESTATISTICAS POR PRODUTO x VARIAVEL ===")
stats = calcular_estatisticas(df)
for s in stats:
    print(f"  {s.variavel_nome} / {s.categoria_nome}:")
    print(f"    Validos: {s.registros_validos}, Ausentes: {s.registros_ausentes}")
    print(f"    Min: {s.minimo:.2f}, Max: {s.maximo:.2f}")
    print(f"    Media: {s.media:.2f}, Mediana: {s.mediana:.2f}")
    print()

# 5. Rankings
print("=== RANKINGS (Top 10 maiores) ===")
for s in stats:
    if s.registros_validos > 0:
        ranking = ranking_municipios(df, s.variavel_id, s.categoria_codigo, n=10)
        print(f"  {s.variavel_nome} / {s.categoria_nome}:")
        for i, r in enumerate(ranking.maiores, 1):
            print(f"    {i}. {r.localidade_nome}: {r.valor_numerico:.2f}")
        print()

print("=== RANKINGS (Top 10 menores) ===")
for s in stats:
    if s.registros_validos > 0:
        ranking = ranking_municipios(df, s.variavel_id, s.categoria_codigo, n=10)
        print(f"  {s.variavel_nome} / {s.categoria_nome}:")
        for i, r in enumerate(ranking.menores, 1):
            print(f"    {i}. {r.localidade_nome}: {r.valor_numerico:.2f}")
        print()

# 6. Unidades
print("=== UNIDADES POR VARIAVEL ===")
unidades = verificar_unidades(df)
for u in unidades:
    status = "OK" if u.consistente else "INCONSISTENTE"
    print(f"  {u.variavel_id}: {u.unidades_encontradas} [{status}]")
print()

# 7. Duplicidades
print("=== DUPLICIDADES ===")
duplicatas = verificar_duplicidades(df)
print(f"  Total duplicatas: {duplicatas}")
