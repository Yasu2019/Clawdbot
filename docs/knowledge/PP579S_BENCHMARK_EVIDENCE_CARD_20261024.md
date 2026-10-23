# PP579S injection-molding benchmark evidence card

Updated 2026-10-24. This note records public-source facts and validation limits; it is not a solver result.

## Sources and measured target

The Zenodo dataset DOI 10.5281/zenodo.20309380 is CC BY 4.0 and reports SABIC 579S PP experiments on a MiniMat 60, a two-cavity mold producing two parts per cycle, five recorded part weights per batch, energy and cycle time. For maximin batch 800, the five recorded individual part weights are 5.847, 5.846, 5.696, 5.796, and 5.733 g (reported mean 5.7836 g). These values are measured part outcomes; no cavity/shot identity is provided for each field.

The author-affiliated UPM record describes the CAD as injected pieces plus sprue and lists machine settings: Tinj 180–240 °C; injection time 0.5–2 s; Pinj and holding pressure settings 5–35 bar; back pressure 15–30 bar; holding time 4–6 s. The pressure reference is not established. Do not use these setpoints as cavity-pressure boundary conditions.

## CAD and material evidence

The publisher-hash-verified STEP imports as an assembly rooted at “Cavidad v5,” with EXPULSOR labels and an aggregate 20-solid B-rep. Available entity links do not partition solids by product. The author-affiliated description says parts plus sprue, while the imported hierarchy does not map solid IDs to polymer, runner, or tooling. This is unresolved evidence, not proof of an erroneous publisher file. Do not infer molded-part mass from total STEP volume until a corrected part/sprue CAD or authoritative product-to-solid map is available.

SABIC screening literature lists PP 579S MFR 47 g/10 min at 230 °C / 2.16 kg and typical density 905 kg/m³. These do not provide shear viscosity versus rate/temperature, pvT, heat capacity, conductivity, or crystallization kinetics. Do not treat them as a solver material card.

## Dispatch and acceptance gate

The current batch-800 manifest is preparation only. A quantitative OpenFOAM comparison remains held until the resin/runner solid mapping, individual specimen-to-shot/cavity mapping, machine pressure conventions and time profiles, mold/cooling conditions, grade-specific rheology/pvT/thermal model, and live solver/resource/native-checkpoint preflight are verified. No solver prediction, run, or checkpoint is claimed. Preserve measured observations separately and report coverage/error only for matched specimens.

## Public references

- Zenodo benchmark: https://zenodo.org/records/20309380
- Author-affiliated UPM record: https://portalcientifico.upm.es/en/ipublic/item/10539434
- SABIC PP 579S product information: https://www.sabic.com/ar/products/polymers/polypropylene-pp/sabic-pp?grade=5271k
- SABIC PP product brochure: https://www.sabic.com/zh/Images/SABIC-Caps-and-Closures-Brochure-022022_tcm11-31972.pdf
