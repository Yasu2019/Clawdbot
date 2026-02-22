import molding_case_builder as mcb
import json

material = "pa66_gf30"
gates = [
    {"x": 10.0, "y": -5.0, "z": 2.5, "v": 1.5},
    {"x": -10.0, "y": 5.0, "z": 2.5, "v": 1.5}
]

print("=== Running Simple Test on molding_case_builder ===")
print("Material:", material)
print("Gates:", json.dumps(gates))
print("Coolant Temp: 60.0 C\n")

# Run OpenFOAM Case Generation
mcb.generate_openfoam_case(
    case_dir="./test_sim/CFD_MeltFront", 
    stl_product="product.stl", 
    stl_cooling="cooling.stl", 
    gates=gates, 
    resin=mcb.load_resin(material), 
    vents=[]
)

# Run ElmerFEM Case Generation
mcb.generate_elmer_case(
    case_dir="./test_sim/FEA_Warpage", 
    stl_product="product.stl", 
    stl_cooling="cooling.stl", 
    resin=mcb.load_resin(material)
)

print("\n=== Test Finished. Check ./test_sim directory ===")
