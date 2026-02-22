# Advanced Injection Molding - DOE Generator (R Script)
# Generates combinations of parameters (Gate Velocity, Coolant Temp) and
# drives the Python case builder.

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
if(length(args) < 1) {
  material_id <- "pp_generic"
} else {
  material_id <- args[1]
}

cat("====================================================\n")
cat(" R-Language DOE Optimizer for Injection Molding\n")
cat(paste(" Target Material:", material_id, "\n"))
cat("====================================================\n")

# Define Parameter Spaces (Factors)
gate_velocities <- c(2.0, 5.0, 8.0)  # m/s
coolant_temps <- c(30, 50, 70)       # Celsius

# Create L9 Orthogonal Array Equivalent (Full Factorial here for simplicity: 3x3 = 9 runs)
doe_matrix <- expand.grid(
  Velocity = gate_velocities,
  CoolantT = coolant_temps
)

cat("Design of Experiments Matrix (L9):\n")
print(doe_matrix)
cat("----------------------------------------------------\n")

run_simulation <- function(run_id, velocity, coolant_t) {
  outdir <- paste0("./sim_run_", run_id)
  cat(paste("Executing Run", run_id, "-> Velocity:", velocity, "m/s, Coolant:", coolant_t, "C\n"))
  
  # Format Gate JSON for Python script
  # For DOE, we assume a single gate at origin whose velocity changes
  gates_json <- paste0('[{"x":0, "y":0, "z":10, "v":', velocity, '}]')
  
  # System call to Python OpenFOAM/Elmer Builder
  # In a real environment, this would wait for the CFD solver to finish 
  # and parse the output results (Fill Time, Max Warpage).
  py_cmd <- if (.Platform$OS.type == "unix") "python3" else "python"
  cmd <- sprintf("%s molding_case_builder.py --material %s --gates '%s' --coolant_temp %f --outdir %s", 
                 py_cmd, material_id, gates_json, coolant_t, outdir)
  
  # Execute system command (Mock output parsing)
  system(cmd, ignore.stdout = TRUE)
  
  # Mock result extraction (In reality, read from ParaView CSV or Elmer Results)
  # Warpage is directly proportional to cooling temp gradient and inversely to fill time
  fill_time <- 100 / velocity
  warpage_mm <- 0.05 + 0.002 * abs(coolant_t - 40) + 0.01 * fill_time
  
  return(data.frame(Run=run_id, FillTime_s=fill_time, Warpage_mm=warpage_mm))
}

results <- data.frame()

# Execute DOE
cat("\nStarting Simulation Loop...\n")
for (i in 1:nrow(doe_matrix)) {
  v <- doe_matrix$Velocity[i]
  t <- doe_matrix$CoolantT[i]
  
  res <- run_simulation(i, v, t)
  results <- rbind(results, res)
}

cat("\n====================================================\n")
cat(" Optimization Results Array\n")
cat("====================================================\n")
print(results)

# Find Optimum
opt_idx <- which.min(results$Warpage_mm)
cat(paste("\n=> OPTIMAL CONDITION FOUND: Run", opt_idx, "\n"))
cat(paste("   Min Warpage:", round(results$Warpage_mm[opt_idx], 3), "mm\n"))
cat(paste("   Optimal Velocity:", doe_matrix$Velocity[opt_idx], "m/s\n"))
cat(paste("   Optimal Coolant Temp:", doe_matrix$CoolantT[opt_idx], "C\n"))

# Save to CSV for Web UI
write.csv(results, "doe_results.csv", row.names = FALSE)
cat("Saved to doe_results.csv\n")
