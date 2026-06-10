# Quality Manufacturing Source Scout

- Updated: 2026-06-10T17:23:42+09:00
- Mode: metadata_only_reachability
- Source count: 44
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
- FREE P1 [Google Dataset Search](https://datasetsearch.research.google.com/)
  - Broad cross-repository search for datasets; use it to discover official landing pages before downloading anything.
- FREE P1 [Google Patents](https://patents.google.com/)
  - Fast patent search for progressive dies, injection molds, gates, cooling channels, press tooling, and inspection fixtures.
- FREE P1 [J-PlatPat](https://www.j-platpat.inpit.go.jp/)
  - Official Japanese patent search; important for domestic tooling and manufacturing ideas.
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
- FREE_REG P1 [Hugging Face Datasets](https://huggingface.co/datasets)
  - Useful for vision, OCR, document AI, and local model training. Requires per-dataset license review.
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
- FREE P1 [CVF Open Access](https://openaccess.thecvf.com/) status=n/a ok=False
  - Reliable open papers for CVPR/ICCV/ECCV methods, often with code links.
  - scout query: `site:openaccess.thecvf.com industrial anomaly detection manufacturing defect segmentation`
- FREE P1 [Google Dataset Search](https://datasetsearch.research.google.com/) status=200 ok=True
  - Broad cross-repository search for datasets; use it to discover official landing pages before downloading anything.
  - scout query: `manufacturing defect detection dataset injection molding dataset tolerance analysis dataset`
- FREE P1 [Papers with Code](https://paperswithcode.com/) status=200 ok=True
  - Good for finding papers with code and benchmark tables before investing implementation time.
  - scout query: `Papers with Code industrial anomaly detection MVTec AD VisA BTAD Real-IAD`
- FREE P1 [arXiv](https://arxiv.org/) status=200 ok=True
  - Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.
  - scout query: `arXiv industrial visual inspection survey manufacturing defect detection tolerance analysis injection molding simulation`
- FREE_REG P1 [Hugging Face Datasets](https://huggingface.co/datasets)
  - Useful for vision, OCR, document AI, and local model training. Requires per-dataset license review.
  - scout query: `site:huggingface.co/datasets industrial defect anomaly detection manufacturing OCR quality`
- FREE_REG P1 [Kolektor Surface-Defect Dataset](https://www.vicos.si/resources/kolektorsdd) status=200 ok=True
  - Real industrial surface-defect dataset with annotations, useful for small-defect segmentation experiments.
  - scout query: `KolektorSDD Kolektor surface defect dataset license paper`
- FREE_REG P1 [MVTec Anomaly Detection Datasets](https://www.mvtec.com/company/research/datasets) status=200 ok=True
  - Standard benchmark family for industrial anomaly detection. License is typically non-commercial, so confirm before business use.
  - scout query: `MVTec AD dataset license anomaly detection industrial inspection`
- FREE P2 [GitHub Topics](https://github.com/topics)
  - Find code candidates for anomaly detection, OpenFOAM utilities, CAD automation, and reporting tools. License review required before reuse.
  - scout query: `github topics industrial anomaly detection openfoam injection molding freecad dxf step`
- FREE_REG P2 [Kaggle Datasets and Competitions](https://www.kaggle.com/datasets) status=404 ok=False
  - Useful datasets such as Severstal steel defects and predictive maintenance examples. Registration and license checks required.
  - scout query: `site:kaggle.com manufacturing defect detection predictive maintenance quality dataset`
- FREE_REG P2 [Roboflow Universe](https://universe.roboflow.com/) status=403 ok=False
  - Large public CV dataset catalog. Quality varies, so use as candidate source, not ground truth.
  - scout query: `Roboflow Universe manufacturing defect detection surface scratch dataset license`
- PAID P3 [IEEE Xplore](https://ieeexplore.ieee.org/)
  - Good for sensor/vision/AI papers, but many articles are paid. Prefer arXiv/CVF copy when available.
  - scout query: `IEEE industrial visual inspection deep learning manufacturing defect detection`

### resin_flow_moldflow
- FREE P1 [Autodesk Moldflow Insight Help](https://help.autodesk.com/view/MFIA/2026/ENU/) status=200 ok=True
  - Best legitimate reference for Moldflow result terminology and benchmark interpretation.
  - scout query: `site:help.autodesk.com/view/MFIA injection molding filling packing cooling warpage material model`
- FREE P1 [Google Patents](https://patents.google.com/)
  - Fast patent search for progressive dies, injection molds, gates, cooling channels, press tooling, and inspection fixtures.
  - scout query: `progressive die strip layout injection mold cooling channel gate design patent`
- FREE P1 [J-PlatPat](https://www.j-platpat.inpit.go.jp/)
  - Official Japanese patent search; important for domestic tooling and manufacturing ideas.
  - scout query: `J-PlatPat 順送金型 射出成形 金型 品質検査 特許`
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
- FREE P3 [MIT OpenCourseWare](https://ocw.mit.edu/)
  - Free education material for engineering math, statistics, manufacturing, and mechanics foundations.
  - scout query: `MIT OCW manufacturing design statistics finite element method quality`
- FREE P3 [PubMed Central](https://pmc.ncbi.nlm.nih.gov/)
  - Not manufacturing-specific, but strong for statistics, validation, and ML evaluation methods.
  - scout query: `site:pmc.ncbi.nlm.nih.gov machine learning anomaly detection measurement validation statistical process control`

### training_video_and_dx
- FREE P1 [CVF Open Access](https://openaccess.thecvf.com/) status=n/a ok=False
  - Reliable open papers for CVPR/ICCV/ECCV methods, often with code links.
  - scout query: `site:openaccess.thecvf.com industrial anomaly detection manufacturing defect segmentation`
- FREE P1 [arXiv](https://arxiv.org/) status=200 ok=True
  - Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.
  - scout query: `arXiv industrial visual inspection survey manufacturing defect detection tolerance analysis injection molding simulation`
- FREE_REG P1 [Hugging Face Datasets](https://huggingface.co/datasets)
  - Useful for vision, OCR, document AI, and local model training. Requires per-dataset license review.
  - scout query: `site:huggingface.co/datasets industrial defect anomaly detection manufacturing OCR quality`
- FREE P2 [Blender Manual](https://docs.blender.org/manual/en/latest/)
  - Official reference for 3D video generation, rendering, and CAE result visualization pipelines.
  - scout query: `Blender manual camera animation materials lighting python rendering`
- FREE P2 [Remotion Documentation](https://www.remotion.dev/docs/)
  - Useful for scripted educational videos, audit training videos, and dashboard-to-video workflows.
  - scout query: `Remotion data driven video captions charts animation documentation`
- FREE_REG P2 [AIAG Core Tools Key Terms and Self Assessment](https://go.aiag.org/core-tools-terms) status=200 ok=True
  - Useful free or registration-gated glossary/self-assessment entry point before buying manuals.
  - scout query: `AIAG core tools terms self assessment APQP FMEA MSA SPC`
- FREE P3 [IPA Digital Skill and DX Materials](https://www.ipa.go.jp/)
  - Useful for internal training apps, IT governance, security, and DX skill maps.
  - scout query: `site:ipa.go.jp AI quality DX skills security training material`
- FREE P3 [MIT OpenCourseWare](https://ocw.mit.edu/)
  - Free education material for engineering math, statistics, manufacturing, and mechanics foundations.
  - scout query: `MIT OCW manufacturing design statistics finite element method quality`
- FREE_REG P3 [GrabCAD Library](https://grabcad.com/library)
  - Useful for reference CAD and training models. Every model needs license and attribution review.
  - scout query: `GrabCAD progressive die injection mold fixture press tool CAD model`

### patents_cad_assets
- FREE P1 [Google Patents](https://patents.google.com/)
  - Fast patent search for progressive dies, injection molds, gates, cooling channels, press tooling, and inspection fixtures.
  - scout query: `progressive die strip layout injection mold cooling channel gate design patent`
- FREE P1 [J-PlatPat](https://www.j-platpat.inpit.go.jp/)
  - Official Japanese patent search; important for domestic tooling and manufacturing ideas.
  - scout query: `J-PlatPat 順送金型 射出成形 金型 品質検査 特許`
- FREE P2 [Espacenet](https://worldwide.espacenet.com/)
  - International patent search to compare global mold, forming, and inspection mechanisms.
  - scout query: `Espacenet progressive die injection mold warpage inspection fixture patent`
- FREE P2 [FreeCAD Documentation](https://wiki.freecad.org/)
  - Reference for DXF/STEP automation and geometry prep before CAE or mold design.
  - scout query: `FreeCAD python API DXF STEP automation part design`
- FREE P3 [MIT OpenCourseWare](https://ocw.mit.edu/)
  - Free education material for engineering math, statistics, manufacturing, and mechanics foundations.
  - scout query: `MIT OCW manufacturing design statistics finite element method quality`
- FREE_REG P3 [3D ContentCentral](https://www.3dcontentcentral.com/)
  - Mechanical CAD parts and supplier models for fixtures and training examples. Check download terms.
  - scout query: `3D ContentCentral mold base die spring press fixture CAD`
- FREE_REG P3 [GrabCAD Library](https://grabcad.com/library)
  - Useful for reference CAD and training models. Every model needs license and attribution review.
  - scout query: `GrabCAD progressive die injection mold fixture press tool CAD model`
- FREE_REG P3 [TraceParts](https://www.traceparts.com/)
  - Standard-part CAD catalog for building realistic tooling examples; registration may be required.
  - scout query: `TraceParts mold components guide pins die springs CAD`

### materials_data
- FREE P1 [Autodesk Moldflow Insight Help](https://help.autodesk.com/view/MFIA/2026/ENU/) status=200 ok=True
  - Best legitimate reference for Moldflow result terminology and benchmark interpretation.
  - scout query: `site:help.autodesk.com/view/MFIA injection molding filling packing cooling warpage material model`
- FREE P1 [Google Dataset Search](https://datasetsearch.research.google.com/) status=200 ok=True
  - Broad cross-repository search for datasets; use it to discover official landing pages before downloading anything.
  - scout query: `manufacturing defect detection dataset injection molding dataset tolerance analysis dataset`
- FREE P1 [Papers with Code](https://paperswithcode.com/) status=200 ok=True
  - Good for finding papers with code and benchmark tables before investing implementation time.
  - scout query: `Papers with Code industrial anomaly detection MVTec AD VisA BTAD Real-IAD`
- FREE_REG P1 [Hugging Face Datasets](https://huggingface.co/datasets)
  - Useful for vision, OCR, document AI, and local model training. Requires per-dataset license review.
  - scout query: `site:huggingface.co/datasets industrial defect anomaly detection manufacturing OCR quality`
- FREE P2 [DataCite Commons](https://commons.datacite.org/)
  - DOI-backed dataset discovery across repositories, useful when papers mention a DOI but not a direct file page.
  - scout query: `DataCite manufacturing defect dataset sheet metal forming injection molding`
- FREE P2 [J-STAGE](https://www.jstage.jst.go.jp/)
  - Japanese technical papers and society journals; useful for Japanese manufacturing terminology and practical framing.
  - scout query: `site:jstage.jst.go.jp resin flow analysis press forming tolerance analysis visual inspection deep learning`
- FREE P2 [NASA Technical Reports Server](https://ntrs.nasa.gov/) status=200 ok=True
  - Large technical-report repository for failure analysis, verification, modelling, and engineering methods.
  - scout query: `site:ntrs.nasa.gov FMEA risk management verification manufacturing simulation`
- FREE P2 [NIMS Materials Data Repository](https://mdr.nims.go.jp/)
  - Materials data from NIMS; useful for resin, metal, and material-property grounding.
  - scout query: `site:mdr.nims.go.jp material property dataset polymer steel forming`
- FREE P2 [Zenodo](https://zenodo.org/) status=200 ok=True
  - Good for DOI-backed datasets and supplementary material with explicit licenses.
  - scout query: `site:zenodo.org manufacturing defect dataset sheet metal forming injection molding tolerance analysis`
- FREE P3 [AIST Research and DB](https://www.aist.go.jp/)
  - Japanese industrial AI, measurement, materials, and manufacturing research gateway.
  - scout query: `site:aist.go.jp manufacturing AI visual inspection metrology materials dataset`
- FREE P3 [DOE Data Explorer](https://www.osti.gov/dataexplorer/)
  - US DOE dataset search for materials, simulation, and engineering datasets.
  - scout query: `site:osti.gov/dataexplorer manufacturing simulation materials dataset`
- FREE P3 [Figshare](https://figshare.com/) status=202 ok=True
  - Supplementary datasets with DOI and license metadata; useful after core sources.
  - scout query: `site:figshare.com manufacturing defect inspection dataset forming simulation`
- FREE P3 [MIT OpenCourseWare](https://ocw.mit.edu/)
  - Free education material for engineering math, statistics, manufacturing, and mechanics foundations.
  - scout query: `MIT OCW manufacturing design statistics finite element method quality`
- FREE P3 [Mendeley Data](https://data.mendeley.com/) status=200 ok=True
  - Often hosts dataset companions to engineering papers.
  - scout query: `site:data.mendeley.com manufacturing defect detection predictive maintenance dataset`
- FREE_REG P3 [Materials Project](https://materialsproject.org/)
  - High-quality materials database; account/API terms may apply. More useful for material-learning foundations than immediate mold/press work.
  - scout query: `Materials Project API license materials property dataset`
- PAID P3 [SAE Mobilus](https://saemobilus.sae.org/)
  - Can contain high-value automotive manufacturing papers, but usually paid.
  - scout query: `SAE sheet metal forming tolerance analysis injection molding quality manufacturing`

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
- Use Google Dataset Search, DataCite, Zenodo, Figshare, Mendeley, NIMS, and DOE Data Explorer as the broad legal data-discovery loop.
- Use Google Patents, J-PlatPat, and Espacenet for tooling and mold-design idea mining before implementation.
- Use Blender, Remotion, FreeCAD, and GitHub documentation/code only after license checks for derivative reuse.
- Treat AIAG/ISO/IATF/SAE/IEEE as paid candidates and ask before purchase or subscription use.
