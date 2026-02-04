# Picarro verification summary (Bronkhorst mixing setup)

Date: 2026-02-03  
Source data: [notebooks/picarro_results.csv](notebooks/picarro_results.csv) and [notebooks/PIcarro_verification.txt](notebooks/PIcarro_verification.txt)

## Context
You analyzed several “known” gases/bags with an independent CH4/CO2 analyzer (RIVER lab Picarro). The goal is to verify whether the Bronkhorst mixing setup and the sampling line (including the Subocean pump) deliver the expected concentrations.

RIVER notes: CO2 is checked monthly and shows no drift; CH4 is assumed stable (not explicitly verified).

## Data overview (means ± 1σ)
All concentrations are in ppm.

- Synthetic air (RIVER): CH4 = 0.030, CO2 = 7.800 (single measurement)
- Synthetic air (SENSE bottle): CH4 = 0.030, CO2 = 10.100 (single measurement)

- CO2 bag (“CO2_ppm”, n=3):
  - CO2 = 97.000 ± 0.513 (range 96.410–97.340)
  - CH4 = 2.026 ± 0.022 (range 2.000–2.039)

- CH4 100 ppm bag 1 (“CH4_100ppm_bag_1”, n=3):
  - CH4 = 90.140 ± 0.095 (range 90.080–90.250)
  - CO2 = 12.777 ± 0.734

- CH4 100 ppm bag 2 (“CH4_100ppm_bag2”, n=3):
  - CH4 = 92.280 ± 0.312 (range 92.080–92.640)
  - CO2 = 16.207 ± 1.533

- Subocean pump outlet (“Gas_Subocean_pump_outlet”, n=3):
  - CO2 = 379.267 ± 0.462 (range 379.000–379.800)
  - CH4 = 1.732 ± 0.003 (range 1.730–1.735)

## Key findings (quantified)
### 1) CH4 “100 ppm” bags are systematically low
Across both CH4 bags (n=6):
- Expected CH4: 100.0 ppm
- Measured CH4 mean: 91.210 ppm
- Bias: -8.790 ppm (i.e., -8.79%)

This matches your conclusion that the mixing setup produces less CH4 than expected, and that the error is systematic (repeatable within-bag scatter is small).

### 2) CO2 “100 ppm” bag reads ~97 ppm, but interpretation depends on the baseline
Measured CO2 in the CO2 bag is 97.0 ppm (very stable across replicates).

Your note: the base synthetic air contains ~10 ppm CO2 (SENSE bottle measured 10.1 ppm; RIVER synthetic air measured 7.8 ppm). That baseline matters when interpreting the “expected” CO2:

- If the mixing calculation targeted **100 ppm total CO2** (absolute), then the bag is ~3 ppm low (97 vs 100).
- If the mixing calculation targeted **100 ppm added above a 0 ppm baseline**, then with a ~10 ppm baseline you would expect ~110 ppm total; the measured 97 ppm would imply a larger negative bias.

Either way, this supports your conclusion that there is a systematic concentration shortfall relative to the ideal mixing assumption.

### 3) Subocean pump outlet gas is consistent with atmospheric air intrusion
At the pump outlet, CO2 is ~379 ppm (near ambient atmospheric CO2) and CH4 is ~1.73 ppm (near typical ambient CH4). This is inconsistent with “0 ppm” synthetic air sources measured at ~8–10 ppm CO2 and near-zero CH4.

This strongly supports your conclusion: the gas reaching the spectrometer is not the intended gas; there is an air ingress somewhere in the line, likely near the pump head or associated fittings.

### 4) Isotope anomalies (qualitative)
Your note: the SENSE bottle synthetic air has high CO2 isotope signal. The raw file includes CO2 isotope values that are markedly different between sources (e.g., SENSE synthetic vs RIVER synthetic, and extreme values on CH4 bags).

Because isotope calibration/units aren’t documented in the dataset, treat isotope results as qualitative flags (source differences) rather than quantitative mixing validation.

## Conclusions (aligned with your notes)
- CH4 100 ppm mixing produces bags ~9% low vs expected (systematic bias).
- CO2 bag is near 97 ppm; baseline CO2 in the synthetic air (7.8–10.1 ppm) must be accounted for when defining “expected”. The direction is still consistent with a systematic shortfall relative to ideal assumptions.
- The Subocean pump outlet composition resembles atmospheric air, indicating a leak/ingress in the sampling line (likely at/near the pump head).

## Recommended next checks
- Leak test the pump head + all upstream/downstream fittings (pressure decay or soap solution), and verify any check valves.
- Repeat “synthetic air” measurement at the spectrometer inlet (not just at the source) to localize where atmospheric ingress begins.
- For mixing validation, log actual MFC setpoints/flows during bag filling and compute expected concentration using measured source baselines (CO2 in base gas).
