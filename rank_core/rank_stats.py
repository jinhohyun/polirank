import itertools
import math
import statistics


# K-Rank 및 PoliRank 공통 신뢰도·표본 통계 모듈 (rank_stats.py)


def adjusted_ratio(success: int, attempts: int) -> float:
    """Agresti-Coull 보정 비율을 계산한다."""
    if attempts == 0:
        return 0.0
    return (success + 2) / (attempts + 4)


def wilson_interval(success: int, attempts: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson 신뢰구간을 계산하고 0~1 범위로 클램프한다."""
    if attempts == 0:
        return (0.0, 0.0)
    p = success / attempts
    z2 = z * z
    denom = 1.0 + z2 / attempts
    center = (p + z2 / (2.0 * attempts)) / denom
    radicand = (p * (1.0 - p) + z2 / (4.0 * attempts)) / attempts
    margin = (z * math.sqrt(max(0.0, radicand))) / denom
    lower = max(0.0, min(1.0, center - margin))
    upper = max(0.0, min(1.0, center + margin))
    return (lower, upper)


def confidence_label(sample_size: int) -> str:
    """표본 크기에 따른 신뢰도 등급 문자열을 반환한다."""
    if sample_size < 5:
        return "low"
    if sample_size < 20:
        return "mid"
    return "high"


def percentile_from_rank(rank: int, total: int) -> float:
    """순위와 전체 인원으로부터 백분위를 소수 1자리로 계산한다."""
    if total <= 0:
        return 0.0
    return round((1.0 - (rank - 0.5) / total) * 100.0, 1)


def tier_by_rank(rank: int, total: int) -> str:
    """누적 비율 기반으로 순위 티어(S+, S, A, B, C)를 판정한다."""
    if total <= 0:
        return "C"
    # 부동소수점 오차 방지를 위해 정수 비례식으로 누적 비율 경계 판정
    if rank * 10 <= total * 1:
        return "S+"
    if rank * 10 <= total * 3:
        return "S"
    if rank * 10 <= total * 6:
        return "A"
    if rank * 10 <= total * 9:
        return "B"
    return "C"


def analyze_correlations(rows: list[dict], threshold: float = 0.8) -> dict:
    """지표 쌍별 Pearson 상관계수를 계산하고 임계값 이상의 고상관 쌍을 반환한다."""
    if not rows:
        return {"n": 0, "high_corr_pairs": [], "pair_count": 0}

    keys = list(rows[0].keys())
    high_corr_pairs = []
    pair_count = 0

    for k1, k2 in itertools.combinations(keys, 2):
        # 결측(None)이 포함된 행은 해당 쌍에서 제외
        valid = [
            (row[k1], row[k2])
            for row in rows
            if row.get(k1) is not None and row.get(k2) is not None
        ]
        # 유효 표본 3개 미만 건너뜀
        if len(valid) < 3:
            continue

        xs = [pair[0] for pair in valid]
        ys = [pair[1] for pair in valid]
        mean_x = statistics.mean(xs)
        mean_y = statistics.mean(ys)

        sxx = sum((x - mean_x) ** 2 for x in xs)
        syy = sum((y - mean_y) ** 2 for y in ys)
        # 분산이 0인 경우 건너뜀
        if sxx == 0.0 or syy == 0.0:
            continue

        pair_count += 1
        sxy = sum((x - mean_x) * (y - mean_y) for x, y in valid)
        r = max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))

        if abs(r) >= threshold:
            high_corr_pairs.append({"a": k1, "b": k2, "r": round(r, 4)})

    return {
        "n": len(rows),
        "high_corr_pairs": high_corr_pairs,
        "pair_count": pair_count,
    }


def renormalize(stats: dict, weights: dict, min_weight: float = 0.5) -> dict:
    """결측이 아닌 지표만으로 가중치를 재정규화하여 점수를 계산한다 (기본값 대체 없음)."""
    available = [k for k in weights if k in stats and stats[k] is not None]
    total_weight = sum(weights.values())
    avail_weight = sum(weights[k] for k in available)
    data_completeness = (avail_weight / total_weight) if total_weight > 0 else 0.0

    if avail_weight < min_weight or avail_weight == 0.0:
        score = None
    else:
        score = sum(stats[k] * weights[k] for k in available) / avail_weight

    return {
        "score": score,
        "data_completeness": data_completeness,
        "available": available,
    }


if __name__ == "__main__":
    # 1. adjusted_ratio 검증
    try:
        assert adjusted_ratio(0, 0) == 0.0
        assert math.isclose(adjusted_ratio(8, 10), 10 / 14)
        print("PASS: adjusted_ratio")
    except AssertionError:
        print("FAIL: adjusted_ratio")

    # 2. wilson_interval 검증
    try:
        assert wilson_interval(0, 0) == (0.0, 0.0)
        lo, hi = wilson_interval(8, 10)
        assert 0.0 <= lo < 0.8 < hi <= 1.0
        lo_full, hi_full = wilson_interval(10, 10)
        assert 0.0 <= lo_full <= hi_full <= 1.0
        print("PASS: wilson_interval")
    except AssertionError:
        print("FAIL: wilson_interval")

    # 3. confidence_label 검증
    try:
        assert confidence_label(0) == "low"
        assert confidence_label(4) == "low"
        assert confidence_label(5) == "mid"
        assert confidence_label(19) == "mid"
        assert confidence_label(20) == "high"
        print("PASS: confidence_label")
    except AssertionError:
        print("FAIL: confidence_label")

    # 4. percentile_from_rank & tier_by_rank 검증
    try:
        assert percentile_from_rank(1, 0) == 0.0
        assert percentile_from_rank(1, 10) == 95.0
        assert percentile_from_rank(10, 10) == 5.0
        tiers = [tier_by_rank(r, 10) for r in range(1, 11)]
        assert tiers == ["S+", "S", "S", "A", "A", "A", "B", "B", "B", "C"]
        print("PASS: percentile_and_tier")
    except AssertionError:
        print("FAIL: percentile_and_tier")

    # 5. analyze_correlations 검증
    try:
        sample_rows = [
            {"x": 10, "y": 20, "z": 5, "sparse": 1},
            {"x": 20, "y": 40, "z": 5, "sparse": 2},
            {"x": 30, "y": 60, "z": 5, "sparse": None},
            {"x": 40, "y": 79, "z": 5, "sparse": None},
        ]
        corr_res = analyze_correlations(sample_rows, threshold=0.8)
        assert corr_res["n"] == 4
        assert corr_res["pair_count"] == 1
        assert len(corr_res["high_corr_pairs"]) == 1
        assert corr_res["high_corr_pairs"][0]["a"] == "x"
        assert corr_res["high_corr_pairs"][0]["b"] == "y"
        assert corr_res["high_corr_pairs"][0]["r"] > 0.99
        print("PASS: analyze_correlations")
    except AssertionError:
        print("FAIL: analyze_correlations")

    # 6. renormalize 검증
    try:
        w = {"m1": 0.4, "m2": 0.4, "m3": 0.2}
        res_ok = renormalize({"m1": 80.0, "m2": None, "m3": 100.0}, w, min_weight=0.5)
        assert math.isclose(res_ok["data_completeness"], 0.6)
        assert res_ok["available"] == ["m1", "m3"]
        assert res_ok["score"] is not None and math.isclose(
            res_ok["score"], (80.0 * 0.4 + 100.0 * 0.2) / 0.6
        )

        res_low = renormalize({"m1": None, "m2": None, "m3": 100.0}, w, min_weight=0.5)
        assert res_low["score"] is None
        assert math.isclose(res_low["data_completeness"], 0.2)
        print("PASS: renormalize")
    except AssertionError:
        print("FAIL: renormalize")
