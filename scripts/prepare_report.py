#!/usr/bin/env python3
"""Validate a checked weekly input, calculate ratios, and render seven SOP charts."""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle


BLUE = "#3370ff"
PALE = "#f0f3ff"
GREEN = "#1a9c48"
RED = "#d32f2f"
INK = "#1f2329"
MUTED = "#646a73"
REQUIRED_UV = ("poweron", "audio_total", "video_total", "native_audio", "store_video")
CHARTS = (
    "音频-各音源UV占比.png",
    "音频-各音源渗透率.png",
    "音乐各音源周度运营数据明细.png",
    "视频-各APP-UV占比.png",
    "视频-各APP渗透率.png",
    "X-Pad-TOP10.png",
    "浏览器-TOP10.png",
)


def fail(message: str) -> None:
    raise ValueError(message)


def number(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{label} 必须是数字")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        fail(f"{label} 必须是有限的{'正' if positive else '非负'}数")
    return result


def day(value: object, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD 日期") from exc


def period(obj: object, label: str) -> tuple[date, date]:
    if not isinstance(obj, dict):
        fail(f"{label} 必须包含 start/end")
    start, end = day(obj.get("start"), f"{label}.start"), day(obj.get("end"), f"{label}.end")
    if start.weekday() != 3 or end != start + timedelta(days=6):
        fail(f"{label} 必须从周四至次周三，恰好 7 天")
    return start, end


def validate(data: object) -> dict:
    if not isinstance(data, dict):
        fail("输入根节点必须是对象")
    periods = data.get("periods", {})
    if not isinstance(periods, dict):
        fail("periods 必须是对象")
    previous = period(periods.get("previous"), "previous")
    current = period(periods.get("current"), "current")
    if current[0] != previous[1] + timedelta(days=1):
        fail("对比期必须紧邻本期")
    scope = data.get("scope", {})
    if not isinstance(scope, dict) or scope.get("official_delivery") is not True:
        fail("scope.official_delivery 必须明确为 true")
    versions = scope.get("cdu_versions_with_rows")
    if not isinstance(versions, list) or not versions or not all(isinstance(v, str) and v.strip() for v in versions):
        fail("需要填写实际有数据的 CDU 版本列表")
    sources = data.get("sources")
    if not isinstance(sources, dict) or not all(isinstance(sources.get(k), str) and sources[k].strip() for k in ("north_star", "app_detail", "poweron")):
        fail("sources 必须记录北极星、应用明细、上电车辆三类来源")
    coverage = data.get("coverage", {})
    if not isinstance(coverage, dict):
        fail("coverage 必须是对象")
    for label, (start, _) in (("previous", previous), ("current", current)):
        actual = coverage.get(label)
        expected = [(start + timedelta(days=i)).isoformat() for i in range(7)]
        if not isinstance(actual, list) or sorted(actual) != expected:
            fail(f"coverage.{label} 未覆盖该期全部 7 天，或存在重复/错期日期")
    north = data.get("north_star_pct", {})
    if not isinstance(north, dict):
        fail("north_star_pct 必须是对象")
    for name in ("overall", "audio", "video"):
        pair = north.get(name, {})
        if not isinstance(pair, dict):
            fail(f"north_star_pct.{name} 必须有两期值")
        for label in ("previous", "current"):
            value = number(pair.get(label), f"north_star_pct.{name}.{label}")
            if value > 100:
                fail(f"north_star_pct.{name}.{label} 超过 100%")
    uv = data.get("mean_daily_uv", {})
    if not isinstance(uv, dict):
        fail("mean_daily_uv 必须是对象")
    for name in REQUIRED_UV:
        pair = uv.get(name, {})
        if not isinstance(pair, dict):
            fail(f"mean_daily_uv.{name} 必须有两期值")
        for label in ("previous", "current"):
            number(pair.get(label), f"mean_daily_uv.{name}.{label}", positive=True)
    for name in ("audio_sources", "video_apps", "xpad_top10", "browser_top10"):
        rows = data.get(name)
        if not isinstance(rows, list) or not rows:
            fail(f"{name} 必须是非空数组")
        if name.endswith("top10") and len(rows) != 10:
            fail(f"{name} 必须正好 10 项")
        seen = set()
        for index, row in enumerate(rows, 1):
            if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"].strip():
                fail(f"{name}[{index}] 缺应用名")
            if row["name"] in seen:
                fail(f"{name} 中应用名重复：{row['name']}")
            seen.add(row["name"])
            for label in ("previous", "current"):
                number(row.get(label), f"{name}[{index}].{label}")
            if name in ("audio_sources", "video_apps"):
                if not isinstance(row.get("group"), str) or not row["group"].strip():
                    fail(f"{name}[{index}] 缺分组")
            else:
                rank = row.get("previous_rank")
                if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
                    fail(f"{name}[{index}] 缺上期排名")
        if name.endswith("top10"):
            values = [row["current"] for row in rows]
            if values != sorted(values, reverse=True):
                fail(f"{name} 需要按本期 UV 降序排列")
    return data


def compute(data: dict) -> dict:
    uv = data["mean_daily_uv"]
    result = {key: data[key] for key in ("periods", "scope", "sources", "coverage", "north_star_pct")}
    result["formulas"] = {
        "north_star": "看板每日占比的 7 天算术平均；输入值为已核实周值",
        "breakdown_share": "应用周日均去重 UV / 业务总盘周日均去重 UV",
        "vehicle_penetration": "音频/视频业务总盘或单应用周日均去重 UV / 同期上电车辆周日均去重 UV；组周报使用业务总盘值",
    }
    result["mean_daily_uv"] = uv
    result["summary"] = {}
    for name, numerator, denominator in (("audio_penetration", "audio_total", "poweron"), ("video_penetration", "video_total", "poweron"), ("native_audio_ratio_of_means", "native_audio", "audio_total"), ("store_video_ratio_of_means", "store_video", "video_total")):
        values = {p: 100 * uv[numerator][p] / uv[denominator][p] for p in ("previous", "current")}
        values["change_pp"] = values["current"] - values["previous"]
        result["summary"][name] = values
    for name, denominator in (("audio_sources", "audio_total"), ("video_apps", "video_total")):
        output = []
        for row in data[name]:
            item = dict(row)
            item["previous_share_pct"] = 100 * row["previous"] / uv[denominator]["previous"]
            item["current_share_pct"] = 100 * row["current"] / uv[denominator]["current"]
            item["share_change_pp"] = item["current_share_pct"] - item["previous_share_pct"]
            for p in ("previous", "current"):
                item[f"{p}_penetration_pct"] = 100 * row[p] / uv["poweron"][p]
            item["penetration_change_pp"] = item["current_penetration_pct"] - item["previous_penetration_pct"]
            item["uv_change_pct"] = None if row["previous"] == 0 else 100 * (row["current"] / row["previous"] - 1)
            output.append(item)
        result[name] = output
    for name in ("xpad_top10", "browser_top10"):
        output = []
        for rank, row in enumerate(data[name], 1):
            item = dict(row)
            item["current_rank"] = rank
            item["rank_change"] = row["previous_rank"] - rank
            item["uv_change_pct"] = None if row["previous"] == 0 else 100 * (row["current"] / row["previous"] - 1)
            output.append(item)
        result[name] = output
    result["notes"] = data.get("notes", [])
    result["demo_only"] = data.get("demo_only", False)
    return result


def pick_font() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ("Noto Sans CJK SC", "Noto Sans CJK JP", "Microsoft YaHei", "PingFang SC", "Heiti SC", "STHeiti"):
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def fmt_uv(value: float) -> str:
    return f"{value:,.0f}"


def fmt_change(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    return f"{'▲' if value > 0 else '▼' if value < 0 else '—'} {value:+.2f}{unit}" if value else "—"


def draw_table(path: Path, title: str, subtitle: str, headers: list[str], rows: list[list[str]], widths: list[float], size: tuple[int, int], footer: str, group_indices: set[int] | None = None) -> None:
    w, h = size
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(.04, .972, title, fontsize=30, fontweight="bold", color=INK, va="top")
    ax.add_patch(Rectangle((.04, .941), .92, .003, color=BLUE, linewidth=0))
    ax.text(.04, .922, subtitle, fontsize=16, color=MUTED, va="top", linespacing=1.5)
    top, bottom = .82, .13
    n = len(rows) + 1
    height = (top - bottom) / max(n, 1)
    starts = [.04]
    for value in widths:
        starts.append(starts[-1] + .92 * value)
    ax.add_patch(Rectangle((.04, top - height), .92, height, color=BLUE, linewidth=0))
    for j, label in enumerate(headers):
        ax.text(starts[j] + .007, top - height / 2, label, fontsize=14, color="white", fontweight="bold", va="center", ha="left")
    for i, row in enumerate(rows):
        y = top - (i + 2) * height
        if group_indices and i in group_indices:
            color = "#e4ebff"
        else:
            color = PALE if i % 2 == 0 else "white"
        ax.add_patch(Rectangle((.04, y), .92, height, color=color, linewidth=0))
        for j, value in enumerate(row):
            ink = GREEN if value.startswith("▲") else RED if value.startswith("▼") else INK
            ax.text(starts[j] + .007, y + height / 2, str(value), fontsize=13 if len(headers) <= 5 else 11, color=ink, va="center", ha="left")
        ax.plot([.04, .96], [y, y], color="#dfe4ed", linewidth=.6)
    ax.text(.04, .096, footer, fontsize=14, color=MUTED, va="top", wrap=True, linespacing=1.35)
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)


def period_label(data: dict) -> str:
    p = data["periods"]
    return f"本期 {p['current']['start']}—{p['current']['end']}  ·  对比期 {p['previous']['start']}—{p['previous']['end']}\n正式交付车 · CDU {', '.join(data['scope']['cdu_versions_with_rows'])} · 两期各 7 天 · 周日均去重 UV"


def group_rows(items: list[dict], mode: str) -> tuple[list[list[str]], set[int]]:
    output, groups = [], set()
    last_group = None
    for index, row in enumerate(items, 1):
        group = row["group"]
        if group != last_group:
            groups.add(index - 1)
            last_group = group
        field = "share" if mode == "share" else "penetration"
        output.append([
            group,
            row["name"],
            f"{row[f'current_{field}_pct']:.2f}%",
            f"{fmt_uv(row['previous'])} → {fmt_uv(row['current'])}",
            fmt_change(row[f"{field}_change_pp"], "pp"),
        ])
    return output, groups


def movement_summary(items: list[dict], field: str, unit: str) -> str:
    ordered = sorted(items, key=lambda row: row[field])
    low, high = ordered[0], ordered[-1]
    return f"变化最大：{high['name']} {high[field]:+.2f}{unit}；变化最小：{low['name']} {low[field]:+.2f}{unit}。跨应用用户可能重叠。"


def render(data: dict, out_dir: Path) -> None:
    pick_font()
    subtitle = period_label(data)
    for key, title, denom, dimensions in (
        ("audio_sources", "音频 · 各音源 UV 占比", "音频总盘周日均去重 UV", (1720, 3020)),
        ("audio_sources", "音频 · 各音源车辆渗透率", "上电车辆周日均去重 UV", (1720, 3020)),
        ("video_apps", "视频 · 各 APP UV 占比", "视频总盘周日均去重 UV", (1720, 2828)),
        ("video_apps", "视频 · 各 APP 车辆渗透率", "上电车辆周日均去重 UV", (1720, 2828)),
    ):
        mode = "share" if "UV 占比" in title else "penetration"
        rows, groups = group_rows(data[key], mode)
        filename = {("audio_sources", "share"): CHARTS[0], ("audio_sources", "penetration"): CHARTS[1], ("video_apps", "share"): CHARTS[3], ("video_apps", "penetration"): CHARTS[4]}[(key, mode)]
        field = "share_change_pp" if mode == "share" else "penetration_change_pp"
        draw_table(out_dir / filename, title, subtitle + f"\n分母：{denom}", ["分类", "音源 / 应用", "本周比率", "上周 → 本周 UV", "变化"], rows, [.15, .27, .14, .28, .16], dimensions, movement_summary(data[key], field, "pp"), groups)
    music_rows = []
    for row in data["audio_sources"]:
        music_rows.append([
            row["group"], row["name"], fmt_uv(row["previous"]), fmt_uv(data["mean_daily_uv"]["poweron"]["previous"]),
            f"{row['previous_penetration_pct']:.2f}%", fmt_uv(row["current"]), fmt_uv(data["mean_daily_uv"]["poweron"]["current"]),
            f"{row['current_penetration_pct']:.2f}%", fmt_change(row["penetration_change_pp"], "pp"),
        ])
    audio_pen = data["summary"]["audio_penetration"]
    native_ratio = data["summary"]["native_audio_ratio_of_means"]
    sorted_audio = sorted(data["audio_sources"], key=lambda row: row["penetration_change_pp"])
    music_footer = "\n".join((
        f"1. 音频总盘车辆渗透率 {audio_pen['previous']:.2f}% → {audio_pen['current']:.2f}%，变化 {audio_pen['change_pp']:+.2f}pp。",
        f"2. 原生音频占总盘的周均 UV 比值 {native_ratio['previous']:.2f}% → {native_ratio['current']:.2f}%。",
        f"3. 音源渗透率增幅最大：{sorted_audio[-1]['name']} {sorted_audio[-1]['penetration_change_pp']:+.2f}pp。",
        f"4. 音源渗透率增幅最小：{sorted_audio[0]['name']} {sorted_audio[0]['penetration_change_pp']:+.2f}pp；跨音源车辆可重叠。",
    ))
    draw_table(out_dir / CHARTS[2], "音乐各音源周度运营数据明细", subtitle + "\n渗透率分母：上电车辆周日均去重 UV", ["分组", "音源", "上周UV", "上周车辆", "上周渗透", "本周UV", "本周车辆", "本周渗透", "变化"], music_rows, [.10, .16, .10, .12, .12, .10, .12, .12, .06], (1800, 1884), music_footer)
    for key, title, filename, size in (("xpad_top10", "X-Pad 应用 TOP10", CHARTS[5], (1720, 1568)), ("browser_top10", "浏览器 TOP10", CHARTS[6], (1720, 1496))):
        rows = []
        for row in data[key]:
            movement = row["rank_change"]
            rows.append([str(row["current_rank"]), row["name"], fmt_uv(row["current"]), f"{fmt_uv(row['previous'])} → {fmt_uv(row['current'])} · {fmt_change(row['uv_change_pct'], '%')}", f"{'▲' if movement > 0 else '▼' if movement < 0 else '—'} {abs(movement) if movement else ''}".strip()])
        draw_table(out_dir / filename, title, subtitle + "\n已按本期周日均去重 UV 排序；榜单排除与多包名口径以来源清单为准", ["排名", "应用", "本周 UV", "上周 → 本周 · 环比", "排名变化"], rows, [.07, .29, .14, .34, .16], size, "注：排名变化基于同口径的对比期榜单；核对原始前 15 名及包名合并。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="已核实的周报输入 JSON")
    parser.add_argument("--out-dir", type=Path, required=True, help="输出目录")
    args = parser.parse_args()
    data = validate(json.loads(args.input.read_text(encoding="utf-8")))
    computed = compute(data)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metrics.json").write_text(json.dumps(computed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render(computed, args.out_dir)
    print(f"已校验两期各 7 天，生成 metrics.json 和 {len(CHARTS)} 张图：{args.out_dir}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"输入检查失败：{error}") from error
