from __future__ import annotations

import pandas as pd


BET_TYPES = ["単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "三連複", "三連単"]


def _normalize_horse_no(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if text.isdigit():
        return str(int(text))
    return text


def _parse_odds_value(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "--", "---.-"}:
        return None
    text = text.replace(",", "").replace("〜", "-")
    if "-" in text:
        parts = [part.strip() for part in text.split("-") if part.strip()]
        values: list[float] = []
        for part in parts:
            try:
                values.append(float(part))
            except ValueError:
                continue
        return sum(values) / len(values) if values else None
    try:
        return float(text)
    except ValueError:
        return None


def _combo_numbers(combo: object) -> list[str]:
    text = str(combo).strip()
    return [_normalize_horse_no(p) for p in text.split("-") if _normalize_horse_no(p)] if text else []


def _synthetic_odds(odds_list: list[float]) -> float | None:
    probs = [1.0 / odd for odd in odds_list if odd and odd > 0]
    total = sum(probs)
    return (1.0 / total) if total > 0 else None


def _horse_sort_key(horse_no: str) -> int:
    return int(horse_no) if horse_no.isdigit() else 9999


def _add_spread_column(df: pd.DataFrame, odds_columns: list[str], column_name: str = "差異率") -> pd.DataFrame:
    frame = df.copy()
    if frame.empty:
        frame[column_name] = []
        return frame
    numeric = frame[odds_columns].apply(pd.to_numeric, errors="coerce")
    base = numeric[odds_columns[0]]
    others = numeric[odds_columns[1:]] if len(odds_columns) > 1 else numeric[odds_columns]
    max_others = others.max(axis=1)
    ratio = (max_others / base.where(base > 0)) * 100
    frame[column_name] = ratio.round(4)
    return frame


def _collect_horse_flow_odds(
    frame: pd.DataFrame,
    horses: list[str],
    excluded: set[str],
    mode: str,
    position: int | None = None,
) -> dict[str, float | None]:
    data: dict[str, list[float]] = {h: [] for h in horses}
    seen_unordered: set[tuple[str, ...]] = set()
    if frame is None or frame.empty or not {"組み合わせ", "オッズ"}.issubset(set(frame.columns)):
        return {h: None for h in horses}

    for _, row in frame.iterrows():
        combo = _combo_numbers(row.get("組み合わせ"))
        if not combo or any(item in excluded for item in combo):
            continue

        if mode == "contains":
            unordered_key = tuple(sorted(combo))
            if unordered_key in seen_unordered:
                continue
            seen_unordered.add(unordered_key)

        odd = _parse_odds_value(row.get("オッズ"))
        if odd is None or odd <= 0:
            continue

        targets: list[str] = []
        if mode == "contains":
            targets = [h for h in combo if h in data]
        elif mode == "position" and position is not None:
            if len(combo) > position and combo[position] in data:
                targets = [combo[position]]

        for horse_no in targets:
            data[horse_no].append(odd)

    return {horse_no: _synthetic_odds(odds_list) for horse_no, odds_list in data.items()}


def _collect_horse_flow_odds_first_column(
    frame: pd.DataFrame,
    horses: list[str],
    excluded: set[str],
    combo_size: int,
) -> dict[str, float | None]:
    data: dict[str, list[float]] = {h: [] for h in horses}
    seen_keys: set[tuple[str, ...]] = set()
    if frame is None or frame.empty or not {"組み合わせ", "オッズ"}.issubset(set(frame.columns)):
        return {h: None for h in horses}

    for _, row in frame.iterrows():
        combo = _combo_numbers(row.get("組み合わせ"))
        if len(combo) != combo_size or any(item in excluded for item in combo):
            continue

        first = combo[0]
        if first not in data:
            continue

        # 順不同券種を順序展開したデータでは、三連複は同じ先頭馬で2重順列が出るため圧縮する。
        # 例: 1-2-3, 1-3-2 は同一イベントとして1回のみ採用。
        key = (first, *sorted(combo[1:]))
        if key in seen_keys:
            continue
        seen_keys.add(key)

        odd = _parse_odds_value(row.get("オッズ"))
        if odd is None or odd <= 0:
            continue
        data[first].append(odd)

    return {horse_no: _synthetic_odds(odds_list) for horse_no, odds_list in data.items()}


def _combine_synthetic_maps(*maps: dict[str, float | None]) -> dict[str, float | None]:
    keys: set[str] = set()
    for item in maps:
        keys.update(item.keys())

    out: dict[str, float | None] = {}
    for key in keys:
        values = [item.get(key) for item in maps]
        odds_values = [value for value in values if value is not None and value > 0]
        out[key] = _synthetic_odds(odds_values)
    return out


def _collect_trifecta_box_flow_odds(
    frame: pd.DataFrame,
    horses: list[str],
    excluded: set[str],
) -> dict[str, float | None]:
    data: dict[str, list[float]] = {h: [] for h in horses}
    trio_odds_map: dict[tuple[str, str, str], list[float]] = {}

    if frame is None or frame.empty or not {"組み合わせ", "オッズ"}.issubset(set(frame.columns)):
        return {h: None for h in horses}

    for _, row in frame.iterrows():
        combo = _combo_numbers(row.get("組み合わせ"))
        if len(combo) != 3 or any(item in excluded for item in combo):
            continue

        odd = _parse_odds_value(row.get("オッズ"))
        if odd is None or odd <= 0:
            continue

        unordered_key = tuple(sorted(combo))
        trio_odds_map.setdefault(unordered_key, []).append(odd)

    for trio, odds_list in trio_odds_map.items():
        synth_box = _synthetic_odds(odds_list)
        if synth_box is None:
            continue
        for horse_no in trio:
            if horse_no in data:
                data[horse_no].append(synth_box)

    return {horse_no: _synthetic_odds(odds_list) for horse_no, odds_list in data.items()}


def _build_pair_compare(
    umaren: pd.DataFrame | None,
    umatan: pd.DataFrame | None,
    sanrentan: pd.DataFrame | None,
    horse_name_map: dict[str, str],
    horses: list[str],
    excluded: set[str],
) -> pd.DataFrame:
    umaren_dir_map: dict[tuple[str, str], float] = {}
    if umaren is not None and not umaren.empty and {"組み合わせ", "オッズ"}.issubset(set(umaren.columns)):
        for _, row in umaren.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 2 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                a, b = nums[0], nums[1]
                umaren_dir_map[(a, b)] = odd
                umaren_dir_map[(b, a)] = odd

    umatan_dir_map: dict[tuple[str, str], float] = {}
    if umatan is not None and not umatan.empty and {"組み合わせ", "オッズ"}.issubset(set(umatan.columns)):
        for _, row in umatan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 2 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                umatan_dir_map[(nums[0], nums[1])] = odd

    sanrentan_map: dict[tuple[str, str, str], float] = {}
    if sanrentan is not None and not sanrentan.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrentan.columns)):
        for _, row in sanrentan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                sanrentan_map[(nums[0], nums[1], nums[2])] = odd

    pair_rows: list[dict[str, object]] = []
    all_pairs = set(umaren_dir_map.keys()) | set(umatan_dir_map.keys())

    for a, b in sorted(all_pairs, key=lambda x: (_horse_sort_key(x[0]), _horse_sort_key(x[1]))):
        ab = umatan_dir_map.get((a, b))
        ba = umatan_dir_map.get((b, a))
        synth_umatan = _synthetic_odds([x for x in [ab, ba] if x is not None])
        umaren_odd = umaren_dir_map.get((a, b))

        sanrentan_top2_any_third_odds: list[float] = []
        for c in horses:
            if c in {a, b}:
                continue
            ab_c = sanrentan_map.get((a, b, c))
            ba_c = sanrentan_map.get((b, a, c))
            if ab_c is not None:
                sanrentan_top2_any_third_odds.append(ab_c)
            if ba_c is not None:
                sanrentan_top2_any_third_odds.append(ba_c)

        synth_top2_any_third = _synthetic_odds(sanrentan_top2_any_third_odds)

        pair_rows.append(
            {
                "馬番A": int(a) if a.isdigit() else a,
                "馬名A": horse_name_map.get(a, ""),
                "馬番B": int(b) if b.isdigit() else b,
                "馬名B": horse_name_map.get(b, ""),
                "馬連オッズ": round(umaren_odd, 4) if umaren_odd is not None else None,
                "馬単表裏合成オッズ": round(synth_umatan, 4) if synth_umatan is not None else None,
                "三連単1-2着裏表3着全流し合成オッズ": round(synth_top2_any_third, 4) if synth_top2_any_third is not None else None,
            }
        )

    pair_df = pd.DataFrame(pair_rows)
    if pair_df.empty:
        return pair_df
    return _add_spread_column(pair_df, ["馬連オッズ", "馬単表裏合成オッズ", "三連単1-2着裏表3着全流し合成オッズ"])


