#!/usr/bin/env python3
# 内网穿透实测图表：深色主题，中文字体，输出到 figs/
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "figs")
os.makedirs(OUT, exist_ok=True)

# 中文字体
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
if os.path.exists(FONT):
    fp = fm.FontProperties(fname=FONT)
    plt.rcParams["font.family"] = fp.get_name()
plt.rcParams["axes.unicode_minus"] = False

BG = "#0D111C"
INK = "#FFFFFF"
MUTED = "#8A94A6"
GRID = "#1B2233"
CYAN = "#00E5FF"
PURPLE = "#8B5CF6"
ORANGE = "#FF7A59"
AMBER = "#FFC94D"
GREEN = "#3DDC97"
RED = "#FF4D6D"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "savefig.facecolor": BG,
    "font.size": 12,
})

def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=1, alpha=0.7)
    ax.set_axisbelow(True)

def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=160, bbox_inches="tight", pad_inches=0.35)
    fig.savefig(p.replace(".png", ".webp"), dpi=160, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    print("->", p)

# ---------- 图1：TTFB 首字节延迟（跨工具，含对数轴标注托管式） ----------
tools = ["直连基线", "frp", "rathole", "nps", "chisel", "cloudflared"]
p50 = [22.1, 9.4, 15.9, 23.9, 35.0, 1100.0]
p95 = [42.8, 309.9, 21.2, 29.8, 41.9, 2950.4]
colors = [MUTED, CYAN, GREEN, PURPLE, AMBER, RED]
fig, ax = plt.subplots(figsize=(10, 5.4))
x = range(len(tools))
b = ax.bar(x, p50, color=colors, width=0.6, zorder=3)
for i, (v, p9) in enumerate(zip(p50, p95)):
    label = f"{v:.0f}ms" if v < 1000 else f"{v/1000:.1f}s"
    ax.text(i, v * 1.15, label, ha="center", va="bottom", color=INK, fontsize=11, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(tools, fontsize=11)
ax.set_ylabel("首字节时间 p50（ms，cloudflared 为秒）")
ax.set_title("首字节延迟：中继式都在 40ms 内，免费托管式 1 秒起", fontsize=14, pad=16, fontweight="bold")
ax.set_yscale("log"); ax.set_ylim(5, 6000)
style(ax)
fig.tight_layout(); save(fig, "01-latency.png")

# ---------- 图2：单流吞吐（去掉异常 FAIL，取有效中位数） ----------
tools2 = ["直连基线", "frp", "rathole", "chisel", "nps", "cloudflared"]
tput = [7.80, 6.87, 7.47, 7.42, 7.06, 2.29]
colors2 = [MUTED, CYAN, GREEN, AMBER, PURPLE, RED]
fig, ax = plt.subplots(figsize=(10, 5.4))
x = range(len(tools2))
ax.axhline(7.8, color=MUTED, ls="--", lw=1.2, alpha=0.6, zorder=1)
ax.text(5.45, 7.9, "链路天花板 ≈7.8Mbps", color=MUTED, fontsize=10, ha="right")
for i, (v, c) in enumerate(zip(tput, colors2)):
    ax.bar(i, v, color=c, width=0.6, zorder=3)
    ax.text(i, v + 0.15, f"{v:.1f}", ha="center", va="bottom", color=INK, fontsize=11, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(tools2, fontsize=11)
ax.set_ylabel("单流吞吐（Mbps，有效值中位）")
ax.set_ylim(0, 9.5)
ax.set_title("单流吞吐：中继式都顶到链路天花板，托管式受出口影响", fontsize=14, pad=16, fontweight="bold")
style(ax)
fig.tight_layout(); save(fig, "02-throughput.png")

# ---------- 图3：常驻内存 RSS（服务端） ----------
tools3 = ["frp", "nps", "chisel", "rathole"]
rss = [27.0, 21.8, 13.7, 9.1]  # MB
colors3 = [CYAN, PURPLE, AMBER, GREEN]
fig, ax = plt.subplots(figsize=(8.5, 5.0))
x = range(len(tools3))
for i, (v, c) in enumerate(zip(rss, colors3)):
    ax.bar(i, v, color=c, width=0.6, zorder=3)
    ax.text(i, v + 0.4, f"{v:.1f}MB", ha="center", va="bottom", color=INK, fontsize=11, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(tools3, fontsize=12)
ax.set_ylabel("常驻内存 RSS（MB）")
ax.set_ylim(0, 32)
ax.set_title("常驻内存：rathole 只有 frp 的 1/3", fontsize=14, pad=16, fontweight="bold")
style(ax)
fig.tight_layout(); save(fig, "03-memory.png")

# ---------- 图4：配置与可用性（定性评分条形） ----------
tools4 = ["bore", "frp", "rathole", "chisel", "nps", "sish", "cloudflared", "localtunnel"]
# 分数：越高越省事（10=一条命令即刻可用）
ease = [9, 5, 5, 6, 4, 2, 9, 3]
status_col = [GREEN, CYAN, CYAN, CYAN, AMBER, RED, GREEN, RED]
fig, ax = plt.subplots(figsize=(10, 6))
y = range(len(tools4))
for i, (v, c) in enumerate(zip(ease, status_col)):
    ax.barh(i, v, color=c, height=0.6, zorder=3)
    ax.text(v + 0.15, i, f"{v}", va="center", color=INK, fontsize=10, fontweight="bold")
ax.set_yticks(list(y)); ax.set_yticklabels(tools4, fontsize=11)
ax.invert_yaxis()
ax.set_xlabel("上手省事程度（越高越简单，作者主观评分 0-10）")
ax.set_xlim(0, 10.5)
ax.set_title("部署门槛与可用性：红色 = 本次特定环境未跑通", fontsize=14, pad=16, fontweight="bold")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.grid(axis="x", color=GRID, lw=1, alpha=0.7); ax.set_axisbelow(True)
fig.tight_layout(); save(fig, "04-usability.png")

print("\n全部图表生成完毕 ->", OUT)
