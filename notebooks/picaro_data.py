
import csv
import argparse
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


DATA_PATH = Path(__file__).with_name("picarro_results.csv")
FIGURES_DIR = Path(__file__).with_name("figures")
TABLE_PATH = Path(__file__).with_name("picarro_summary_table.md")


def _parse_num(value: str | None) -> float | None:
	if value is None:
		return None
	value = value.strip()
	if value == "":
		return None
	return float(value.replace(" ", "").replace(",", "."))


def _clean_key(key: str) -> str:
	return key.replace("\ufeff", "").strip()


def _summarize(values: list[float | None]) -> dict[str, float | int | None]:
	values = [v for v in values if v is not None]
	if not values:
		return {"n": 0, "mean": None, "stdev": None, "min": None, "max": None}
	return {
		"n": len(values),
		"mean": statistics.mean(values),
		"stdev": statistics.stdev(values) if len(values) >= 2 else 0.0,
		"min": min(values),
		"max": max(values),
	}


def load_rows(path: Path = DATA_PATH) -> list[dict[str, object]]:
	rows: list[dict[str, object]] = []
	with path.open("r", encoding="utf-8") as f:
		reader = csv.DictReader(f, delimiter=";")
		if reader.fieldnames:
			reader.fieldnames = [_clean_key(k) for k in reader.fieldnames]
		for raw in reader:
			raw = {_clean_key(k): v for k, v in raw.items()}
			rows.append(
				{
					"Gas": raw.get("Gas"),
					"Experiment_number": int(raw["Experiment_number"]),
					"expected_CH4_ppm": _parse_num(raw["expected_CH4_ppm"]),
					"CH4_ppm": _parse_num(raw["CH4_ppm"]),
					"CH4_isotope": _parse_num(raw["CH4_isotope"]),
					"CO2_ppm": _parse_num(raw["CO2_ppm"]),
					"CO2_isotope": _parse_num(raw["CO2_isotope"]),
					"H2O_%": _parse_num(raw["H2O_%"]),
				}
			)
	return rows


def group_stats(rows: list[dict[str, object]]) -> dict[str, dict[str, dict[str, float | int | None]]]:
	by_gas: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
	for row in rows:
		by_gas[str(row["Gas"])].append(row)

	stats: dict[str, dict[str, dict[str, float | int | None]]] = {}
	for gas, gas_rows in by_gas.items():
		stats[gas] = {
			"CH4_ppm": _summarize([r["CH4_ppm"] for r in gas_rows]),
			"CO2_ppm": _summarize([r["CO2_ppm"] for r in gas_rows]),
			"H2O_%": _summarize([r["H2O_%"] for r in gas_rows]),
		}
	return stats


def write_summary_table(
	stats: dict[str, dict[str, dict[str, float | int | None]]],
	out_path: Path = TABLE_PATH,
) -> None:
	order = [
		"Synthetic_air_RIVER",
		"Synthetic_air_SENSE",
		"CO2_ppm",
		"CH4_100ppm_bag_1",
		"CH4_100ppm_bag2",
		"Gas_Subocean_pump_outlet",
	]

	def fmt(v: float | int | None, digits: int = 3) -> str:
		if v is None:
			return ""
		if isinstance(v, int):
			return str(v)
		return f"{v:.{digits}f}"

	lines: list[str] = []
	lines.append("# Picarro summary table\n")
	lines.append(f"Source: `{DATA_PATH.name}`\n")
	lines.append("\n")
	lines.append(
		"| Gas | n | CH4 mean (ppm) | CH4 sd | CO2 mean (ppm) | CO2 sd | H2O mean (%) |"\
		"\n|---|---:|---:|---:|---:|---:|---:|"
	)

	gases = [g for g in order if g in stats] + [g for g in sorted(stats.keys()) if g not in order]
	for gas in gases:
		ch4 = stats[gas]["CH4_ppm"]
		co2 = stats[gas]["CO2_ppm"]
		h2o = stats[gas]["H2O_%"]
		n = int(ch4["n"] or 0)
		lines.append(
			"| "
			+ gas
			+ " | "
			+ str(n)
			+ " | "
			+ fmt(ch4["mean"], 3)
			+ " | "
			+ fmt(ch4["stdev"], 3)
			+ " | "
			+ fmt(co2["mean"], 3)
			+ " | "
			+ fmt(co2["stdev"], 3)
			+ " | "
			+ fmt(h2o["mean"], 3)
			+ " |"
		)

	out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_ch4_bags(rows: list[dict[str, object]], out_path: Path) -> None:
	bag_names = ["CH4_100ppm_bag_1", "CH4_100ppm_bag2"]
	bag_rows = {name: [r for r in rows if r["Gas"] == name] for name in bag_names}

	means: list[float] = []
	sds: list[float] = []
	for name in bag_names:
		values = [float(r["CH4_ppm"]) for r in bag_rows[name] if r["CH4_ppm"] is not None]
		means.append(statistics.mean(values))
		sds.append(statistics.stdev(values) if len(values) >= 2 else 0.0)

	expected = 100.0
	fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=160)
	x = range(len(bag_names))
	ax.bar(x, means, yerr=sds, capsize=6, color=["#4C78A8", "#72B7B2"])
	ax.axhline(expected, color="#E45756", linestyle="--", linewidth=2, label="Expected (100 ppm)")
	ax.set_xticks(list(x), ["Bag 1", "Bag 2"])
	ax.set_ylabel("CH4 (ppm)")
	ax.set_title("CH4 100 ppm bags: measured vs expected")
	ax.set_ylim(0, max(105, expected * 1.05))
	ax.legend(loc="lower right")
	ax.grid(axis="y", alpha=0.25)

	for i, m in enumerate(means):
		ax.text(i, m + 1.0, f"{m:.2f}", ha="center", va="bottom", fontsize=9)

	fig.tight_layout()
	out_path.parent.mkdir(parents=True, exist_ok=True)
	fig.savefig(out_path)
	plt.close(fig)