def _build_exacta_compare(
    umatan: pd.DataFrame | None,
    sanrentan: pd.DataFrame | None,
    horse_name_map: dict[str, str],
    horses: list[str],
    excluded: set[str],
) -> pd.DataFrame:
    umatan_dir_map: dict[tuple[str, str], float] = {}
    if umatan is not None and not umatan.empty and {"組み合わせ", "オッズ"}.issubset(set(umatan.columns)):
        for _, row in umatan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 2 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                umatan_dir_map[(nums[0], nums[1])] = odd

    sanrentan_map: dict[tuple[str, str, str], float] = {}
    if sanrentan is not None and not sanrentan.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrentan.columns)):
        for _, row in sanrentan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                sanrentan_map[(nums[0], nums[1], nums[2])] = odd

    rows: list[dict[str, object]] = []
    for a, b in sorted(umatan_dir_map.keys(), key=lambda x: (_horse_sort_key(x[0]), _horse_sort_key(x[1]))):
        third_odds: list[float] = []
        for c in horses:
            if c in {a, b}:
                continue
            value = sanrentan_map.get((a, b, c))
            if value is not None:
                third_odds.append(value)

        synth_third = _synthetic_odds(third_odds)
        rows.append(
            {
                "馬番A": int(a) if a.isdigit() else a,
                "馬名A": horse_name_map.get(a, ""),
                "馬番B": int(b) if b.isdigit() else b,
                "馬名B": horse_name_map.get(b, ""),
                "馬単オッズ": round(umatan_dir_map[(a, b)], 4),
                "三連単3着全流し合成オッズ": round(synth_third, 4) if synth_third is not None else None,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return _add_spread_column(frame, ["馬単オッズ", "三連単3着全流し合成オッズ"])


def _build_pair_extension_compare(
    umaren: pd.DataFrame | None,
    sanrentan: pd.DataFrame | None,
    horse_name_map: dict[str, str],
    horses: list[str],
    excluded: set[str],
) -> pd.DataFrame:
    def pair_key(x: str, y: str) -> tuple[str, str]:
        return tuple(sorted((x, y), key=_horse_sort_key))

    umaren_map: dict[tuple[str, str], float] = {}
    if umaren is not None and not umaren.empty and {"組み合わせ", "オッズ"}.issubset(set(umaren.columns)):
        for _, row in umaren.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 2 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                umaren_map[pair_key(nums[0], nums[1])] = odd

    sanrentan_map: dict[tuple[str, str, str], float] = {}
    if sanrentan is not None and not sanrentan.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrentan.columns)):
        for _, row in sanrentan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                sanrentan_map[(nums[0], nums[1], nums[2])] = odd

    rows: list[dict[str, object]] = []
    for idx_a in range(len(horses)):
        for idx_b in range(idx_a + 1, len(horses)):
            a, b = horses[idx_a], horses[idx_b]

            top13_any_second: list[float] = []
            bottom23_any_first: list[float] = []
            for c in horses:
                if c in {a, b}:
                    continue
                for key in [(a, c, b), (b, c, a)]:
                    value = sanrentan_map.get(key)
                    if value is not None:
                        top13_any_second.append(value)
                for key in [(c, a, b), (c, b, a)]:
                    value = sanrentan_map.get(key)
                    if value is not None:
                        bottom23_any_first.append(value)

            rows.append(
                {
                    "馬番A": int(a) if a.isdigit() else a,
                    "馬名A": horse_name_map.get(a, ""),
                    "馬番B": int(b) if b.isdigit() else b,
                    "馬名B": horse_name_map.get(b, ""),
                    "馬連オッズ": round(umaren_map.get(pair_key(a, b)), 4) if umaren_map.get(pair_key(a, b)) is not None else None,
                    "三連単1-3着裏表2着全流し合成オッズ": round(_synthetic_odds(top13_any_second), 4)
                    if _synthetic_odds(top13_any_second) is not None
                    else None,
                    "三連単2-3着裏表1着全流し合成オッズ": round(_synthetic_odds(bottom23_any_first), 4)
                    if _synthetic_odds(bottom23_any_first) is not None
                    else None,
                }
            )

    return pd.DataFrame(rows)


