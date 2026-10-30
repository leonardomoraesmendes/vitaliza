"""Parte de John na S5: base analítica e diagnóstico, sem clusterizar ou prever.

Execute da raiz: .venv/bin/python src/preparar_diagnostico_s5.py
Dados individuais permanecem em dados/processados/ (ignorado no Git).
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CUT = pd.Timestamp("2026-10-01")  # limite exclusivo: inclui todo 30/09 em Brasília
LOG_START = pd.Timestamp("2024-07-01")
SEM_CONTEUDO = {"nada", "😂", ".", "x", "sla", "kkkk", "asdf", "ok", "-", "nao sei", "não sei"}
TYPE_MAP = {"run": "corrida", "walk": "caminhada", "strength": "forca", "ride": "pedal"}
VIDEO = {"forca", "funcional", "hiit", "yoga"}
FEES = {"app_store": .15, "google_play": .15, "cartao": .035, "pix_automatico": .0099}


def timestamps(s: pd.Series) -> pd.Series:
    """Datas com Z são UTC; as demais já representam Brasília, conforme dicionário."""
    raw = s.astype("string")
    utc = raw.str.endswith("Z").fillna(False)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    out.loc[utc] = pd.to_datetime(raw[utc], utc=True, errors="coerce").dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    out.loc[~utc] = pd.to_datetime(raw[~utc], format="mixed", errors="coerce")
    return out


def money_cents(s: pd.Series) -> pd.Series:
    # Decimal text is converted to integer cents, avoiding cumulative currency rounding.
    clean = s.astype("string").str.replace("R$", "", regex=False).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(clean, errors="coerce").mul(100).round().astype("Int64")


def intended_days(s: pd.Series) -> pd.Series:
    raw = s.astype("string").str.strip().str.lower().replace({"todos": "7"})
    extracted = raw.str.extract(r"^([1-7])(?:x| vezes)?$", expand=False)
    return pd.to_numeric(extracted, errors="coerce").astype("Int64")


def build_intervals(subs: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Bootstraps only subscriptions predating event coverage; later starts use events."""
    seed = subs.loc[pd.to_datetime(subs.inicio) < LOG_START, ["user_id", "inicio", "plano_atual", "canal_cobranca"]].copy()
    seed["ts"] = pd.to_datetime(seed.pop("inicio"))
    seed = seed.rename(columns={"plano_atual": "plano"})
    seed["evento"] = "assinatura_iniciada"
    changes = events.loc[events.evento.isin(["assinatura_iniciada", "assinatura_expirada"]),
                         ["user_id", "ts", "plano", "canal_cobranca", "evento"]]
    changes = pd.concat([seed, changes], ignore_index=True).sort_values(["user_id", "ts"], kind="stable")
    is_start = changes.evento.eq("assinatura_iniciada")
    previous = changes.groupby("user_id").evento.shift()
    assert not (is_start & previous.eq("assinatura_iniciada")).any(), "Inícios consecutivos: revisar reconstrução"
    assert not (~is_start & ~previous.eq("assinatura_iniciada")).any(), "Expiração sem início: revisar reconstrução"
    changes["fim_ts"] = changes.groupby("user_id").ts.shift(-1)
    result = changes[is_start].rename(columns={"ts": "inicio_ts"}).drop(columns="evento")
    assert (result.fim_ts.isna() | result.fim_ts.ge(result.inicio_ts)).all()
    return result.reset_index(drop=True)


