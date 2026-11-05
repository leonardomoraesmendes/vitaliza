"""Clusterização dos pagantes ativos no corte (30/09/2026) — objetivo 3 do case.

Entrada: dados/processados/s5_john/base_clusterizacao.csv e base_assinantes_corte.csv,
geradas por src/preparar_diagnostico_s5.py a partir de dados/brutos/.

Saídas (fora do Git, em dados/):
- dados/processados/s5_leo/segmentos.csv: user_id, segmento e variáveis transformadas
- dados/saidas/s5_leo/*.csv: varredura de k, estabilidade, perfil e ponte de linhas

Uso: .venv/bin/python src/clusterizacao_s5.py [--k 4]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
ENTRADA = ROOT / "dados/processados/s5_john"
PROCESSADOS = ROOT / "dados/processados/s5_leo"
SAIDAS = ROOT / "dados/saidas/s5_leo"
SEMENTE = 42
CORTE = pd.Timestamp("2026-09-30")
# Quem não treinou em 2026 tem recência de pelo menos (corte − 01/01/2026); usamos esse limite inferior.
RECENCIA_SEM_TREINO_2026 = (CORTE - pd.Timestamp("2026-01-01")).days + 1  # 273 dias

# Uma variável por dimensão de comportamento. Volume (treinos/minutos/dias, 30d/90d) tem
# Spearman 0,80–0,99 entre si: só dias ativos entra. seguindo ~ seguidores (0,79): só seguidores.
# Contagens em janela de 90 dias viram taxa pela exposição: quem tem conta há menos de 90 dias
# não teve como acumular a janela inteira. Exposição = min(90, tempo_cadastro + 1), porque treino
# é grátis antes da assinatura (7 dias de teste) e o dia do cadastro também conta como data.
VARIAVEIS = {
    "taxa_dias_ativos_90d": "frequência",
    "min_por_treino_90d": "intensidade",
    "recencia_dias": "recência",
    "variacao_treinos_30d": "tendência",
    "proporcao_video_90d": "modalidade",
    "posts_por_90d": "social (produção)",
    "seguidores_corte": "social (rede)",
    "tempo_assinatura_dias": "tempo de casa",
}
LOG = ["min_por_treino_90d", "recencia_dias", "posts_por_90d", "seguidores_corte", "tempo_assinatura_dias"]
JANELA_TENDENCIA = 60  # últimos 30 dias contra os 30 anteriores


def carregar() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = pd.read_csv(ENTRADA / "base_clusterizacao.csv")
    contexto = pd.read_csv(ENTRADA / "base_assinantes_corte.csv")
    assert base.user_id.is_unique and contexto.user_id.is_unique
    assert set(base.user_id) == set(contexto.user_id)
    return base, contexto


def preparar(base: pd.DataFrame, contexto: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Variáveis na escala original (para descrever) e transformadas (para agrupar)."""
    log_decisoes = []
    base = base.merge(contexto[["user_id", "tempo_cadastro_dias"]], on="user_id", validate="1:1")
    assert base.tempo_cadastro_dias.notna().all()
    exposicao = (base.tempo_cadastro_dias + 1).clip(upper=90)
    assert (base.dias_ativos_90d <= exposicao).all(), "dias ativos acima da exposição"

    f = pd.DataFrame({"user_id": base.user_id})
    f["taxa_dias_ativos_90d"] = base.dias_ativos_90d / exposicao
    f["min_por_treino_90d"] = base.minutos_90d / base.treinos_90d.where(base.treinos_90d > 0)
    f["recencia_dias"] = base.dias_desde_ultimo_treino_2026
    f["variacao_treinos_30d"] = base.variacao_treinos_tratados_30d
    f["proporcao_video_90d"] = base.proporcao_video_90d
    f["posts_por_90d"] = base.posts_90d / exposicao * 90
    f["seguidores_corte"] = base.seguidores_corte
    f["tempo_assinatura_dias"] = base.tempo_assinatura_dias
    # Escala original, só para descrever os segmentos.
    f["dias_ativos_90d"] = base.dias_ativos_90d
    f["posts_90d"] = base.posts_90d
    f["exposicao_dias"] = exposicao
    f["tendencia_incompleta"] = (base.tempo_cadastro_dias + 1 < JANELA_TENDENCIA).astype(int)
    f["sem_treino_90d"] = (base.treinos_90d == 0).astype(int)
    f["sem_treino_2026"] = base.sem_treino_observado_2026
    for c, regra in [("taxa_dias_ativos_90d", "dias ativos / min(90, cadastro + 1)"),
                     ("posts_por_90d", "posts_90d / min(90, cadastro + 1) × 90")]:
        log_decisoes.append({"variavel": c, "regra": f"taxa por exposição: {regra}", "linhas": int((exposicao < 90).sum())})

    x = f[list(VARIAVEIS)].copy()
    # Com menos de 60 dias de conta, a janela anterior está incompleta e a variação sai positiva
    # por construção. Tendência fica neutra (0 = sem informação) para essas contas.
    n = int(f.tendencia_incompleta.sum())
    x.loc[f.tendencia_incompleta.eq(1), "variacao_treinos_30d"] = 0
    log_decisoes.append({"variavel": "variacao_treinos_30d", "regra": "conta com menos de 60 dias: neutra (0), janela anterior incompleta", "linhas": n})
    n = x.recencia_dias.isna().sum()
    x["recencia_dias"] = x.recencia_dias.fillna(RECENCIA_SEM_TREINO_2026)
    log_decisoes.append({"variavel": "recencia_dias", "regra": f"ausente (sem treino em 2026) = {RECENCIA_SEM_TREINO_2026} dias, limite inferior", "linhas": int(n)})
    for c in ["min_por_treino_90d", "proporcao_video_90d"]:
        n, med = x[c].isna().sum(), x[c].median()
        x[c] = x[c].fillna(med)
        log_decisoes.append({"variavel": c, "regra": f"ausente (zero treino em 90d) = mediana {med:.3f}, valor neutro", "linhas": int(n)})
    for c in LOG:
        x[c] = np.log1p(x[c])
    for c in x:
        lo, hi = x[c].quantile([.01, .99])
        n = int(((x[c] < lo) | (x[c] > hi)).sum())
        x[c] = x[c].clip(lo, hi)
        log_decisoes.append({"variavel": c, "regra": f"corte nos percentis 1 e 99{' após log1p' if c in LOG else ''}", "linhas": n})
    assert not x.isna().any().any()
    return f, x, log_decisoes