def _build_exacta_extension_compare(
    umatan: pd.DataFrame | None,
    sanrentan: pd.DataFrame | None,
    horse_name_map: dict[str, str],
    horses: list[str],
    excluded: set[str],
) -> pd.DataFrame:
    umatan_dir_map: dict[tuple[str, str], float] = {}
    if umatan is not None and not umatan.empty and {"組み合わせ", "オッズ"}.issubset(set(umatan.columns)):
        for _, row in umatan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 2 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                umatan_dir_map[(nums[0], nums[1])] = odd

    sanrentan_map: dict[tuple[str, str, str], float] = {}
    if sanrentan is not None and not sanrentan.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrentan.columns)):
        for _, row in sanrentan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                sanrentan_map[(nums[0], nums[1], nums[2])] = odd

    rows: list[dict[str, object]] = []
    for a, b in sorted(umatan_dir_map.keys(), key=lambda x: (_horse_sort_key(x[0]), _horse_sort_key(x[1]))):
        first_all: list[float] = []
        second_all: list[float] = []
        for c in horses:
            if c in {a, b}:
                continue
            v1 = sanrentan_map.get((c, a, b))
            v2 = sanrentan_map.get((a, c, b))
            if v1 is not None:
                first_all.append(v1)
            if v2 is not None:
                second_all.append(v2)

        rows.append(
            {
                "馬番A": int(a) if a.isdigit() else a,
                "馬名A": horse_name_map.get(a, ""),
                "馬番B": int(b) if b.isdigit() else b,
                "馬名B": horse_name_map.get(b, ""),
                "馬単オッズ": round(umatan_dir_map[(a, b)], 4),
                "三連単1着全流し合成オッズ": round(_synthetic_odds(first_all), 4) if _synthetic_odds(first_all) is not None else None,
                "三連単2着全流し合成オッズ": round(_synthetic_odds(second_all), 4) if _synthetic_odds(second_all) is not None else None,
            }
        )

    return pd.DataFrame(rows)


