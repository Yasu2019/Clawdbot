-- Turso / LibSQL Database Export Schema for Moldflow Superiority CAE Studio Knowledge Base
-- Created: 2026-08-07

CREATE TABLE IF NOT EXISTS cae_accuracy_matrix (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL,
    confidence_score INTEGER NOT NULL,
    governing_physics TEXT NOT NULL,
    moldflow_comparison TEXT NOT NULL
);

INSERT INTO cae_accuracy_matrix (feature_name, confidence_score, governing_physics, moldflow_comparison) VALUES
('3D Warpage (C3D8)', 95, 'CalculiX C3D8 solid FEA + Fiber tensor A_ij + Orthotropic thermal strain', 'Equal or superior to Moldflow. Direct node-by-node C3D8 mesh output.'),
('Resin Filling (VOF)', 90, 'OpenFOAM interFoam + Cross-WLF non-Newtonian viscosity', 'Equal to Moldflow. Academic-grade melt front & pressure prediction.'),
('Insert Pin Deflection', 92, 'Bending beam mechanics (I = pi*d^4/64) + Fluid drag force F_drag', 'Superior to Moldflow. Direct MPa, deflection mm, and SF safety factor.'),
('Mold Base Plate Sizing', 88, 'Plate bending deflection (delta = P*W^4 / E*T^3) + Mold steel catalog', 'Standard tool design rule automation with raw material cost (JPY).'),
('Parting Line (PL) AI', 85, '3D surface normal n.d_open + Undercut area minimization', 'AI auto-recommends zero-slider PL Z-level or accepts user custom PL.'),
('Physical Flash Length', 82, 'Hagen-Poiseuille gap flow + Mold plate clamping deflection gap', 'Superior to Moldflow. Calculates physical length (um) instead of generic probability.'),
('Internal Void Diameter', 80, 'Rayleigh-Plesset cavitation growth + Volumetric thermal shrinkage', 'Superior to Moldflow. Direct micro-void diameter (um) in thick sections.'),
('Silver Streak Index', 78, 'Arrhenius thermal degradation kinetics + Moisture evaporation vol%', 'Reliable risk index for melt temp & cylinder residence time.'),
('Purging Waste Shots', 85, 'Convective-diffusive purging residence species decay C(n) = C0*exp(-n)', 'Accurately predicts minimum required purge shots to hit target PPM.'),
('0.1s AI Surrogate', 93, 'Physics-Informed Neural Network (PINN)', 'Sub-100ms instant response for interactive optimization sliders.');

CREATE TABLE IF NOT EXISTS commercial_content_ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    target_audience TEXT NOT NULL,
    description TEXT NOT NULL
);

INSERT INTO commercial_content_ideas (platform, title, target_audience, description) VALUES
('Kindle Unlimited', '[Replacing Moldflow] Building an Open-Source 3D Injection Molding CAE & AI Simulator', 'CAE Engineers / Injection Molding Professionals', 'eBook guide on OpenFOAM + CalculiX C3D8 FEA + Web Cockpit UI.'),
('Qiita / Zenn', '[Sub-100ms Response] Real-Time 3D Warpage Prediction Using PINN Physics AI', 'Python AI / Mechanical Engineers', 'Technical article detailing PINN surrogate solver & 3D visualization.'),
('Udemy', 'Full-Stack CAE Engineering: Building a Next-Gen Injection Molding Simulator', 'Engineers / Students / Developers', 'Hands-on video course from STEP file to C3D8 warpage MP4 Telegram bot.'),
('Booth', 'Next-Gen Moldflow Superiority CAE Studio Web Application & Engine Package', 'Molding Factories / CAE Analysts', 'Complete Python + Three.js web app template source code.');
