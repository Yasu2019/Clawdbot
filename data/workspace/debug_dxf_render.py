import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import os

def render_dxf_to_png(dxf_path, output_path):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_aspect('equal')
    ax.set_facecolor('black')  # CAD-like background
    
    # Iterate over entities
    for e in msp:
        layer = e.dxf.layer
        color = 'white'
        style = '-'
        label = layer
        
        # Color coating based on layer
        if layer == '231': color = 'yellow'; label='Punch'
        elif layer == '69': color = 'cyan'; label='Frame'
        elif layer == '0': color = 'white'
        else: color = 'gray'
        
        if e.dxftype() == 'LINE':
            start = e.dxf.start
            end = e.dxf.end
            ax.plot([start.x, end.x], [start.y, end.y], color=color, lw=1, label=label)
        elif e.dxftype() == 'LWPOLYLINE':
            points = e.get_points(format='xy')
            x = [p[0] for p in points]
            y = [p[1] for p in points]
            if e.closed:
                x.append(x[0])
                y.append(y[0])
            ax.plot(x, y, color=color, lw=1, label=label)
        elif e.dxftype() == 'CIRCLE':
            c = plt.Circle((e.dxf.center.x, e.dxf.center.y), e.dxf.radius, color=color, fill=False)
            ax.add_patch(c)
        elif e.dxftype() == 'ARC':
            # Arc from start_angle to end_angle
            import matplotlib.patches as patches
            arc = patches.Arc((e.dxf.center.x, e.dxf.center.y), 2*e.dxf.radius, 2*e.dxf.radius,
                             theta1=e.dxf.start_angle, theta2=e.dxf.end_angle, color=color)
            ax.add_patch(arc)

    # Auto-scale
    ax.autoscale()
    
    # Add grid and legend (deduplicated)
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper right')
    
    plt.grid(True, color='#333', linestyle='--')
    plt.title(f"DXF Content: {os.path.basename(dxf_path)}", color='white')
    plt.savefig(output_path, dpi=150, facecolor='black')
    print(f"DXF rendered to {output_path}")

try:
    dxf_file = r"D:\Clawdbot_Docker_20260125\data\workspace\Punch_Header and Frame_Hole_20260215.dxf"
    render_dxf_to_png(dxf_file, "dxf_debug_view.png")
except Exception as e:
    print(f"Error rendering DXF: {e}")