def _build_wide_compare(
    wide: pd.DataFrame | None,
    sanrenpuku: pd.DataFrame | None,
    sanrentan: pd.DataFrame | None,
    horse_name_map: dict[str, str],
    horses: list[str],
    excluded: set[str],
) -> pd.DataFrame:
    def pair_key(x: str, y: str) -> tuple[str, str]:
        return tuple(sorted((x, y), key=_horse_sort_key))

    wide_map: dict[tuple[str, str], float] = {}
    if wide is not None and not wide.empty and {"組み合わせ", "オッズ"}.issubset(set(wide.columns)):
        for _, row in wide.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 2 or any(n in excluded for n in nums):
                continue
            key = pair_key(nums[0], nums[1])
            if key in wide_map:
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                wide_map[key] = odd

    trio_axis_map: dict[tuple[str, str], list[float]] = {}
    if sanrenpuku is not None and not sanrenpuku.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrenpuku.columns)):
        seen_trios: set[tuple[str, str, str]] = set()
        for _, row in sanrenpuku.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            trio_key = tuple(sorted(nums))
            if trio_key in seen_trios:
                continue
            seen_trios.add(trio_key)
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is None or odd <= 0:
                continue
            a, b, c = trio_key
            for pair in [pair_key(a, b), pair_key(a, c), pair_key(b, c)]:
                trio_axis_map.setdefault(pair, []).append(odd)

    trifecta_multi_map: dict[tuple[str, str], list[float]] = {}
    if sanrentan is not None and not sanrentan.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrentan.columns)):
        for _, row in sanrentan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is None or odd <= 0:
                continue
            a, b, c = nums
            for pair in [pair_key(a, b), pair_key(a, c), pair_key(b, c)]:
                trifecta_multi_map.setdefault(pair, []).append(odd)

    rows: list[dict[str, object]] = []
    for idx_a in range(len(horses)):
        for idx_b in range(idx_a + 1, len(horses)):
            a, b = horses[idx_a], horses[idx_b]
            key = pair_key(a, b)
            trio_synth = _synthetic_odds(trio_axis_map.get(key, []))
            trifecta_synth = _synthetic_odds(trifecta_multi_map.get(key, []))
            rows.append(
                {
                    "馬番A": int(a) if a.isdigit() else a,
                    "馬名A": horse_name_map.get(a, ""),
                    "馬番B": int(b) if b.isdigit() else b,
                    "馬名B": horse_name_map.get(b, ""),
                    "ワイドオッズ": round(wide_map.get(key), 4) if wide_map.get(key) is not None else None,
                    "三連複2頭軸流し合成オッズ": round(trio_synth, 4) if trio_synth is not None else None,
                    "三連単2頭軸マルチ合成オッズ": round(trifecta_synth, 4) if trifecta_synth is not None else None,
                }
            )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return _add_spread_column(frame, ["ワイドオッズ", "三連複2頭軸流し合成オッズ", "三連単2頭軸マルチ合成オッズ"])


