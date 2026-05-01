// OpenSCAD example: simple inspection jig block with holes
length = 80;
width = 30;
height = 10;
hole_d = 6;

module jig() {
  difference() {
    cube([length, width, height], center=true);
    translate([-25, 0, 0]) cylinder(h=height+2, d=hole_d, center=true, $fn=64);
    translate([ 25, 0, 0]) cylinder(h=height+2, d=hole_d, center=true, $fn=64);
  }
}

jig();