def padronizar(x: pd.DataFrame) -> np.ndarray:
    return StandardScaler().fit_transform(x)


def varrer_k(z: np.ndarray, ks=range(2, 9), reamostras=20) -> pd.DataFrame:
    """Para cada k: inércia, silhueta, Calinski-Harabasz e estabilidade (ARI médio).

    Estabilidade: ajusta o K-means em 80% da base sorteada, rotula a base toda e compara
    com o rótulo do ajuste completo. ARI = 1 é partição idêntica; ~0 é acaso.
    """
    rng = np.random.default_rng(SEMENTE)
    amostra_sil = rng.choice(len(z), size=min(5000, len(z)), replace=False)
    linhas = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEMENTE).fit(z)
        aris = []
        for _ in range(reamostras):
            idx = rng.choice(len(z), size=int(.8 * len(z)), replace=False)
            sub = KMeans(n_clusters=k, n_init=10, random_state=int(rng.integers(1e9))).fit(z[idx])
            aris.append(adjusted_rand_score(km.labels_, sub.predict(z)))
        tamanhos = np.bincount(km.labels_)
        linhas.append({
            "k": k, "inercia": km.inertia_,
            "silhueta": silhouette_score(z[amostra_sil], km.labels_[amostra_sil]),
            "calinski_harabasz": calinski_harabasz_score(z, km.labels_),
            "ari_medio": np.mean(aris), "ari_min": np.min(aris),
            "menor_grupo_pct": tamanhos.min() / len(z) * 100,
        })
    return pd.DataFrame(linhas)


def ajustar(z: np.ndarray, k: int) -> np.ndarray:
    return KMeans(n_clusters=k, n_init=50, random_state=SEMENTE).fit_predict(z)


def comparar_ward(z: np.ndarray, rotulos: np.ndarray, k: int, n=6000) -> float:
    """Concordância (ARI) entre K-means e hierárquico de Ward numa amostra."""
    idx = np.random.default_rng(SEMENTE).choice(len(z), size=min(n, len(z)), replace=False)
    ward = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(z[idx])
    return adjusted_rand_score(rotulos[idx], ward)