def _build_trio_compare(
    sanrenpuku: pd.DataFrame | None,
    sanrentan: pd.DataFrame | None,
    horse_name_map: dict[str, str],
    horses: list[str],
    excluded: set[str],
) -> pd.DataFrame:
    trio_map: dict[tuple[str, str, str], float] = {}
    if sanrenpuku is not None and not sanrenpuku.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrenpuku.columns)):
        for _, row in sanrenpuku.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            key = tuple(sorted(nums))
            if key in trio_map:
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is not None and odd > 0:
                trio_map[key] = odd

    trifecta_box_map: dict[tuple[str, str, str], list[float]] = {}
    if sanrentan is not None and not sanrentan.empty and {"組み合わせ", "オッズ"}.issubset(set(sanrentan.columns)):
        for _, row in sanrentan.iterrows():
            nums = _combo_numbers(row.get("組み合わせ"))
            if len(nums) != 3 or any(n in excluded for n in nums):
                continue
            odd = _parse_odds_value(row.get("オッズ"))
            if odd is None or odd <= 0:
                continue
            key = tuple(sorted(nums))
            trifecta_box_map.setdefault(key, []).append(odd)

    rows: list[dict[str, object]] = []
    for idx_a in range(len(horses)):
        for idx_b in range(idx_a + 1, len(horses)):
            for idx_c in range(idx_b + 1, len(horses)):
                a, b, c = horses[idx_a], horses[idx_b], horses[idx_c]
                trio_key = tuple(sorted((a, b, c)))
                trifecta_box = _synthetic_odds(trifecta_box_map.get(trio_key, []))
                rows.append(
                    {
                        "馬番A": int(a) if a.isdigit() else a,
                        "馬名A": horse_name_map.get(a, ""),
                        "馬番B": int(b) if b.isdigit() else b,
                        "馬名B": horse_name_map.get(b, ""),
                        "馬番C": int(c) if c.isdigit() else c,
                        "馬名C": horse_name_map.get(c, ""),
                        "三連複オッズ": round(trio_map.get(trio_key), 4) if trio_map.get(trio_key) is not None else None,
                        "三連単3頭ボックス合成オッズ": round(trifecta_box, 4) if trifecta_box is not None else None,
                    }
                )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return _add_spread_column(frame, ["三連複オッズ", "三連単3頭ボックス合成オッズ"])


