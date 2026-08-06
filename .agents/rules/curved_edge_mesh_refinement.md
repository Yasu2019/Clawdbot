# Rule: Curvature-Based Adaptive Edge Mesh Refinement for CAE Solvers (CalculiX / OpenFOAM)

Whenever generating, modifying, or executing 3D FEM solid meshes or fluid flow meshes for CalculiX, OpenFOAM, or general CAE simulation decks:

1. **Curved Boundary Edge Refinement**:
   - For all curved edges, circular holes, and fillets (e.g. $\varnothing 20\text{mm}$ holes, R-corners), NEVER use coarse linear approximations.
   - You MUST apply Curvature-Based Adaptive Edge Mesh Refinement with high-density angular resolution (minimum $N_{\theta} \ge 48$ angular divisions around circular boundaries, local element size $h_{curved} \approx 0.8\text{mm}$).

2. **Multi-Layer Radial Transition**:
   - Generate at least 8 radial concentric refinement layers ($N_{radial} \ge 8$) extending from the curved boundary edge into the domain to accurately capture stress concentrations ($\sigma_{notch}$) and melt front flow dynamics.

3. **Flat Region Efficiency**:
   - Maintain standard mesh sizing ($h_{flat} \approx 3.5\text{mm}$) on flat planar regions to optimize computation speed while guaranteeing boundary geometric precision.