def plot_overview(stats: dict[str, dict[str, dict[str, float | int | None]]], out_path: Path) -> None:
	order = [
		"Synthetic_air_RIVER",
		"Synthetic_air_SENSE",
		"CO2_ppm",
		"CH4_100ppm_bag_1",
		"CH4_100ppm_bag2",
		"Gas_Subocean_pump_outlet",
	]
	gases = [g for g in order if g in stats]

	ch4_means = [float(stats[g]["CH4_ppm"]["mean"]) for g in gases]
	ch4_sds = [float(stats[g]["CH4_ppm"]["stdev"]) for g in gases]
	co2_means = [float(stats[g]["CO2_ppm"]["mean"]) for g in gases]
	co2_sds = [float(stats[g]["CO2_ppm"]["stdev"]) for g in gases]

	labels = [
		"RIVER\nsynthetic",
		"SENSE\nsynthetic",
		"CO2\nbag",
		"CH4 bag\n1",
		"CH4 bag\n2",
		"Pump\noutlet",
	]

	fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=160)
	x = range(len(gases))

	ax1.bar(x, ch4_means, yerr=ch4_sds, capsize=4, color="#4C78A8")
	ax1.set_xticks(list(x), labels, rotation=0)
	ax1.set_ylabel("CH4 (ppm)")
	ax1.set_title("CH4 by sample")
	ax1.grid(axis="y", alpha=0.25)

	ax2.bar(x, co2_means, yerr=co2_sds, capsize=4, color="#F58518")
	ax2.set_xticks(list(x), labels, rotation=0)
	ax2.set_ylabel("CO2 (ppm)")
	ax2.set_title("CO2 by sample")
	ax2.grid(axis="y", alpha=0.25)

	# keep CO2 readable (pump outlet dominates)
	ax2.set_ylim(0, max(420.0, max(co2_means) * 1.1))

	fig.suptitle("Independent analyzer verification (means ± 1σ)")
	fig.tight_layout()
	out_path.parent.mkdir(parents=True, exist_ok=True)
	fig.savefig(out_path)
	plt.close(fig)


def main(argv: list[str] | None = None) -> None:
	parser = argparse.ArgumentParser(description="Summarize Picarro verification results")
	parser.add_argument("--data", type=Path, default=DATA_PATH, help="Path to picarro_results.csv")
	parser.add_argument("--write-table", action="store_true", help="Write a Markdown summary table")
	parser.add_argument("--write-plots", action="store_true", help="Write PNG plots into notebooks/figures")
	args = parser.parse_args(argv)

	rows = load_rows(args.data)
	stats = group_stats(rows)

	print("Per Gas summary (mean +/- sd)")
	for gas in sorted(stats.keys()):
		ch4 = stats[gas]["CH4_ppm"]
		co2 = stats[gas]["CO2_ppm"]
		h2o = stats[gas]["H2O_%"]
		if ch4["mean"] is None or co2["mean"] is None:
			continue
		print(
			f"- {gas:24s} "
			f"CH4={float(ch4['mean']):.3f}+/-{float(ch4['stdev']):.3f} ppm | "
			f"CO2={float(co2['mean']):.3f}+/-{float(co2['stdev']):.3f} ppm | "
			f"H2O={float(h2o['mean']):.3f}%"
		)

	bag_rows = [r for r in rows if str(r["Gas"]).lower().startswith("ch4_100ppm")]
	if bag_rows:
		exp_mean = statistics.mean([float(r["expected_CH4_ppm"]) for r in bag_rows])
		meas_mean = statistics.mean([float(r["CH4_ppm"]) for r in bag_rows])
		bias = meas_mean - exp_mean
		rel_bias_pct = bias / exp_mean * 100
		print("\nCH4 100 ppm bags")
		print(f"- measured mean={meas_mean:.3f} ppm vs expected {exp_mean:.1f} ppm")
		print(f"- bias={bias:.3f} ppm ({rel_bias_pct:.2f}%)")

	if args.write_table:
		write_summary_table(stats, TABLE_PATH)
		print(f"\nWrote table: {TABLE_PATH}")

	if args.write_plots:
		overview_path = FIGURES_DIR / "picarro_overview.png"
		ch4bags_path = FIGURES_DIR / "picarro_ch4_bags.png"
		plot_overview(stats, overview_path)
		plot_ch4_bags(rows, ch4bags_path)
		print(f"Wrote plot: {overview_path}")
		print(f"Wrote plot: {ch4bags_path}")


if __name__ == "__main__":
	main()