def _build_horse_master(entries: list[dict[str, object]], tansho_frame: pd.DataFrame, excluded: set[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if not tansho_frame.empty and {"馬番", "馬名"}.issubset(set(tansho_frame.columns)):
        for _, row in tansho_frame.iterrows():
            horse_no = _normalize_horse_no(row.get("馬番", ""))
            if horse_no and horse_no not in excluded:
                rows.append({"馬番": horse_no, "馬名": str(row.get("馬名", "")).strip()})
    else:
        for row in entries:
            horse_no = _normalize_horse_no(row.get("馬番", row.get("col_2", "")))
            horse_name = str(row.get("馬名", row.get("col_4", ""))).strip()
            if horse_no and horse_name and horse_no not in excluded:
                rows.append({"馬番": horse_no, "馬名": horse_name})

    frame = pd.DataFrame(rows).drop_duplicates(subset=["馬番"], keep="first")
    if frame.empty:
        raise ValueError("馬番・馬名の抽出に失敗しました")
    frame["馬番_num"] = pd.to_numeric(frame["馬番"], errors="coerce")
    frame = frame.sort_values(by=["馬番_num"]).reset_index(drop=True)
    return frame


def build_comparisons(
    odds: dict[str, list[dict[str, object]]],
    entries: list[dict[str, object]],
    excluded_horses: list[str] | None = None,
) -> dict[str, list[dict[str, object]]]:
    excluded = {_normalize_horse_no(x) for x in (excluded_horses or []) if _normalize_horse_no(x)}

    frames = {bet_type: pd.DataFrame(odds.get(bet_type, [])) for bet_type in BET_TYPES}
    tansho = frames.get("単勝", pd.DataFrame())
    fukusho = frames.get("複勝", pd.DataFrame())

    tansho_map: dict[str, float | None] = {}
    if not tansho.empty and {"馬番", "オッズ"}.issubset(set(tansho.columns)):
        for _, row in tansho.iterrows():
            horse_no = _normalize_horse_no(row.get("馬番", ""))
            if horse_no:
                tansho_map[horse_no] = _parse_odds_value(row.get("オッズ"))

    fukusho_map: dict[str, float | None] = {}
    if not fukusho.empty and {"馬番", "オッズ"}.issubset(set(fukusho.columns)):
        for _, row in fukusho.iterrows():
            horse_no = _normalize_horse_no(row.get("馬番", ""))
            if horse_no and horse_no not in excluded:
                fukusho_map[horse_no] = _parse_odds_value(row.get("オッズ"))

    master = _build_horse_master(entries, tansho, excluded)
    master["単勝オッズ"] = master["馬番"].astype(str).map(tansho_map)

    horse_numbers = [str(x) for x in master["馬番"].tolist()]
    horse_name_map = {str(row["馬番"]): row["馬名"] for _, row in master.iterrows()}

    umatan_first = _collect_horse_flow_odds(frames.get("馬単", pd.DataFrame()), horse_numbers, excluded, mode="position", position=0)
    umatan_second = _collect_horse_flow_odds(frames.get("馬単", pd.DataFrame()), horse_numbers, excluded, mode="position", position=1)
    sanrentan_first = _collect_horse_flow_odds(frames.get("三連単", pd.DataFrame()), horse_numbers, excluded, mode="position", position=0)
    sanrentan_second = _collect_horse_flow_odds(frames.get("三連単", pd.DataFrame()), horse_numbers, excluded, mode="position", position=1)
    sanrentan_third = _collect_horse_flow_odds(frames.get("三連単", pd.DataFrame()), horse_numbers, excluded, mode="position", position=2)
    sanrentan_any_pos = _combine_synthetic_maps(sanrentan_first, sanrentan_second, sanrentan_third)
    umaren_flow = _collect_horse_flow_odds_first_column(frames.get("馬連", pd.DataFrame()), horse_numbers, excluded, combo_size=2)
    wide_flow = _collect_horse_flow_odds_first_column(frames.get("ワイド", pd.DataFrame()), horse_numbers, excluded, combo_size=2)
    sanrenpuku_flow = _collect_horse_flow_odds_first_column(frames.get("三連複", pd.DataFrame()), horse_numbers, excluded, combo_size=3)

    all_market_compare = master[["馬番", "馬名", "単勝オッズ"]].copy()
    all_market_compare["複勝オッズ"] = all_market_compare["馬番"].astype(str).map(fukusho_map)
    all_market_compare["馬連流し合成オッズ"] = all_market_compare["馬番"].astype(str).map(umaren_flow)
    all_market_compare["ワイド流し合成オッズ"] = all_market_compare["馬番"].astype(str).map(wide_flow)
    all_market_compare["馬単(1着流し)合成オッズ"] = all_market_compare["馬番"].astype(str).map(umatan_first)
    all_market_compare["馬単(2着流し)合成オッズ"] = all_market_compare["馬番"].astype(str).map(umatan_second)
    all_market_compare["馬単表裏合成オッズ"] = all_market_compare["馬番"].astype(str).map(
        _combine_synthetic_maps(umatan_first, umatan_second)
    )
    all_market_compare["三連複流し合成オッズ"] = all_market_compare["馬番"].astype(str).map(sanrenpuku_flow)
    all_market_compare["三連単(1着流し)合成オッズ"] = all_market_compare["馬番"].astype(str).map(sanrentan_first)
    all_market_compare["三連単(2着流し)合成オッズ"] = all_market_compare["馬番"].astype(str).map(sanrentan_second)
    all_market_compare["三連単(3着流し)合成オッズ"] = all_market_compare["馬番"].astype(str).map(sanrentan_third)
    all_market_compare["三連単1頭軸マルチ合成オッズ"] = all_market_compare["馬番"].astype(str).map(sanrentan_any_pos)
    all_market_compare["馬番"] = pd.to_numeric(all_market_compare["馬番"], errors="coerce").astype("Int64")

    compare1 = master[["馬番", "馬名", "単勝オッズ"]].copy()
    compare1["馬単(1着流し)合成オッズ"] = compare1["馬番"].astype(str).map(umatan_first)
    compare1["三連単(1着流し)合成オッズ"] = compare1["馬番"].astype(str).map(sanrentan_first)
    compare1["馬番"] = pd.to_numeric(compare1["馬番"], errors="coerce").astype("Int64")
    compare1 = _add_spread_column(compare1, ["単勝オッズ", "馬単(1着流し)合成オッズ", "三連単(1着流し)合成オッズ"])

    compare2 = master[["馬番", "馬名"]].copy()
    compare2["複勝オッズ"] = compare2["馬番"].astype(str).map(fukusho_map)
    compare2["三連複流し合成オッズ"] = compare2["馬番"].astype(str).map(sanrenpuku_flow)
    compare2["三連単1頭軸マルチ合成オッズ"] = compare2["馬番"].astype(str).map(sanrentan_any_pos)
    compare2["馬番"] = pd.to_numeric(compare2["馬番"], errors="coerce").astype("Int64")
    compare2 = _add_spread_column(compare2, ["複勝オッズ", "三連複流し合成オッズ", "三連単1頭軸マルチ合成オッズ"])

    compare3 = _build_pair_compare(
        frames.get("馬連", pd.DataFrame()),
        frames.get("馬単", pd.DataFrame()),
        frames.get("三連単", pd.DataFrame()),
        horse_name_map,
        horse_numbers,
        excluded,
    )
    compare4 = _build_exacta_compare(
        frames.get("馬単", pd.DataFrame()),
        frames.get("三連単", pd.DataFrame()),
        horse_name_map,
        horse_numbers,
        excluded,
    )
    compare5 = _build_wide_compare(
        frames.get("ワイド", pd.DataFrame()),
        frames.get("三連複", pd.DataFrame()),
        frames.get("三連単", pd.DataFrame()),
        horse_name_map,
        horse_numbers,
        excluded,
    )
    compare6 = _build_trio_compare(
        frames.get("三連複", pd.DataFrame()),
        frames.get("三連単", pd.DataFrame()),
        horse_name_map,
        horse_numbers,
        excluded,
    )

    compare1_extended = master[["馬番", "馬名", "単勝オッズ"]].copy()
    compare1_extended["馬単(2着流し)合成オッズ"] = compare1_extended["馬番"].astype(str).map(umatan_second)
    compare1_extended["三連単(2着流し)合成オッズ"] = compare1_extended["馬番"].astype(str).map(sanrentan_second)
    compare1_extended["三連単(3着流し)合成オッズ"] = compare1_extended["馬番"].astype(str).map(sanrentan_third)
    compare1_extended["馬番"] = pd.to_numeric(compare1_extended["馬番"], errors="coerce").astype("Int64")

    compare3_extended = _build_pair_extension_compare(
        frames.get("馬連", pd.DataFrame()),
        frames.get("三連単", pd.DataFrame()),
        horse_name_map,
        horse_numbers,
        excluded,
    )

    compare4_extended = _build_exacta_extension_compare(
        frames.get("馬単", pd.DataFrame()),
        frames.get("三連単", pd.DataFrame()),
        horse_name_map,
        horse_numbers,
        excluded,
    )

    return {
        "all_market_compare": all_market_compare.to_dict(orient="records"),
        "compare1": compare1.to_dict(orient="records"),
        "compare2": compare2.to_dict(orient="records"),
        "compare3": compare3.to_dict(orient="records"),
        "compare4": compare4.to_dict(orient="records"),
        "compare5": compare5.to_dict(orient="records"),
        "compare6": compare6.to_dict(orient="records"),
        "compare1_extended": compare1_extended.to_dict(orient="records"),
        "compare3_extended": compare3_extended.to_dict(orient="records"),
        "compare4_extended": compare4_extended.to_dict(orient="records"),
    }
