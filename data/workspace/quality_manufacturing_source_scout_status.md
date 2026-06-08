# Quality Manufacturing Source Scout

- Updated: 2026-06-08T16:55:13+09:00
- Mode: metadata_only_reachability
- Source count: 27
- Reachability checks are advisory; a failed check can mean bot protection, HEAD blocking, or a local network timeout.

## Safety Policy

- Prefer FREE and official/open-access sources first.
- Do not bypass paywalls, DRM, login walls, or license controls.
- Mark paid standards, paid manuals, and paid databases as PAID before use.
- Treat unknown mirrors and unofficial PDFs as CHECK until the origin is verified.
- Download large datasets only after license and storage impact are confirmed.

## Cost Labels

- FREE: Free and normally accessible.
- FREE_REG: Free or open, but registration, license acceptance, API key, or non-commercial terms may apply.
- PAID: Purchase, subscription, membership, or paid database access is likely.
- CHECK: Copyright, redistribution, or source legitimacy needs review.

## Recommended First Reading

- FREE P1 [Autodesk Moldflow Insight Help](https://help.autodesk.com/view/MFIA/2026/ENU/)
  - Best legitimate reference for Moldflow result terminology and benchmark interpretation.
- FREE P1 [CVF Open Access](https://openaccess.thecvf.com/)
  - Reliable open papers for CVPR/ICCV/ECCV methods, often with code links.
- FREE P1 [NASA Systems Engineering Handbook](https://www.nasa.gov/reference/systems-engineering-handbook/)
  - Good free framework for requirements, validation, verification, risk, interfaces, and complex app development discipline.
- FREE P1 [NIST/SEMATECH Engineering Statistics Handbook](https://www.nist.gov/programs-projects/nistsematech-engineering-statistics-handbook)
  - Strong free baseline for SPC, DOE, process monitoring, measurement, and statistical quality thinking.
- FREE P1 [OpenFOAM Documentation](https://www.openfoam.com/documentation/overview)
  - Free CFD solver docs for file structure, meshing, numerical schemes, and post-processing foundations.
- FREE P1 [OpenRadioss Documentation](https://openradioss.atlassian.net/wiki/spaces/OPENRADIOSS/overview)
  - Primary reference for our bending and blanking solver work and deck correctness.
- FREE P1 [Papers with Code](https://paperswithcode.com/)
  - Good for finding papers with code and benchmark tables before investing implementation time.
- FREE P1 [arXiv](https://arxiv.org/)
  - Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.
- FREE P1 [openInjMoldSim Paper](https://www.mdpi.com/2311-5521/5/2/84)
  - Closest open paper pattern for building our own injection molding simulation and using Moldflow as benchmark.
- FREE_REG P1 [Kolektor Surface-Defect Dataset](https://www.vicos.si/resources/kolektorsdd)
  - Real industrial surface-defect dataset with annotations, useful for small-defect segmentation experiments.
- FREE_REG P1 [MVTec Anomaly Detection Datasets](https://www.mvtec.com/company/research/datasets)
  - Standard benchmark family for industrial anomaly detection. License is typically non-commercial, so confirm before business use.
- PAID P1 [AIAG Quality Core Tools](https://www.aiag.org/expertise-areas/quality/quality-core-tools)
  - Authoritative source for automotive core tools. Many manuals and courses are paid, so use as paid-reference candidate.
- PAID P1 [ISO, JIS, IATF Standard Texts](https://www.iso.org/standards.html)
  - Authoritative, but usually paid and license-restricted. Do not download from unofficial mirrors.

## Domain Map

### qms_core_tools
- FREE P1 [NASA Systems Engineering Handbook](https://www.nasa.gov/reference/systems-engineering-handbook/) status=200 ok=True
  - Good free framework for requirements, validation, verification, risk, interfaces, and complex app development discipline.
  - scout query: `NASA systems engineering handbook risk requirements verification FMEA PDF`
- FREE P1 [NIST/SEMATECH Engineering Statistics Handbook](https://www.nist.gov/programs-projects/nistsematech-engineering-statistics-handbook) status=200 ok=True
  - Strong free baseline for SPC, DOE, process monitoring, measurement, and statistical quality thinking.
  - scout query: `site:nist.gov SEMATECH engineering statistics handbook SPC MSA DOE process capability`
- PAID P1 [AIAG Quality Core Tools](https://www.aiag.org/expertise-areas/quality/quality-core-tools) status=200 ok=True
  - Authoritative source for automotive core tools. Many manuals and courses are paid, so use as paid-reference candidate.
  - scout query: `site:aiag.org APQP Control Plan PPAP FMEA MSA SPC free overview`
- PAID P1 [ISO, JIS, IATF Standard Texts](https://www.iso.org/standards.html)
  - Authoritative, but usually paid and license-restricted. Do not download from unofficial mirrors.
  - scout query: `ISO 9001 IATF 16949 internal audit guidance official paid standard`
- FREE_REG P2 [AIAG Core Tools Key Terms and Self Assessment](https://go.aiag.org/core-tools-terms) status=200 ok=True
  - Useful free or registration-gated glossary/self-assessment entry point before buying manuals.
  - scout query: `AIAG core tools terms self assessment APQP FMEA MSA SPC`

### visual_inspection_ai
- FREE P1 [CVF Open Access](https://openaccess.thecvf.com/) status=200 ok=True
  - Reliable open papers for CVPR/ICCV/ECCV methods, often with code links.
  - scout query: `site:openaccess.thecvf.com industrial anomaly detection manufacturing defect segmentation`
- FREE P1 [Papers with Code](https://paperswithcode.com/) status=200 ok=True
  - Good for finding papers with code and benchmark tables before investing implementation time.
  - scout query: `Papers with Code industrial anomaly detection MVTec AD VisA BTAD Real-IAD`
- FREE P1 [arXiv](https://arxiv.org/) status=200 ok=True
  - Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.
  - scout query: `arXiv industrial visual inspection survey manufacturing defect detection tolerance analysis injection molding simulation`
- FREE_REG P1 [Kolektor Surface-Defect Dataset](https://www.vicos.si/resources/kolektorsdd) status=200 ok=True
  - Real industrial surface-defect dataset with annotations, useful for small-defect segmentation experiments.
  - scout query: `KolektorSDD Kolektor surface defect dataset license paper`
- FREE_REG P1 [MVTec Anomaly Detection Datasets](https://www.mvtec.com/company/research/datasets) status=200 ok=True
  - Standard benchmark family for industrial anomaly detection. License is typically non-commercial, so confirm before business use.
  - scout query: `MVTec AD dataset license anomaly detection industrial inspection`
- FREE_REG P2 [Kaggle Datasets and Competitions](https://www.kaggle.com/datasets) status=404 ok=False
  - Useful datasets such as Severstal steel defects and predictive maintenance examples. Registration and license checks required.
  - scout query: `site:kaggle.com manufacturing defect detection predictive maintenance quality dataset`
- FREE_REG P2 [Roboflow Universe](https://universe.roboflow.com/) status=206 ok=True
  - Large public CV dataset catalog. Quality varies, so use as candidate source, not ground truth.
  - scout query: `Roboflow Universe manufacturing defect detection surface scratch dataset license`
- PAID P3 [IEEE Xplore](https://ieeexplore.ieee.org/)
  - Good for sensor/vision/AI papers, but many articles are paid. Prefer arXiv/CVF copy when available.
  - scout query: `IEEE industrial visual inspection deep learning manufacturing defect detection`

### resin_flow_moldflow
- FREE P1 [Autodesk Moldflow Insight Help](https://help.autodesk.com/view/MFIA/2026/ENU/) status=200 ok=True
  - Best legitimate reference for Moldflow result terminology and benchmark interpretation.
  - scout query: `site:help.autodesk.com/view/MFIA injection molding filling packing cooling warpage material model`
- FREE P1 [OpenFOAM Documentation](https://www.openfoam.com/documentation/overview) status=200 ok=True
  - Free CFD solver docs for file structure, meshing, numerical schemes, and post-processing foundations.
  - scout query: `OpenFOAM user guide multiphase non Newtonian polymer injection molding`
- FREE P1 [openInjMoldSim Paper](https://www.mdpi.com/2311-5521/5/2/84) status=200 ok=True
  - Closest open paper pattern for building our own injection molding simulation and using Moldflow as benchmark.
  - scout query: `openInjMoldSim OpenFOAM injection molding Cross WLF Tait VOF`

### press_progressive_die
- FREE P1 [OpenRadioss Documentation](https://openradioss.atlassian.net/wiki/spaces/OPENRADIOSS/overview) status=200 ok=True
  - Primary reference for our bending and blanking solver work and deck correctness.
  - scout query: `OpenRadioss examples shell forming bending blanking springback`

### tolerance_cetol_like
- FREE P1 [NIST/SEMATECH Engineering Statistics Handbook](https://www.nist.gov/programs-projects/nistsematech-engineering-statistics-handbook) status=200 ok=True
  - Strong free baseline for SPC, DOE, process monitoring, measurement, and statistical quality thinking.
  - scout query: `site:nist.gov SEMATECH engineering statistics handbook SPC MSA DOE process capability`
- FREE P1 [arXiv](https://arxiv.org/) status=200 ok=True
  - Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.
  - scout query: `arXiv industrial visual inspection survey manufacturing defect detection tolerance analysis injection molding simulation`
- PAID P1 [AIAG Quality Core Tools](https://www.aiag.org/expertise-areas/quality/quality-core-tools) status=200 ok=True
  - Authoritative source for automotive core tools. Many manuals and courses are paid, so use as paid-reference candidate.
  - scout query: `site:aiag.org APQP Control Plan PPAP FMEA MSA SPC free overview`
- FREE_REG P2 [AIAG Core Tools Key Terms and Self Assessment](https://go.aiag.org/core-tools-terms) status=200 ok=True
  - Useful free or registration-gated glossary/self-assessment entry point before buying manuals.
  - scout query: `AIAG core tools terms self assessment APQP FMEA MSA SPC`
- FREE P3 [PubMed Central](https://pmc.ncbi.nlm.nih.gov/)
  - Not manufacturing-specific, but strong for statistics, validation, and ML evaluation methods.
  - scout query: `site:pmc.ncbi.nlm.nih.gov machine learning anomaly detection measurement validation statistical process control`

### training_video_and_dx
- FREE P1 [CVF Open Access](https://openaccess.thecvf.com/) status=200 ok=True
  - Reliable open papers for CVPR/ICCV/ECCV methods, often with code links.
  - scout query: `site:openaccess.thecvf.com industrial anomaly detection manufacturing defect segmentation`
- FREE P1 [arXiv](https://arxiv.org/) status=200 ok=True
  - Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.
  - scout query: `arXiv industrial visual inspection survey manufacturing defect detection tolerance analysis injection molding simulation`
- FREE_REG P2 [AIAG Core Tools Key Terms and Self Assessment](https://go.aiag.org/core-tools-terms) status=200 ok=True
  - Useful free or registration-gated glossary/self-assessment entry point before buying manuals.
  - scout query: `AIAG core tools terms self assessment APQP FMEA MSA SPC`
- FREE P3 [IPA Digital Skill and DX Materials](https://www.ipa.go.jp/)
  - Useful for internal training apps, IT governance, security, and DX skill maps.
  - scout query: `site:ipa.go.jp AI quality DX skills security training material`

## Paid Watchlist

- PAID [AIAG Quality Core Tools](https://www.aiag.org/expertise-areas/quality/quality-core-tools)
  - Authoritative source for automotive core tools. Many manuals and courses are paid, so use as paid-reference candidate.
- PAID [ISO, JIS, IATF Standard Texts](https://www.iso.org/standards.html)
  - Authoritative, but usually paid and license-restricted. Do not download from unofficial mirrors.
- PAID [IEEE Xplore](https://ieeexplore.ieee.org/)
  - Good for sensor/vision/AI papers, but many articles are paid. Prefer arXiv/CVF copy when available.
- PAID [SAE Mobilus](https://saemobilus.sae.org/)
  - Can contain high-value automotive manufacturing papers, but usually paid.

## Next Actions

- Read NIST statistics handbook sections for SPC, DOE, process monitoring, and measurement foundations.
- Use Autodesk Moldflow Help plus openInjMoldSim paper to define resin-flow solver benchmark terminology.
- Use OpenRadioss and existing project pregates for press bending/blanking deck improvement.
- Use MVTec/Kolektor/CVF/arXiv/Papers with Code for visual inspection AI experiments after license checks.
- Treat AIAG/ISO/IATF/SAE/IEEE as paid candidates and ask before purchase or subscription use.