def active_at(intervals: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    # Intervalo [início, fim): desligar renovação não encerra o período pago.
    return intervals[intervals.inicio_ts.le(date) & (intervals.fim_ts.isna() | intervals.fim_ts.gt(date))].copy()


def historical_panel(intervals: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for date in pd.date_range("2025-01-01", "2026-09-01", freq="MS"):
        end = date + pd.offsets.MonthBegin()
        frame = active_at(intervals, date)
        frame["mes"] = date.strftime("%Y-%m")
        frame["mes_anterior"] = (date - pd.offsets.MonthBegin()).strftime("%Y-%m")
        frame["saiu_mes"] = frame.fim_ts.ge(date) & frame.fim_ts.lt(end)
        frame["tempo_assinatura_dias"] = (date - frame.inicio_ts).dt.days
        frame["mes_anterior_completo"] = frame.inicio_ts.le(date - pd.offsets.MonthBegin())
        pieces.append(frame)
    panel = pd.concat(pieces, ignore_index=True)
    previous = usage[["user_id", "mes", "atividades", "minutos", "sessoes_app"]].rename(columns={
        "mes": "mes_anterior", "atividades": "atividades_mes_anterior", "minutos": "minutos_mes_anterior",
        "sessoes_app": "sessoes_mes_anterior"})
    panel = panel.merge(previous, how="left", on=["user_id", "mes_anterior"], validate="many_to_one", indicator="linha_uso")
    panel["uso_anterior_coberto"] = panel.mes_anterior.ge("2025-01")
    # Absence means no training only inside the documented observation window.
    for col in ["atividades_mes_anterior", "minutos_mes_anterior"]:
        panel.loc[panel.uso_anterior_coberto, col] = panel.loc[panel.uso_anterior_coberto, col].fillna(0)
    # 2025 did not record app openings in training-free months: preserve as missing.
    panel.loc[panel.mes_anterior.ge("2026-01"), "sessoes_mes_anterior"] = panel.loc[
        panel.mes_anterior.ge("2026-01"), "sessoes_mes_anterior"].fillna(0)
    panel["faixa_uso_anterior"] = pd.cut(panel.atividades_mes_anterior, [-1, 0, 3, 7, np.inf],
        labels=["0 treinos", "1–3 treinos", "4–7 treinos", "8+ treinos"]).astype("string")
    panel["ano"] = panel.mes.str[:4]
    return panel


def clean_activities(a: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    a = a.copy()
    a["ts"] = timestamps(a.inicio)
    garmin = a.origem.eq("garmin")
    a.loc[garmin, "ts"] -= pd.Timedelta(hours=3)
    a["tipo_original"] = a.tipo
    a["tipo"] = a.tipo.replace(TYPE_MAP)
    a["duracao_invalida"] = a.duracao_min.le(0) | a.duracao_min.isna()
    inferred = a.duracao_min.div(a.ritmo_min_km.where(a.ritmo_min_km.gt(0)))
    incompatible = a.distancia_km.div(inferred).sub(1).abs().gt(.10) & inferred.gt(0)
    unevaluable = a.distancia_km.gt(200) & (inferred.isna() | inferred.le(0))
    a["distancia_invalida"] = incompatible | unevaluable
    stats = {"linhas_brutas": len(a), "garmin_fuso_corrigido": int(garmin.sum()),
        "tipos_padronizados": int(a.tipo_original.isin(TYPE_MAP).sum()),
        "duracao_invalida": int(a.duracao_invalida.sum()), "distancia_incompativel_ritmo": int(incompatible.sum()),
        "distancia_alta_nao_avaliavel_ritmo": int(unevaluable.sum()), "distancia_invalida": int(a.distancia_invalida.sum()),
        "fora_corte": int((a.ts.isna() | a.ts.ge(CUT) | a.ts.lt("2026-01-01")).sum())}
    # Preserve original spelling for conservative copy matching, reproducing notebook 06.
    key = ["user_id", "tipo_original", "duracao_min"]
    app = a[a.origem.eq("app")]
    watch = a[~a.origem.eq("app")]
    pairs = app.merge(watch, on=key, suffixes=("_app", "_relogio"))
    pairs = pairs[(pairs.ts_app - pairs.ts_relogio).abs().le(pd.Timedelta(minutes=5))]
    assert pairs.atividade_id_app.is_unique and pairs.atividade_id_relogio.is_unique
    stats["copias_app_removidas"] = pairs.atividade_id_app.nunique()
    a = a[~a.atividade_id.isin(pairs.atividade_id_app) & a.ts.ge("2026-01-01") & a.ts.lt(CUT)].copy()
    # Invalid distance never enters clustering; invalid duration stays flagged but not in usage aggregates.
    a.loc[a.distancia_invalida, "distancia_km"] = np.nan
    a["video"] = a.tipo.isin(VIDEO)
    a["ar_livre"] = ~a.video
    stats["linhas_sem_copias_no_corte"] = len(a)
    stats["linhas_duracao_valida"] = int((~a.duracao_invalida).sum())
    return a, stats


def rates(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    out = df.groupby(keys, observed=True, dropna=False).agg(expostos=("user_id", "size"), perdas=("saiu_mes", "sum")).reset_index()
    out["churn_pct"] = out.perdas.div(out.expostos).mul(100)
    return out


def audit_sources(raw: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    completeness, checks = [], []
    users = set(raw["usuarios"].user_id)
    keys = {"usuarios": ["user_id"], "assinaturas": ["assinatura_id"], "eventos_assinatura": None,
        "pagamentos": ["pagamento_id"], "uso_mensal": ["user_id", "mes"], "atividades": ["atividade_id"],
        "onboarding": ["onboarding_id"], "feed_posts": ["post_id"], "amizades": ["seguidor_id", "seguido_id"],
        "tickets_suporte": ["ticket_id"], "pesquisa_saida": ["resposta_id"]}
    datecols = {"usuarios": ["data_cadastro"], "assinaturas": ["inicio", "data_fim"],
        "eventos_assinatura": ["data_hora"], "pagamentos": ["data_hora"], "atividades": ["inicio"],
        "onboarding": ["respondido_em"], "feed_posts": ["data_hora"], "amizades": ["desde"],
        "tickets_suporte": ["aberto_em", "resolvido_em"], "pesquisa_saida": ["respondido_em"]}
    for name, df in raw.items():
        for col in df:
            s = df[col].astype("string")
            blank = s.str.strip().eq("").fillna(False)
            pseudo = s.str.strip().str.lower().isin(SEM_CONTEUDO)
            completeness.append({"arquivo": name, "coluna": col, "linhas": len(df), "nulos": int(df[col].isna().sum()),
                "so_espacos": int(blank.sum()), "pseudo_vazios": int(pseudo.sum()),
                "nulos_pct": df[col].isna().mean()*100})
        uidcols = [c for c in ["user_id", "seguidor_id", "seguido_id", "treino_com"] if c in df]
        orphan = sum(int((df[c].notna() & df[c].astype("string").str.strip().ne("") & ~df[c].isin(users)).sum()) for c in uidcols)
        k = keys[name]
        checks.append({"arquivo": name, "dimensao": "Unicidade", "regra": f"duplicatas na chave {k or 'linha completa'}",
            "afetadas": int(df.duplicated(k).sum()), "linhas": len(df)})
        checks.append({"arquivo": name, "dimensao": "Consistência", "regra": "referências a contas inexistentes (ocorrências)",
            "afetadas": orphan, "linhas": len(df)})
        for col in datecols.get(name, []):
            ts = timestamps(df[col])
            if name == "atividades": ts.loc[df.origem.eq("garmin")] -= pd.Timedelta(hours=3)
            checks.extend([
                {"arquivo": name, "dimensao": "Validade", "regra": f"{col}: preenchida e não interpretável", "afetadas": int((df[col].notna() & ts.isna()).sum()), "linhas": len(df)},
                {"arquivo": name, "dimensao": "Temporalidade", "regra": f"{col}: posterior ao corte (não necessariamente erro)", "afetadas": int(ts.ge(CUT).sum()), "linhas": len(df)}])
        if name == "uso_mensal":
            checks.append({"arquivo": name, "dimensao": "Validade", "regra": "mês fora de 2025-01 a 2026-09",
                "afetadas": int((~df.mes.between("2025-01", "2026-09")).sum()), "linhas": len(df)})
    return pd.DataFrame(completeness), pd.DataFrame(checks)


def make_features(current, users, usage, activities, onboarding, posts, friends, tickets, payments, events, subs):
    base = current[["user_id", "inicio_ts", "plano", "canal_cobranca"]].merge(
        users[["user_id", "canal_aquisicao", "sistema", "data_cadastro"]], on="user_id", validate="one_to_one")
    base["tempo_assinatura_dias"] = (CUT - base.inicio_ts).dt.days
    base["tempo_cadastro_dias"] = (CUT - timestamps(base.data_cadastro)).dt.days
    base.loc[base.tempo_cadastro_dias.lt(0), "tempo_cadastro_dias"] = np.nan
    # Do not export identity, birth date, location, email, full text or current app version.
    base = base.drop(columns=["data_cadastro", "inicio_ts"])
    for days in [30, 90]:
        a = activities[activities.ts.ge(CUT - pd.Timedelta(days=days)) & ~activities.duracao_invalida].copy()
        a["dia"] = a.ts.dt.normalize()
        agg = a.groupby("user_id").agg(**{
            f"treinos_{days}d": ("atividade_id", "size"), f"minutos_{days}d": ("duracao_min", "sum"),
            f"dias_ativos_{days}d": ("dia", "nunique"), f"treinos_video_{days}d": ("video", "sum"),
            f"treinos_ar_livre_{days}d": ("ar_livre", "sum")})
        base = base.merge(agg, on="user_id", how="left", validate="one_to_one")
        for col in agg: base[col] = base[col].fillna(0)
    last = activities[~activities.duracao_invalida].groupby("user_id").ts.max()
    base["dias_desde_ultimo_treino_2026"] = (CUT - base.user_id.map(last)).dt.total_seconds().div(86400).round(2)
    base["sem_treino_observado_2026"] = base.dias_desde_ultimo_treino_2026.isna().astype(int)
    base["proporcao_video_90d"] = base.treinos_video_90d.div(base.treinos_90d.where(base.treinos_90d.gt(0)))
    earlier = activities[activities.ts.ge(CUT-pd.Timedelta(days=60)) & activities.ts.lt(CUT-pd.Timedelta(days=30)) & ~activities.duracao_invalida]
    base["treinos_30d_anteriores"] = base.user_id.map(earlier.groupby("user_id").size()).fillna(0).astype(int)
    base["variacao_treinos_tratados_30d"] = base.treinos_30d - base.treinos_30d_anteriores
    for month, label in [("2026-08", "ago"), ("2026-09", "set")]:
        um = usage[usage.mes.eq(month)][["user_id", "atividades", "minutos", "sessoes_app"]].rename(
            columns={c: f"{c}_bi_{label}" for c in ["atividades", "minutos", "sessoes_app"]})
        base = base.merge(um, on="user_id", how="left", validate="one_to_one")
        for col in um.columns.drop("user_id"): base[col] = base[col].fillna(0)
    base["variacao_treinos_bi_set_ago"] = base.atividades_bi_set - base.atividades_bi_ago
    base["bi_treinos_set_menos_detalhe"] = base.atividades_bi_set - base.treinos_30d
    ob = onboarding[timestamps(onboarding.respondido_em).lt(CUT)].copy()
    ob["dias_planejados_semana"] = intended_days(ob.dias_por_semana)
    ob["objetivo_sem_conteudo"] = (ob.objetivo_texto.isna() | ob.objetivo_texto.str.strip().str.lower().isin(SEM_CONTEUDO)).astype(int)
    base = base.merge(ob[["user_id", "nivel", "dias_planejados_semana", "objetivo_sem_conteudo"]], on="user_id", how="left", validate="one_to_one")
    for name, frame, col in [("posts_90d", posts, "data_hora"), ("tickets_90d", tickets, "aberto_em")]:
        ts = timestamps(frame[col]); counts = frame[ts.ge(CUT-pd.Timedelta(days=90)) & ts.lt(CUT)].groupby("user_id").size()
        base[name] = base.user_id.map(counts).fillna(0).astype(int)
    f = friends[timestamps(friends.desde).lt(CUT)]
    base["seguidores_corte"] = base.user_id.map(f.groupby("seguido_id").size()).fillna(0).astype(int)
    base["seguindo_corte"] = base.user_id.map(f.groupby("seguidor_id").size()).fillna(0).astype(int)
    open_ts, resolved = timestamps(tickets.aberto_em), timestamps(tickets.resolvido_em)
    unresolved = tickets[open_ts.lt(CUT) & (resolved.isna() | resolved.ge(CUT))].groupby("user_id").size()
    base["tickets_pendentes_corte"] = base.user_id.map(unresolved).fillna(0).astype(int)
    renewal = events[events.evento.isin(["assinatura_iniciada", "renovacao_automatica_desligada", "renovacao_automatica_religada", "cancelamento_web"])].sort_values("ts", kind="stable").groupby("user_id").tail(1).set_index("user_id").evento
    last_renewal_event = base.user_id.map(renewal)
    base["renovacao_desligada_eventos"] = last_renewal_event.isin(["renovacao_automatica_desligada", "cancelamento_web"]).astype("Int64")
    base.loc[last_renewal_event.isna(), "renovacao_desligada_eventos"] = pd.NA
    snapshot = subs.set_index("user_id").renovacao_automatica.eq("nao").astype(int)
    base["renovacao_desligada_retrato"] = base.user_id.map(snapshot)
    base["renovacao_divergente"] = base.renovacao_desligada_eventos.ne(base.renovacao_desligada_retrato).astype("Int64")
    # Last observed charge is a descriptive proxy; never call it recognized revenue, LTV or guaranteed MRR.
    last_pay = payments.sort_values("ts", kind="stable").groupby("user_id").tail(1).set_index("user_id")
    base["ultima_cobranca_aprovada_reais"] = base.user_id.map(last_pay.centavos).astype(float).div(100)
    base["receita_mensal_equivalente_proxy"] = base.ultima_cobranca_aprovada_reais / np.where(base.plano.eq("anual"), 12, 1)
    base["receita_liquida_mensal_equivalente_proxy"] = base.receita_mensal_equivalente_proxy * (1-base.user_id.map(last_pay.metodo.map(FEES)))
    return base.sort_values("user_id").reset_index(drop=True)


def md_table(df: pd.DataFrame) -> str:
    def fmt(v):
        if pd.isna(v): return "—"
        if isinstance(v, (float, np.floating)): return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(v).replace("|", "/")
    return "| " + " | ".join(map(str, df.columns)) + " |\n|" + "|".join(["---"]*len(df.columns)) + "|\n" + "\n".join("| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False, name=None))


def feature_dictionary(features, clustercols):
    definitions = {
        "user_id": ("usuarios", "Chave de integração; nunca usar como variável de agrupamento."),
        "plano": ("eventos + semente anterior ao log", "Plano do pagante no corte; validado como constante por conta nesta base."),
        "canal_cobranca": ("eventos + semente anterior ao log", "Canal de pagamento no corte; categoria, não escala numérica."),
        "canal_aquisicao": ("usuarios", "Canal atribuído no cadastro; não confundir com canal de cobrança."),
        "sistema": ("usuarios", "Sistema registrado no retrato; sem histórico de troca."),
        "tempo_assinatura_dias": ("intervalos de assinatura", "Dias inteiros entre início do período pago e limite exclusivo; controlar exposição."),
        "tempo_cadastro_dias": ("usuarios", "Dias inteiros desde cadastro; negativo é marcado como ausente."),
        "dias_desde_ultimo_treino_2026": ("atividades tratadas", "Dias decimais desde último treino válido em 2026; ausente não significa zero nem abandono."),
        "sem_treino_observado_2026": ("atividades tratadas", "1 se não há treino válido na cobertura 2026; 0 caso contrário."),
        "proporcao_video_90d": ("atividades tratadas", "Treinos em vídeo / treinos válidos nos últimos 90 dias; ausente quando denominador é zero."),
        "variacao_treinos_bi_set_ago": ("uso_mensal", "Diferença absoluta setembro menos agosto, sem divisão por zero; fonte BI não deduplicada."),
        "treinos_30d_anteriores": ("atividades tratadas", "Treinos válidos de 02/08 a 31/08/2026, janela de 30 dias imediatamente anterior à janela atual."),
        "variacao_treinos_tratados_30d": ("atividades tratadas", "Treinos válidos dos últimos 30 dias menos treinos dos 30 dias anteriores; mesma fonte e duração de janela."),
        "bi_treinos_set_menos_detalhe": ("uso_mensal × atividades", "Contagem do BI de setembro menos treinos válidos tratados; indicador de conciliação, fora dos clusters."),
        "nivel": ("onboarding", "Nível autodeclarado no cadastro; preservar ausência."),
        "dias_planejados_semana": ("onboarding", "Número de 1 a 7; aceita número, Nx, N vezes; todos = 7; demais valores ausentes."),
        "objetivo_sem_conteudo": ("onboarding", "1 se resposta é nula ou pseudo-vazia; ausência de onboarding permanece ausente."),
        "posts_90d": ("feed_posts", "Número de posts publicados nos últimos 90 dias; não usa texto ou curtidas acumuladas."),
        "tickets_90d": ("tickets_suporte", "Número de tickets abertos nos últimos 90 dias; não indica gravidade."),
        "seguidores_corte": ("amizades", "Relações de seguir recebidas antes do limite; excluir contas de teste."),
        "seguindo_corte": ("amizades", "Relações de seguir iniciadas pela conta antes do limite; excluir contas de teste."),
        "tickets_pendentes_corte": ("tickets_suporte", "Abertura antes do limite e resolução ausente ou posterior ao corte; não usa status atual como histórico."),
        "renovacao_desligada_eventos": ("eventos_assinatura", "Último início/desligamento/religamento/cancelamento ordenado pelo horário recebido; ausente sem estado observado."),
        "renovacao_desligada_retrato": ("assinaturas", "Situação da renovação no retrato de 01/10; contexto descritivo separado da reconstrução por eventos."),
        "renovacao_divergente": ("eventos × retrato", "1 se os estados conhecidos discordam; ausente se eventos não informam estado inicial; não corrigir por suposição."),
        "ultima_cobranca_aprovada_reais": ("pagamentos tratados", "Última cobrança aprovada antes do limite; não desconta estornos/chargebacks."),
        "receita_mensal_equivalente_proxy": ("pagamentos × plano", "Última cobrança no mensal; última cobrança / 12 no anual; aproximação, não receita contábil ou LTV."),
        "receita_liquida_mensal_equivalente_proxy": ("pagamentos × taxas", "Aproximação anterior menos taxa do método; sem estornos, custo de servir ou ofertas."),
    }
    records=[]
    for col in features:
        if col in definitions: source, definition=definitions[col]
        elif "_bi_" in col:
            source="uso_mensal";definition="Indicador mensal original de agosto ou setembro/2026; não substitui a atividade tratada. Ausência de linha em 2026 = zero."
        elif re.search(r"_(30|90)d$",col):
            source="atividades tratadas"
            definition="Agregado de treinos com duração positiva, sem cópias do app, entre limite menos N dias (inclusivo) e limite (exclusivo). Minutos somam duração; dias_ativos conta datas distintas; treinos conta registros."
        else: raise ValueError(f"Variável sem definição: {col}")
        records.append({"variavel":col,"fonte":source,"definicao":definition,
            "candidata_clusterizacao":col in clustercols and col!="user_id","ausentes_corte":int(features[col].isna().sum())})
    return pd.DataFrame(records)


def svg_plot(path: Path, title: str, labels, series: dict[str, list], line=False, subtitle="Churn (%)"):
    width, height, left, top, bottom = 1060, 500, 95, 90, 140
    plotw, ploth = width-left-35, height-top-bottom
    vals = [float(v) for values in series.values() for v in values if pd.notna(v)]
    ymax = max(vals, default=1)*1.20 or 1
    colors = ["#087e8b", "#e17731", "#6655aa", "#9d354d"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect width="100%" height="100%" fill="#fafbfc"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#20313e}.title{font-size:23px;font-weight:bold}.small{font-size:13px}</style>',
        f'<text x="25" y="32" class="title">{html.escape(title)}</text>', f'<text x="25" y="57" class="small">{html.escape(subtitle)}</text>']
    for j in range(5):
        y=top+ploth-ploth*j/4
        parts += [f'<line x1="{left}" y1="{y}" x2="{width-35}" y2="{y}" stroke="#dce3e8"/>',
            f'<text x="{left-12}" y="{y+5}" text-anchor="end" class="small">{ymax*j/4:.1f}</text>']
    step=plotw/max(len(labels),1)
    for k,(name,values) in enumerate(series.items()):
        color=colors[k%len(colors)];points=[]
        for i,v in enumerate(values):
            if pd.isna(v): continue
            x=left+step*(i+.5);y=top+ploth-float(v)/ymax*ploth
            if line: points.append(f"{x:.1f},{y:.1f}");parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{color}"/>')
            else:
                bw=step*.7/len(series); bx=left+step*i+step*.15+k*bw
                parts.append(f'<rect x="{bx}" y="{y}" width="{bw-3}" height="{top+ploth-y}" fill="{color}"/>')
                parts.append(f'<text x="{bx+bw/2}" y="{y-7}" text-anchor="middle" class="small">{float(v):.1f}%</text>')
        if line: parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<rect x="{left+k*230}" y="{height-35}" width="14" height="14" fill="{color}"/><text x="{left+21+k*230}" y="{height-23}" class="small">{html.escape(name)}</text>')
    for i,label in enumerate(labels):
        x=left+step*(i+.5);y=top+ploth+20
        parts.append(f'<text x="{x}" y="{y}" transform="rotate(-35 {x} {y})" text-anchor="end" class="small">{html.escape(str(label))}</text>')
    parts.append('</svg>');path.write_text("\n".join(parts))


def main():
    bruto, proc, out = ROOT/"dados/brutos", ROOT/"dados/processados/s5_john", ROOT/"dados/saidas/s5_john"
    proc.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    names = ["usuarios", "assinaturas", "eventos_assinatura", "pagamentos", "uso_mensal", "onboarding", "feed_posts", "amizades", "tickets_suporte", "pesquisa_saida"]
    paths = {n: bruto/f"{n}.csv" for n in names}; paths["atividades"] = bruto/"atividades.parquet"
    before = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()}
    raw = {n: pd.read_csv(p, low_memory=False, keep_default_na=False, na_values=[""]) for n,p in paths.items() if n != "atividades"}
    raw["atividades"] = pd.read_parquet(paths["atividades"])
    completeness, quality = audit_sources(raw)
    extra=[]
    def quality_check(source, dimension, rule, mask):
        extra.append({"arquivo":source,"dimensao":dimension,"regra":rule,"afetadas":int(mask.sum()),"linhas":len(mask)})
    for col in ["atividades","atividades_ar_livre","atividades_video","minutos","dias_ativos","sessoes_app"]:
        quality_check("uso_mensal","Validade",f"{col}: negativo ou ausente",raw["uso_mensal"][col].lt(0)|raw["uso_mensal"][col].isna())
    quality_check("uso_mensal","Consistência","total de atividades diferente de ar livre + vídeo",
        raw["uso_mensal"].atividades.ne(raw["uso_mensal"].atividades_ar_livre+raw["uso_mensal"].atividades_video))
    sub_users=raw["assinaturas"].merge(raw["usuarios"][["user_id","data_cadastro"]],on="user_id",validate="many_to_one")
    quality_check("assinaturas","Consistência","início anterior ao dia de cadastro; marcar, sem alterar população",
        timestamps(sub_users.inicio).lt(timestamps(sub_users.data_cadastro).dt.normalize()))
    quality_check("onboarding","Validade","dias preenchidos sem extração inequívoca entre 1 e 7",
        raw["onboarding"].dias_por_semana.notna() & intended_days(raw["onboarding"].dias_por_semana).isna())
    quality=pd.concat([quality,pd.DataFrame(extra)],ignore_index=True)
    completeness.to_csv(proc/"completude_por_coluna.csv", index=False)
    filters = []
    def step(source, rule, df): filters.append({"fonte":source, "etapa":rule, "linhas":len(df)})
    u=raw["usuarios"].copy(); test=u.email.str.strip().str.lower().str.endswith("@vitaliza.com.br").fillna(False)
    testids=set(u.loc[test,"user_id"]); u=u[~test].copy()
    a=raw["assinaturas"][~raw["assinaturas"].user_id.isin(testids)].copy()
    assert u.user_id.is_unique and a.user_id.is_unique, "Rever granularidade: mais de uma assinatura por usuário"
    for n in names + ["atividades"]:
        step(n,"bruto",raw[n])
    step("usuarios","excluir contas de teste",u);step("assinaturas","excluir contas de teste",a)
    e=raw["eventos_assinatura"].copy();e["ts"]=timestamps(e.data_hora)
    assert e.ts.notna().all()
    e=e[~e.user_id.isin(testids) & e.ts.lt(CUT)].copy();step("eventos_assinatura","sem testes e anterior ao limite exclusivo",e)
    # Plan/channel are stable in this dataset. Fail explicitly if a future version changes them.
    assert e.groupby("user_id").plano.nunique().le(1).all()
    assert e.groupby("user_id").canal_cobranca.nunique().le(1).all()
    intervals=build_intervals(a,e)
    current=active_at(intervals,CUT)
    assert current.user_id.is_unique and len(current)==14753
    assert set(current.user_id)==set(a.loc[a.status_atual.eq("ativa"),"user_id"])
    step("base_integrada","pagantes ativos no corte pelos eventos; conciliados ao retrato",current)
    intervals.to_parquet(proc/"intervalos_assinatura.parquet",index=False)
    usage=raw["uso_mensal"].copy();assert not usage.duplicated(["user_id","mes"]).any()
    usage=usage[~usage.user_id.isin(testids) & usage.mes.between("2025-01","2026-09")]
    step("uso_mensal","sem testes dentro da cobertura documentada",usage)
    panel=historical_panel(intervals,usage)
    panel.to_parquet(proc/"painel_churn_mensal.parquet",index=False)
    monthly=rates(panel,["mes"])
    anchors={"2025-01":8540,"2026-04":14237,"2026-09":14319}
    for month,n in anchors.items(): assert monthly.set_index("mes").loc[month,"expostos"]==n
    assert monthly.set_index("mes").loc["2026-04","perdas"]==1154
    assert monthly.set_index("mes").loc["2026-09","perdas"]==714
    plan=rates(panel,["mes","plano"]);channel=rates(panel,["mes","canal_cobranca"])
    yearly=rates(panel,["ano"])
    yearly["media_mensal_simples_pct"] = monthly.assign(ano=monthly.mes.str[:4]).groupby("ano").churn_pct.mean().reindex(yearly.ano).to_numpy()
    yearly_plan=rates(panel,["ano","plano"]); yearly_channel=rates(panel,["ano","canal_cobranca"])
    eligible=panel[panel.uso_anterior_coberto & panel.mes_anterior_completo].copy()
    engagement=rates(eligible,["ano","faixa_uso_anterior"])
    # Compare Jan-Sep of both years, plus the all-available series; do not conflate unequal periods.
    same=panel[panel.mes.str[5:7].le("09")]
    comparable=rates(same,["ano"])
    comparable_plan=rates(same,["ano","plano"])
    components=[]
    for plan_name in sorted(comparable_plan.plano.unique()):
        both=comparable_plan[comparable_plan.plano.eq(plan_name)].set_index("ano")
        totals=comparable.set_index("ano").expostos
        s0,s1=both.loc["2025","expostos"]/totals["2025"],both.loc["2026","expostos"]/totals["2026"]
        r0,r1=both.loc["2025","churn_pct"],both.loc["2026","churn_pct"]
        components.append({"plano":plan_name,"participacao_exposicoes_2025_pct":s0*100,"participacao_exposicoes_2026_pct":s1*100,
            "churn_2025_pct":r0,"churn_2026_pct":r1,"componente_taxas_pp":(s0+s1)/2*(r1-r0),
            "componente_composicao_pp":(r0+r1)/2*(s1-s0)})
    decomposition=pd.DataFrame(components)
    observed_delta=comparable.set_index("ano").loc["2026","churn_pct"]-comparable.set_index("ano").loc["2025","churn_pct"]
    assert np.isclose(decomposition[["componente_taxas_pp","componente_composicao_pp"]].to_numpy().sum(),observed_delta)
    periods=panel.copy();periods["periodo"]=np.select([
        periods.mes.between("2026-01","2026-02"),periods.mes.between("2026-03","2026-04"),periods.mes.between("2026-05","2026-09")],
        ["2026 jan–fev","2026 mar–abr","2026 mai–set"],default="2025")
    price=rates(periods,["periodo","plano"])
    reason=a[a.data_fim.notna()].copy();reason["fim"]=pd.to_datetime(reason.data_fim);reason["mes"]=reason.fim.dt.strftime("%Y-%m")
    reason=reason[reason.fim.ge("2025-01-01") & reason.fim.lt(CUT)]
    causes=reason.groupby(["mes","motivo_fim"],dropna=False).size().rename("fins_assinatura").reset_index()
    # End reasons are contextual; this denominator also includes starts-and-ends inside one month.
    act, activity_stats=clean_activities(raw["atividades"])
    act=act[~act.user_id.isin(testids)]
    for k in ["linhas_sem_copias_no_corte","linhas_duracao_valida"]:
        filters.append({"fonte":"atividades","etapa":k,"linhas":activity_stats[k]})
    activity_stats["linhas_sem_testes"]=len(act)
    pay=raw["pagamentos"].copy();pay["ts"]=timestamps(pay.data_hora);pay["centavos"]=money_cents(pay.valor)
    assert pay.loc[pay.status.eq("aprovado"),"centavos"].notna().all()
    pay=pay[~pay.user_id.isin(testids) & pay.ts.lt(CUT) & pay.status.eq("aprovado")].copy();step("pagamentos","aprovados sem testes e no corte",pay)
    pay=pay.drop_duplicates(["user_id","ts","centavos"]);step("pagamentos","deduplicar user_id + instante + valor",pay)
    scoped={}
    for name,col in [("onboarding","respondido_em"),("feed_posts","data_hora"),("tickets_suporte","aberto_em")]:
        frame=raw[name]
        scoped[name]=frame[~frame.user_id.isin(testids) & timestamps(frame[col]).lt(CUT)]
        step(name,"sem testes e com ocorrência anterior ao limite",scoped[name])
    friends=raw["amizades"]
    friends=friends[timestamps(friends.desde).lt(CUT) & ~friends.seguidor_id.isin(testids) & ~friends.seguido_id.isin(testids)]
    step("amizades","relações no corte sem contas de teste nas duas pontas",friends)
    features=make_features(current,u,usage,act,scoped["onboarding"],scoped["feed_posts"],friends,scoped["tickets_suporte"],pay,e,a)
    # Observation-only behavioural features for clustering. Outcome/renewal intent and financial values are separate.
    clustercols=["user_id","tempo_assinatura_dias","treinos_30d","minutos_30d","dias_ativos_30d","treinos_90d","minutos_90d",
        "dias_ativos_90d","proporcao_video_90d","dias_desde_ultimo_treino_2026","sem_treino_observado_2026",
        "variacao_treinos_tratados_30d","posts_90d","seguidores_corte","seguindo_corte","tickets_90d","dias_planejados_semana","nivel"]
    features.to_csv(proc/"base_assinantes_corte.csv",index=False)
    features[clustercols].to_csv(proc/"base_clusterizacao.csv",index=False)
    dictionary=feature_dictionary(features,clustercols)
    dictionary.to_csv(out/"dicionario_base_analitica.csv",index=False)
    (out/"dicionario_base_analitica.md").write_text("# Dicionário da base analítica — S5\n\nLimite exclusivo: 01/10/2026, Brasília. Os 90 dias vão de 03/07 a 30/09; os 30 dias correspondem a setembro.\n\n"+md_table(dictionary)+"\n")
    assert len(features)==features.user_id.nunique()==14753
    assert not features.user_id.isin(testids).any()
    for table in [plan,channel]:
        assert table.groupby("mes").expostos.sum().equals(monthly.set_index("mes").expostos)
        assert table.groupby("mes").perdas.sum().equals(monthly.set_index("mes").perdas)
    # Hand audit: compare three independent snapshot rows with start/end events; identifiers stay local.
    audit=a[a.status_atual.eq("ativa")].sample(3,random_state=42).merge(current,on="user_id",validate="one_to_one",suffixes=("_retrato","_evento"))
    assert audit.plano_atual.eq(audit.plano).all()
    assert audit.canal_cobranca_retrato.eq(audit.canal_cobranca_evento).all()
    assert pd.to_datetime(audit.inicio).eq(audit.inicio_ts.dt.normalize()).all()
    audit.to_csv(proc/"conferencia_tres_assinantes.csv",index=False)
    expired=a[a.data_fim.between("2025-01-01","2026-09-30")].sample(3,random_state=42).merge(intervals,on="user_id",validate="one_to_one")
    assert pd.to_datetime(expired.data_fim).eq(expired.fim_ts.dt.normalize()).all()
    expired.to_csv(proc/"conferencia_tres_expiracoes.csv",index=False)
    last_usage=usage[usage.mes.eq("2026-09")]
    actsept=act[act.ts.ge("2026-09-01")]
    detail=actsept.groupby("user_id").agg(treinos_sem_copias=("atividade_id","size"),minutos_sem_copias=("duracao_min","sum"))
    reconcile=last_usage.merge(detail,on="user_id",how="left").fillna({"treinos_sem_copias":0,"minutos_sem_copias":0})
    reconcile["delta_treinos"]=reconcile.atividades-reconcile.treinos_sem_copias
    reconcile.to_csv(proc/"conciliacao_uso_bi_detalhe_setembro.csv",index=False)
    survey=raw["pesquisa_saida"].copy();survey=survey[timestamps(survey.respondido_em).lt(CUT) & ~survey.user_id.isin(testids)]
    step("pesquisa_saida","sem testes e respostas no corte",survey)
    survey_agg=survey.groupby("motivo_principal").size().rename("respostas").reset_index();survey_agg["pct_respostas"]=survey_agg.respostas.div(len(survey)).mul(100)
    base_summary=features.groupby(["plano","canal_cobranca"]).agg(assinantes=("user_id","size"),mediana_treinos_30d=("treinos_30d","median"),
        media_treinos_30d=("treinos_30d","mean"),sem_treino_30d_pct=("treinos_30d",lambda s:s.eq(0).mean()*100),
        renovacao_desligada_retrato=("renovacao_desligada_retrato","sum"),receita_mensal_equivalente_proxy=("receita_mensal_equivalente_proxy","sum")).reset_index()
    support=raw["tickets_suporte"].copy();support["mes"]=timestamps(support.aberto_em).dt.strftime("%Y-%m")
    support=support[~support.user_id.isin(testids) & support.mes.between("2025-07","2026-09")]
    support_agg=support.groupby(["mes","categoria_atendente"]).size().rename("tickets").reset_index()
    support_paid=support.merge(intervals[["user_id","inicio_ts","fim_ts"]],on="user_id",how="inner",validate="many_to_one")
    opened=timestamps(support_paid.aberto_em)
    support_paid=support_paid[support_paid.inicio_ts.le(opened) & (support_paid.fim_ts.isna() | support_paid.fim_ts.gt(opened))]
    support_paid_agg=support_paid.groupby(["mes","categoria_atendente"]).size().rename("tickets_pagantes_na_abertura").reset_index()
    quality["pct_linhas"]=quality.afetadas.div(quality.linhas).mul(100)
    quality.to_csv(proc/"auditoria_qualidade.csv",index=False)
    quality_public=quality[quality.afetadas.gt(0)]
    tables={"churn_mensal":monthly,"churn_por_plano_mes":plan,"churn_por_canal_mes":channel,"churn_por_ano":yearly,
        "churn_plano_ano":yearly_plan,"churn_canal_ano":yearly_channel,"churn_jan_set_comparavel":comparable,
        "churn_plano_jan_set":comparable_plan,"decomposicao_plano_jan_set":decomposition,
        "churn_uso_anterior_por_plano":rates(eligible,["ano","plano","faixa_uso_anterior"]),
        "churn_uso_anterior":engagement,"churn_periodo_reajuste":price,"fins_por_motivo_mes":causes,
        "pesquisa_saida_resumo":survey_agg,"base_corte_resumo":base_summary,"tickets_por_mes_categoria":support_agg,
        "tickets_pagantes_por_mes_categoria":support_paid_agg,
        "filtros":pd.DataFrame(filters),"qualidade_alertas":quality_public}
    for name,df in tables.items(): df.to_csv(out/f"{name}.csv",index=False,float_format="%.6f")
    svg_plot(out/"01_churn_mensal.svg","Churn mensal: base no início do mês",monthly.mes,{"Churn observado":monthly.churn_pct.tolist()},line=True)
    for keys,table,name,title in [(["mensal","anual"],yearly_plan,"02_churn_plano.svg","Churn por plano e ano"),
        (["app_store","google_play","web_cartao","web_pix"],yearly_channel,"03_churn_canal.svg","Churn por canal e ano"),
        (["0 treinos","1–3 treinos","4–7 treinos","8+ treinos"],engagement,"04_uso_churn.svg","Uso anterior e churn posterior")]:
        col={"02_churn_plano.svg":"plano","03_churn_canal.svg":"canal_cobranca","04_uso_churn.svg":"faixa_uso_anterior"}[name]
        pivot=table.pivot(index=col,columns="ano",values="churn_pct").reindex(keys)
        svg_plot(out/name,title,keys,{str(year):pivot[year].tolist() for year in pivot.columns},subtitle="Perdas / exposições usuário-mês (%); 2025 e jan–set/2026; associação descritiva")
    manifest={"corte_inclusivo":"2026-09-30 America/Sao_Paulo","limite_exclusivo":str(CUT),"sha256_brutos":before,
        "atividades":activity_stats,"assinantes_corte":len(features),"exposicoes_painel":len(panel),
        "linhas_bi_detalhe_divergentes_setembro":int(reconcile.delta_treinos.ne(0).sum()),
        "renovacao_desligada_eventos":int(features.renovacao_desligada_eventos.sum()),
        "renovacao_sem_estado_inicial_eventos":int(features.renovacao_desligada_eventos.isna().sum()),
        "renovacao_divergencias":int(features.renovacao_divergente.sum()),
        "renovacao_desligada_retrato":int(a.loc[a.status_atual.eq("ativa"),"renovacao_automatica"].eq("nao").sum()),
        "sem_pagamento_aprovado":int(features.ultima_cobranca_aprovada_reais.isna().sum()),
        "variaveis_base_clusterizacao":clustercols,"verificacoes":"âncoras oficiais, partições por plano/canal, 3 assinantes, chaves e hashes"}
    after={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()}
    assert before==after,"Fonte bruta foi alterada"
    (proc/"manifesto_validacao.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    write_report(out,features,tables,manifest)
    write_synthesis(out,features,tables,manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in {"sha256_brutos","variaveis_base_clusterizacao"}},ensure_ascii=False,indent=2))


def write_report(out, features, tables, manifest):
    """Relatório é gerado com números calculados; interpretação final está nos documentos de entrega."""
    report = """# Preparação dos dados e diagnóstico — John | Semana 5

Status: análise descritiva reproduzível; revisão do grupo pendente. Corte: 30/09/2026, em Brasília.
Responsabilidade: integração, indicadores e hipóteses. Clusterização, personas e decisão financeira final pertencem às demais frentes.

## Pergunta de negócio e entregáveis

Como uso e churn variam por plano, canal e período, e quais hipóteses os dados sustentam para investigar a alta de 2026?
Período histórico: janeiro/2025 a setembro/2026. População da segmentação: pagantes ativos ao final do corte, incluindo quem desligou a renovação mas ainda tem período pago.

As bases individuais estão em `dados/processados/s5_john/`, fora do Git. Os CSVs agregados e gráficos desta pasta podem ser compartilhados com o grupo. O código está em `src/preparar_diagnostico_s5.py`.

## Método e decisões

- As 60 contas internas são identificadas pelo domínio de e-mail normalizado e excluídas das populações pagantes.
- O histórico é reconstruído com inícios e expirações dos eventos. Somente assinaturas anteriores a 01/07/2024 usam a data de início do retrato como semente. Nesta base há uma assinatura por conta e plano/canal não mudam nos eventos; essas condições são verificadas em código.
- Ativo em uma data significa início ≤ data e fim > data, ou sem fim. Desligar renovação e entrar em carência não encerram o período pago. Expiração já acompanha reembolso/chargeback; esses avisos não são contados novamente como perdas.
- Churn mensal = assinantes ativos no início do mês que expiram durante o mês / ativos no início do mês. Quem começou e terminou no mesmo mês não pertence a esse denominador.
- Datas com `Z` são convertidas de UTC para Brasília; Garmin recebe correção de −3h. O limite de tempo é exclusivo em 01/10/2026 00h.
- Uso para comparar com churn é do mês anterior; a análise principal de uso inclui apenas quem já era pagante no início daquele mês anterior. Janeiro/2025 fica sem uso anterior porque dezembro/2024 não foi fornecido.
- Ausência de linha de treino em 2025 vira zero somente dentro da cobertura conhecida e com população definida. Sessões do app não são reconstruídas nos meses sem treino de 2025.
- A atividade detalhada é padronizada, corrigida de fuso e deduplicada. Duração inválida fica sinalizada e sai dos agregados de treino válido; distância incompatível fica nula e não entra no agrupamento.
- As referências a companhia de treino em branco são ausência opcional, não referências a contas inexistentes. Datas posteriores ao corte em posts e relações sociais são excluídas; resoluções futuras não tornam um ticket resolvido no passado.
- Textos e imagens não recebem interpretação generativa nesta etapa. Contagens de posts, seguidores e tickets são usadas como sinais observados. Não há chamadas pagas de IA.

## Base no corte

{base}

Há {n} pagantes ativos. A base individual preserva `user_id`, mas exclui e-mail, data de nascimento, localização e textos integrais. O arquivo de clusterização não inclui desfecho futuro, intenção de cancelamento nem valor financeiro; Leonardo deve escolher variáveis, tratar ausências e padronizar escalas antes de ajustar os grupos.

## Evolução do churn

![Churn mensal](01_churn_mensal.svg)

{year}

`churn_pct` na tabela acima divide o total de perdas pelo total de exposições usuário-mês; `media_mensal_simples_pct` dá o mesmo peso a cada mês e é a referência mais próxima à média mensal do enunciado. Exposições não são pessoas distintas. Os períodos completos disponíveis têm durações diferentes.

Comparação com meses equivalentes (jan–set nos dois anos):

{comparable}

Decomposição aritmética por plano, usando janeiro–setembro nos dois anos:

{decomposition}

O componente de taxas usa a participação média de cada plano nos dois períodos multiplicada pela mudança de sua taxa. O componente de composição usa a taxa média multiplicada pela mudança de participação. A soma fecha exatamente com a mudança agregada, mas não identifica causas. A migração da composição para o anual amortece parte da piora dentro dos planos.

Série mensal completa:

{monthly}

## Diferenças por plano e canal

![Churn por plano](02_churn_plano.svg)

{plans}

![Churn por canal](03_churn_canal.svg)

{channels}

As taxas são descritivas. O anual só expira no fim do ciclo, enquanto o mensal renova todos os meses. Comparar taxas sem olhar quem estava elegível à renovação mistura ritmos contratuais com preferência do cliente. Plano, canal, tempo de casa e perfil de uso também podem estar associados entre si.

## Uso anterior e saída posterior

![Uso anterior e churn](04_uso_churn.svg)

{engagement}

Uso baixo pode antecipar a saída, mas também refletir problemas de produto, motivação, saúde ou diferenças de perfil. A tabela não prova que aumentar treinos causa retenção. O BI mensal e os eventos de treino detalhados não são intercambiáveis: {divergent} linhas de setembro apresentam contagem diferente após deduplicação. Por isso os indicadores mantêm sufixos que identificam sua fonte.

## Reajuste: comparação exploratória

{price}

O preço mensal mudou em março/2026. Comparar janeiro–fevereiro com março–abril e maio–setembro permite localizar a mudança, mas não isola seu efeito. São grupos e meses diferentes, sem controle de sazonalidade e composição; não há conclusão causal nem estimativa de impacto do reajuste.

## Motivos declarados e suporte

{survey}

A pesquisa só alcança cancelamentos pelo site e é opcional. As porcentagens acima descrevem respostas, não toda a base nem todas as perdas. Algumas respostas antecedem o fim do período pago e duas contas podem ter mais de uma resposta. O CSV `fins_por_motivo_mes.csv` usa todos os fins por data, incluindo assinaturas iniciadas no próprio mês; seu total não é o numerador do churn. `tickets_por_mes_categoria.csv` permite investigar a hipótese técnica, com cobertura apenas desde julho/2025.

## Limitações e próximos passos

1. Ainda não há clusters: a base preparada é a entrada para o trabalho de Leonardo. Churn por cluster exigirá aplicar a mesma segmentação a observações históricas compatíveis; não atribuir o churn dos que saíram aos grupos formados apenas por sobreviventes do corte.
2. Risco individual de saída até 29/11/2026 não é observado no corte e não é inferido aqui. Intenção de cancelar e expiração são conceitos distintos.
3. A última cobrança aprovada dividida por 12 no anual é somente uma aproximação mensal descritiva. Não representa receita contábil, caixa do mês, LTV ou retorno de intervenção. Faltam estornos/chargebacks líquidos e regras de reconhecimento para essas contas.
4. A base de uso atual contém pessoas com pouco tempo de assinatura: comparar janelas fixas sem considerar tempo de exposição favorece antigos. `tempo_assinatura_dias` está disponível para controle.
5. A versão do app é a última vista no cadastro. Não foi usada como se fosse a versão instalada em abril/2026. A mudança de idioma dos treinos é um sinal de registro, não prova de falha técnica.
6. A análise da campanha sorteada, uplift, mensagens e ROI ficam para a etapa apropriada. Não foi estimado benefício de contato.
7. Qualidade foi medida antes das conclusões. Completude por coluna e auditoria detalhada ficam em arquivos locais; alertas agregados e filtros estão nesta pasta. Campo vazio pode ser opcional: a auditoria não transforma todo vazio em erro.
8. A situação de renovação apresenta cinco divergências conhecidas entre eventos ordenados pelo horário de recebimento e retrato. Em 1.112 pagantes, os eventos relevantes não fornecem o estado inicial da renovação. Os campos ficam separados, com ausências e sinalização; nenhum deles entra nas variáveis candidatas de clusterização.
9. As 6.716 linhas divergentes entre BI e detalhe de setembro não são automaticamente 6.716 erros: as fontes podem usar regras distintas. A diferença não foi atribuída apenas às cópias. A tendência recomendada para clusterização compara duas janelas iguais de 30 dias da atividade tratada; a tendência do BI permanece apenas para auditoria.

## Reprodução e evidências

Na raiz do repositório: `.venv/bin/python src/preparar_diagnostico_s5.py`.
Fontes: `docs/enunciado.md`, `docs/dicionario_dados.md`, `decisoes.md` e 11 arquivos utilizados do data room (campanha e imagens não processadas).
Validação: âncoras oficiais, fechamento por plano e canal, três assinantes ativos e três expirações confrontados com retrato, testes de regras temporais e hashes dos arquivos brutos antes/depois. O manifesto local registra as verificações e as contagens.
"""
    rendered=report.format(base=md_table(tables["base_corte_resumo"]),n=len(features),year=md_table(tables["churn_por_ano"]),
        comparable=md_table(tables["churn_jan_set_comparavel"]),monthly=md_table(tables["churn_mensal"]),
        plans=md_table(tables["churn_plano_ano"]),channels=md_table(tables["churn_canal_ano"]),
        engagement=md_table(tables["churn_uso_anterior"]),price=md_table(tables["churn_periodo_reajuste"]),
        survey=md_table(tables["pesquisa_saida_resumo"]),divergent=manifest["linhas_bi_detalhe_divergentes_setembro"],
        decomposition=md_table(tables["decomposicao_plano_jan_set"]))
    (out/"diagnostico.md").write_text(rendered)


def write_synthesis(out, features, tables, manifest):
    # Editorial numbers were reviewed for this fixed case revision. Stop rather than
    # silently publishing stale prose if a later data-room version changes them.
    checks = [
        (tables["churn_por_ano"].set_index("ano").loc["2025","media_mensal_simples_pct"],5.62),
        (tables["churn_por_ano"].set_index("ano").loc["2026","media_mensal_simples_pct"],6.62),
        (tables["churn_jan_set_comparavel"].set_index("ano").loc["2025","churn_pct"],5.61),
        (tables["churn_jan_set_comparavel"].set_index("ano").loc["2026","churn_pct"],6.61),
    ]
    for year,plan,value in [("2025","mensal",9.14),("2026","mensal",10.86),("2025","anual",2.45),("2026","anual",3.32)]:
        checks.append((tables["churn_plano_jan_set"].set_index(["ano","plano"]).loc[(year,plan),"churn_pct"],value))
    for plan,band,value in [("mensal","0 treinos",40.75),("mensal","8+ treinos",7.49),("anual","0 treinos",8.79),("anual","8+ treinos",.40)]:
        checks.append((tables["churn_uso_anterior_por_plano"].set_index(["ano","plano","faixa_uso_anterior"]).loc[("2026",plan,band),"churn_pct"],value))
    for band,value in [("0 treinos",11.18),("8+ treinos",4.04)]:
        checks.append((tables["churn_uso_anterior"].set_index(["ano","faixa_uso_anterior"]).loc[("2026",band),"churn_pct"],value))
    for period,value in [("2026 jan–fev",10.07),("2026 mar–abr",12.82),("2026 mai–set",10.34)]:
        checks.append((tables["churn_periodo_reajuste"].set_index(["periodo","plano"]).loc[(period,"mensal"),"churn_pct"],value))
    for actual,expected in checks:
        assert round(float(actual),2)==expected,"Dados mudaram: revisar números e interpretação da síntese antes de exportar"
    assert features.treinos_30d.eq(0).sum()==1702 and features.tempo_assinatura_dias.lt(30).sum()==1148
    assert manifest["linhas_bi_detalhe_divergentes_setembro"]==6716 and features.bi_treinos_set_menos_detalhe.ne(0).sum()==5542
    tech=tables["tickets_por_mes_categoria"].query("categoria_atendente == 'tecnico'").set_index("mes").tickets
    assert tech.loc["2026-01":"2026-06"].tolist()==[17,14,20,19,383,310]
    (out/"sintese_para_relatorio.md").write_text("""# Síntese para o relatório do grupo — contribuição de John

## Preparação dos dados e diagnóstico

A análise integra os dados da Vitaliza até 30/09/2026 e reconstrói as assinaturas a partir dos eventos de início e expiração. Contas de teste são excluídas pelo domínio de e-mail normalizado. O resultado fecha com as referências do enunciado: 8.540 pagantes no início de 2025, 14.237 no início de abril/2026 e 14.753 ativos no corte. A base de segmentação tem uma linha por pagante, com indicadores observados de treino, uso social, suporte e perfil de entrada.

O churn é medido como a proporção dos ativos no início do mês que encerram a assinatura naquele mês. A média mensal simples foi de 5,62% em 2025 e 6,62% entre janeiro e setembro de 2026. Para comparar períodos equivalentes, janeiro a setembro apresenta 5,61% em 2025 contra 6,61% em 2026, usando perdas divididas pelas exposições usuário-mês. Abril/2026 foi o pico: 1.154 perdas entre 14.237 ativos no início do mês, ou 8,11%.

A piora permanece dentro dos dois planos. Entre janeiro e setembro, o mensal passou de 9,14% para 10,86%, e o anual de 2,45% para 3,32%. Uma decomposição aritmética da alta agregada de aproximadamente 1,00 ponto percentual atribui 1,25 p.p. à elevação das taxas dentro dos planos e −0,25 p.p. à mudança da composição. A maior participação do anual atenua a alta agregada; não a explica. Esses componentes descrevem a conta, sem identificar mecanismos causais. As taxas contratuais mensal e anual têm calendários distintos de renovação e não medem diretamente insatisfação.

O uso anterior apresenta associação com a saída posterior. Entre pagantes que já estavam ativos no início do mês de uso, o churn observado em 2026 foi de 11,18% para quem não treinou no mês anterior e de 4,04% para quem registrou oito ou mais treinos. O padrão persiste ao separar os planos: no mensal, 40,75% versus 7,49%; no anual, 8,79% versus 0,40%. Essas são taxas de grupos históricos, não probabilidades individuais de saída nem efeito de uma ação de retenção. O uso pode refletir diversas condições subjacentes; incentivar treino não tem benefício causal demonstrado por esta comparação.

O plano mensal passou de 10,07% de churn em janeiro–fevereiro/2026 para 12,82% em março–abril, retornando a 10,34% em maio–setembro. A proximidade com o reajuste de março justifica investigar sensibilidade a preço, sem excluir sazonalidade, tempo de assinatura e composição dos clientes. Não é possível atribuir essa variação ao reajuste apenas com a comparação entre períodos.

Os chamados classificados como técnicos somaram 17, 14, 20 e 19 de janeiro a abril/2026, seguidos de 383 em maio e 310 em junho. A tabela abrange todas as contas que abriram chamados; a versão restrita a pagantes no momento da abertura está disponível separadamente. O pico sugere uma investigação de problemas de produto nesse intervalo, mas não demonstra que uma atualização do aplicativo causou churn. A mudança de idioma nos registros desde 15/04/2026 também é um sinal de alteração de registro, não prova de defeito. Os picos de suporte posteriores não bastam para explicar o pico de churn de abril.

## Hipóteses e verificações necessárias

| Hipótese | Evidência que motiva investigar | Próxima verificação |
|---|---|---|
| Baixo engajamento antecipa parte das saídas | Gradiente de churn por uso anterior, também dentro dos planos | Comparar coortes, tempo de casa, elegibilidade de renovação e outras características anteriores à saída |
| Reajuste contribuiu para a piora do mensal | Churn mensal maior em março–abril após a mudança de preço | Comparar meses equivalentes, clientes e ciclos de renovação; separar mudanças de perfil |
| Problemas técnicos contribuíram para saídas | Concentração de tickets técnicos em maio–junho | Relacionar abertura anterior à saída, tema do ticket e recorrência; a versão atual do app não informa a versão histórica |
| Canal marca públicos ou fricções diferentes | Em 2026 as taxas vão de 5,96% na App Store a 7,33% no Pix | Estratificar por plano, tempo de casa e uso; separar cobrança involuntária de decisão de sair |

## Limitações que precisam acompanhar as conclusões

- O BI mensal e o detalhe tratado dos treinos não conciliam em 6.716 linhas de setembro, das quais 5.542 são dos pagantes atuais. O diagnóstico histórico usa o BI com sua origem explícita; as variáveis recomendadas para agrupamento usam a atividade detalhada tratada. Não se combinam as contagens como se fossem equivalentes.
- A atividade detalhada contém 9.383 cópias de registros de relógio no app, 3.649 durações inválidas antes da deduplicação, 999 distâncias incompatíveis com o ritmo e outras três distâncias altas sem duração/ritmo avaliável. As decisões e contagens de tratamento estão documentadas.
- A pesquisa de saída é opcional e restrita ao site. Ela descreve respondentes, sem representar todos os assinantes. Renovação desligada não equivale a expiração.
- Eventos e retrato discordam sobre renovação em cinco casos conhecidos; o estado inicial não está informado nos eventos relevantes de 1.112 pagantes antigos. Esses campos são mantidos separados e não entram no agrupamento proposto.
- Não há desfecho futuro até 29/11/2026, score individual, efeito incremental de contato ou ROI calculados nesta contribuição.

## Encaminhamento para as demais frentes

Leonardo recebe uma base por pagante e 17 variáveis candidatas de agrupamento, além da chave de integração. Deve selecionar variáveis, avaliar correlação e escalas, tratar ausências e validar os clusters. Os campos de volume de treino são relacionados entre si; usar todos sem escolha pode dar peso excessivo ao engajamento. Churn histórico por cluster exigirá aplicar a segmentação às observações históricas correspondentes, e não somente classificar quem sobreviveu até o corte.

Claudinne recebe os filtros, as medidas de qualidade e as pendências de conciliação. Kiril recebe o diagnóstico e, após a clusterização, poderá construir personas ancoradas em comportamentos observados. Marcela recebe plano, canal e uma aproximação mensal da última cobrança aprovada; esse valor não é receita contábil, LTV ou benefício de retenção. A priorização final exige complementar risco com valor, custos e capacidade de ação.

Fontes e rastreabilidade: enunciado e dicionário do case, decisões do grupo, código reproduzível, CSVs agregados e gráficos em `dados/saidas/s5_john/`. As bases individuais e o manifesto de validação ficam em `dados/processados/s5_john/`, fora do repositório público. Esta seção está preparada para revisão e integração ao relatório do grupo.
""")


if __name__ == "__main__":
    main()
