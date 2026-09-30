"""Script de validação de performance do MVP1."""

from __future__ import annotations

import statistics
import time
from typing import Any

import httpx

API_BASE = "http://127.0.0.1:8000/api"


def medir_tempo(funcao, *args, **kwargs) -> tuple[Any, float]:
    """Mede tempo de execução de uma função."""
    inicio = time.perf_counter()
    resultado = funcao(*args, **kwargs)
    fim = time.perf_counter()
    return resultado, fim - inicio


def testar_api_geojson():
    """Testa performance da API /api/map/geojson."""
    print("\n" + "=" * 60)
    print("TESTE A: API /api/map/geojson")
    print("=" * 60)

    resultados = {
        "cache_miss": [],
        "cache_hit": [],
        "features": 0,
        "tamanho_mb": 0,
    }

    # Teste 1: Cache MISS (primeira chamada após restart)
    print("\n1. Cache MISS (cultura=Todos, indicador=Produção, periodo=2023)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Todos", "periodo": "2023", "indicador": "Produção"},
        )
    resp.raise_for_status()
    data = resp.json()
    resultados["cache_miss"].append(tempo)
    resultados["features"] = len(data.get("features", []))
    resultados["tamanho_mb"] = len(resp.content) / (1024 * 1024)
    print(f"   Tempo: {tempo:.3f}s")
    print(f"   Features: {resultados['features']}")
    print(f"   Tamanho: {resultados['tamanho_mb']:.2f} MB")

    # Teste 2: Cache HIT (segunda chamada mesma query)
    print("\n2. Cache HIT (mesma query)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Todos", "periodo": "2023", "indicador": "Produção"},
        )
    resp.raise_for_status()
    resultados["cache_hit"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")

    # Teste 3: Cache MISS - mudança de cultura
    print("\n3. Cache MISS (mudança cultura: Todos -> Milho)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Milho", "periodo": "2023", "indicador": "Produção"},
        )
    resp.raise_for_status()
    data = resp.json()
    resultados["cache_miss"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")
    print(f"   Features: {len(data.get('features', []))}")

    # Teste 4: Cache HIT - cultura Milho
    print("\n4. Cache HIT (cultura=Milho)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Milho", "periodo": "2023", "indicador": "Produção"},
        )
    resp.raise_for_status()
    resultados["cache_hit"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")

    # Teste 5: Cache MISS - mudança indicador
    print("\n5. Cache MISS (mudança indicador: Produção -> Área)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Milho", "periodo": "2023", "indicador": "Área"},
        )
    resp.raise_for_status()
    data = resp.json()
    resultados["cache_miss"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")
    print(f"   Features: {len(data.get('features', []))}")

    # Teste 6: Cache HIT - indicador Área
    print("\n6. Cache HIT (indicador=Área)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Milho", "periodo": "2023", "indicador": "Área"},
        )
    resp.raise_for_status()
    resultados["cache_hit"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")

    # Teste 7: Cache MISS - mudança indicador para Produtividade
    print("\n7. Cache MISS (mudança indicador: Área -> Produtividade)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Milho", "periodo": "2023", "indicador": "Produtividade"},
        )
    resp.raise_for_status()
    data = resp.json()
    resultados["cache_miss"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")
    print(f"   Features: {len(data.get('features', []))}")

    # Teste 8: Cache HIT - indicador Produtividade
    print("\n8. Cache HIT (indicador=Produtividade)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Milho", "periodo": "2023", "indicador": "Produtividade"},
        )
    resp.raise_for_status()
    resultados["cache_hit"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")

    # Teste 9: Cache MISS - mudança cultura para Soja
    print("\n9. Cache MISS (mudança cultura: Milho -> Soja)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Soja", "periodo": "2023", "indicador": "Produtividade"},
        )
    resp.raise_for_status()
    data = resp.json()
    resultados["cache_miss"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")
    print(f"   Features: {len(data.get('features', []))}")

    # Teste 10: Cache HIT - cultura Soja
    print("\n10. Cache HIT (cultura=Soja)")
    with httpx.Client(timeout=60.0) as client:
        resp, tempo = medir_tempo(
            client.get,
            f"{API_BASE}/map/geojson",
            params={"cultura": "Soja", "periodo": "2023", "indicador": "Produtividade"},
        )
    resp.raise_for_status()
    resultados["cache_hit"].append(tempo)
    print(f"   Tempo: {tempo:.3f}s")

    return resultados


def testar_cache_chaves():
    """Valida comportamento do cache com diferentes chaves."""
    print("\n" + "=" * 60)
    print("TESTE C: Validação de Chaves de Cache")
    print("=" * 60)

    combinacoes = [
        ("Todos", "2023", "Produção"),
        ("Todos", "2023", "Área"),
        ("Todos", "2023", "Produtividade"),
        ("Milho", "2023", "Produção"),
        ("Soja", "2023", "Produção"),
        ("Milho", "2023", "Área"),
        ("Milho", "2023", "Produtividade"),
    ]

    for i, (cultura, periodo, indicador) in enumerate(combinacoes):
        print(f"\n{i+1}. cultura={cultura}, periodo={periodo}, indicador={indicador}")

        # Primeira chamada (MISS)
        with httpx.Client(timeout=60.0) as client:
            resp1, t1 = medir_tempo(
                client.get,
                f"{API_BASE}/map/geojson",
                params={"cultura": cultura, "periodo": periodo, "indicador": indicador},
            )
        resp1.raise_for_status()

        # Segunda chamada (HIT)
        with httpx.Client(timeout=60.0) as client:
            resp2, t2 = medir_tempo(
                client.get,
                f"{API_BASE}/map/geojson",
                params={"cultura": cultura, "periodo": periodo, "indicador": indicador},
            )
        resp2.raise_for_status()

        # Verifica se conteúdo é idêntico
        conteudo_igual = resp1.content == resp2.content
        speedup = t1 / t2 if t2 > 0 else float("inf")

        print(f"   MISS: {t1:.3f}s | HIT: {t2:.3f}s | Speedup: {speedup:.1f}x | Conteúdo igual: {conteudo_igual}")

        if not conteudo_igual:
            print("   ⚠️  AVISO: Conteúdo difere entre MISS e HIT!")


def testar_fingerprint():
    """Verifica o fingerprint do dataset."""
    print("\n" + "=" * 60)
    print("TESTE: Fingerprint do Dataset")
    print("=" * 60)

    from agrodata.config import DatasetConfig

    hash1 = DatasetConfig.obter_dataset_hash()
    print(f"Hash inicial: {hash1}")

    # Verifica se o hash é baseado em mtime + tamanho
    for caminho in [DatasetConfig.PAM_INTEGRADO, DatasetConfig.MALHA_TERRITORIAL]:
        stat = caminho.stat()
        print(f"  {caminho.name}: mtime={stat.st_mtime_ns}, size={stat.st_size}")


def main():
    print("=" * 60)
    print("VALIDAÇÃO DE PERFORMANCE MVP1 - AgroData")
    print("=" * 60)

    # Testa API
    resultados_api = testar_api_geojson()

    # Valida chaves de cache
    testar_cache_chaves()

    # Verifica fingerprint
    testar_fingerprint()

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)

    miss_times = resultados_api["cache_miss"]
    hit_times = resultados_api["cache_hit"]

    print("\nAPI /api/map/geojson:")
    print(f"  Cache MISS (média): {statistics.mean(miss_times):.3f}s (min: {min(miss_times):.3f}s, max: {max(miss_times):.3f}s)")
    print(f"  Cache HIT (média):  {statistics.mean(hit_times):.3f}s (min: {min(hit_times):.3f}s, max: {max(hit_times):.3f}s)")
    if miss_times and hit_times:
        speedup = statistics.mean(miss_times) / statistics.mean(hit_times)
        print(f"  Speedup médio:      {speedup:.1f}x")

    print("\nGeoJSON:")
    print(f"  Features: {resultados_api['features']}")
    print(f"  Tamanho:  {resultados_api['tamanho_mb']:.2f} MB")

    print("\n" + "=" * 60)
    print("ANÁLISE DE GARGALOS")
    print("=" * 60)

    if statistics.mean(miss_times) > 5.0:
        print("[GARGALO] Tempo de MISS alto (>5s) - processamento geoespacial pesado")
    elif statistics.mean(miss_times) > 2.0:
        print("[ATENCAO] Tempo de MISS moderado (>2s)")
    else:
        print("[OK] Tempo de MISS aceitavel")

    if statistics.mean(hit_times) > 0.5:
        print("[GARGALO] Tempo de HIT alto (>0.5s) - serializacao/transferencia")
    elif statistics.mean(hit_times) > 0.1:
        print("[ATENCAO] Tempo de HIT moderado (>0.1s)")
    else:
        print("[OK] Tempo de HIT aceitavel")

    if resultados_api["tamanho_mb"] > 10:
        print(f"[GARGALO] Resposta grande ({resultados_api['tamanho_mb']:.1f} MB) - considerar simplificacao ou paginacao")
    elif resultados_api["tamanho_mb"] > 5:
        print(f"[ATENCAO] Resposta moderada ({resultados_api['tamanho_mb']:.1f} MB)")
    else:
        print(f"[OK] Tamanho de resposta aceitavel ({resultados_api['tamanho_mb']:.1f} MB)")

    print("\n" + "=" * 60)
    print("DOCUMENTACAO - Correcoes necessarias:")
    print("=" * 60)
    print("1. Tolerancia de simplificacao: 0.0005 graus (nao 0.005)")
    print("2. Cache evita processamento/reconstrucao geoespacial")
    print("3. Resposta HTTP ainda precisa ser serializada")
    print("4. Cache e em memoria do processo (LRU, maxsize=64)")
    print("5. Fingerprint baseado em mtime + tamanho dos arquivos Parquet")
    print("   (nao e hash criptografico do conteudo)")


if __name__ == "__main__":
    main()