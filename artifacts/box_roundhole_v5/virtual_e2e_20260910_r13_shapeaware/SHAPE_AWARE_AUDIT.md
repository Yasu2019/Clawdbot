# Shape-aware air-trap candidate audit

The earlier r12 animation was distance-dominant. It did not adequately show
geometry. r13 adds explicit virtual geometry terms:

- round-hole boundary cells (`surface_region_id == 7`);
- corner proximity from the x/y wall distances;
- local half-thickness percentile;
- far-end distance from the gate/vent direction;
- advancing unfilled-front and derived air-entrapment fields.

The final display therefore shows both a far-end band and a ring around the
round-hole boundary. This is a shape-aware candidate visualization. It is not a
compressible-air/vent-network solution and cannot establish actual trapped-air
volume or pressure without measured vent pressure and gas-flow data.

The hole ring and far-end band were confirmed in first/middle/final frame
contact sheets and remain persistent after full fill.
