from paraview.simple import *
import os
import sys

# ParaView Macro for Automated Report Rendering
# Usage: pvpython render_results.py <case_path> <output_dir>

def render_case(case_path, output_dir):
    print(f"--- Starting ParaView Rendering for {case_path} ---")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Search for VTK files in the VTK subdirectory
    vtk_dir = os.path.join(case_path, "VTK")
    vtk_files = [f for f in os.listdir(vtk_dir) if f.endswith(".vtk") and "internal" not in f.lower()]
    if not vtk_files:
        # Fallback to any vtk file
        vtk_files = [f for f in os.listdir(vtk_dir) if f.endswith(".vtk")]
    
    if not vtk_files:
        print("Error: No VTK files found.")
        return

    vtk_files.sort()
    print(f"Found {len(vtk_files)} VTK files.")

    # Create a view
    view = GetActiveViewOrCreate('RenderView')
    view.ViewSize = [1280, 720]
    view.Background = [0.05, 0.05, 0.1] # Dark blue Clawstack theme

    for i, vtk_file in enumerate(vtk_files):
        full_path = os.path.join(vtk_dir, vtk_file)
        reader = LegacyVTKReader(FileNames=[full_path])
        
        # Add Contour for Melt Front (alpha.resin = 0.5) if array exists
        try:
            contour = Contour(Input=reader)
            contour.ContourBy = ['POINTS', 'alpha.resin']
            contour.Isosurfaces = [0.5]
            Show(contour, view)
        except:
            print(f"Warning: Could not apply contour to {vtk_file}")
            # Just show the solid/mesh as fallback
            Show(reader, view)

        # Setup Camera
        view.ResetCamera()
        view.CameraPosition = [0.2, 0.2, 0.2]
        view.CameraFocalPoint = [0.05, 0.025, 0.005]
        view.CameraViewUp = [0, 0, 1]

        Render()
        img_path = os.path.join(output_dir, f"frame_{i:04d}.png")
        SaveScreenshot(img_path, view)
        print(f"Rendered {vtk_file} to {img_path}")
        
        Delete(reader)

    print("--- Rendering Complete ---")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: pvpython render_results.py <case_path> <output_dir>")
    else:
        render_case(sys.argv[1], sys.argv[2])