def perfil(f: pd.DataFrame, contexto: pd.DataFrame, rotulos: np.ndarray) -> pd.DataFrame:
    """Tabela comparativa na escala original. Plano, canal, receita e renovação só descrevem."""
    d = f.assign(segmento=rotulos).merge(contexto[[
        "user_id", "plano", "canal_cobranca", "nivel", "dias_planejados_semana", "tickets_90d",
        "renovacao_desligada_retrato", "receita_liquida_mensal_equivalente_proxy"]], on="user_id", validate="1:1")
    g = d.groupby("segmento")
    t = pd.DataFrame({
        "assinantes": g.size(),
        "pct_base": g.size() / len(d) * 100,
        "taxa_dias_ativos_90d_mediana": g.taxa_dias_ativos_90d.median(),
        "dias_ativos_90d_mediana": g.dias_ativos_90d.median(),
        "exposicao_dias_mediana": g.exposicao_dias.median(),
        "min_por_treino_mediana": g.min_por_treino_90d.median(),
        "recencia_dias_mediana": g.recencia_dias.median(),
        "variacao_treinos_30d_media_comparavel": d[d.tendencia_incompleta.eq(0)].groupby("segmento").variacao_treinos_30d.mean(),
        "tendencia_incompleta_pct": g.tendencia_incompleta.mean() * 100,
        "proporcao_video_mediana": g.proporcao_video_90d.median(),
        "posts_por_90d_media": g.posts_por_90d.mean(),
        "seguidores_media": g.seguidores_corte.mean(),
        "tempo_assinatura_dias_mediana": g.tempo_assinatura_dias.median(),
        "sem_treino_90d_pct": g.sem_treino_90d.mean() * 100,
        "anual_pct": g.plano.apply(lambda s: s.eq("anual").mean() * 100),
        "lojas_pct": g.canal_cobranca.apply(lambda s: s.isin(["app_store", "google_play"]).mean() * 100),
        "nivel_iniciante_pct": g.nivel.apply(lambda s: s.eq("iniciante").mean() * 100),
        "dias_planejados_mediana": g.dias_planejados_semana.median(),
        "tickets_90d_pct_com": g.tickets_90d.apply(lambda s: s.gt(0).mean() * 100),
        "renovacao_desligada_pct": g.renovacao_desligada_retrato.mean() * 100,
        "receita_liquida_mensal_total": g.receita_liquida_mensal_equivalente_proxy.sum(),
        "receita_liquida_mensal_media": g.receita_liquida_mensal_equivalente_proxy.mean(),
    })
    return t, d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=None, help="número de segmentos; sem valor, só faz a varredura")
    args = ap.parse_args()
    PROCESSADOS.mkdir(parents=True, exist_ok=True)
    SAIDAS.mkdir(parents=True, exist_ok=True)

    base, contexto = carregar()
    ponte = [{"etapa": "base_clusterizacao.csv (pagantes no corte, sem contas de teste)", "linhas": len(base)}]
    f, x, decisoes = preparar(base, contexto)
    ponte.append({"etapa": "após tratamento de ausências e escala (nenhuma linha removida)", "linhas": len(x)})
    z = padronizar(x)

    varredura = varrer_k(z, ks=[args.k] if args.k else range(2, 9))
    varredura.to_csv(SAIDAS / "varredura_k.csv", index=False)
    pd.DataFrame(decisoes).to_csv(SAIDAS / "tratamentos_variaveis.csv", index=False)
    print(varredura.round(3).to_string(index=False))
    if args.k is None:
        return

    rotulos = ajustar(z, args.k)
    # Ordena segmentos pela taxa de dias ativos (0 = menos ativo) para os rótulos serem estáveis entre execuções.
    ordem = pd.Series(f.taxa_dias_ativos_90d.values).groupby(rotulos).mean().sort_values().index
    rotulos = pd.Series(rotulos).map({old: new for new, old in enumerate(ordem)}).to_numpy()

    tabela, detalhado = perfil(f, contexto, rotulos)
    ponte.append({"etapa": f"atribuídos a um dos {args.k} segmentos", "linhas": int(tabela.assinantes.sum())})
    assert tabela.assinantes.sum() == len(base) == 14753

    ward = comparar_ward(z, rotulos, args.k)
    centros_z = pd.DataFrame(z, columns=list(VARIAVEIS)).groupby(rotulos).mean()

    tabela.to_csv(SAIDAS / "perfil_segmentos.csv")
    centros_z.to_csv(SAIDAS / "centros_padronizados.csv")
    pd.DataFrame(ponte).to_csv(SAIDAS / "ponte_linhas.csv", index=False)
    detalhado.to_csv(PROCESSADOS / "segmentos.csv", index=False)
    resumo = {"k": args.k, "ari_kmeans_vs_ward": round(ward, 3),
              **varredura.set_index("k").loc[args.k].round(3).to_dict()}
    (SAIDAS / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False))
    pd.set_option("display.width", 250)
    print("\n", pd.DataFrame(ponte).to_string(index=False))
    print("\ncentros (z):\n", centros_z.round(2).to_string())
    print("\nperfil:\n", tabela.round(1).T.to_string())
    print("\n", resumo)


if __name__ == "__main__":
    main()
