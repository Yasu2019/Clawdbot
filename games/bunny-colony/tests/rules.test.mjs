import test from "node:test";
import assert from "node:assert/strict";
import {
  canAfford, defenseStrength, phaseAt, populationCap, productionPerSecond,
  purchase, resolveRaid, validCell
} from "../src/rules.js";

test("day phases have stable boundaries", () => {
  assert.equal(phaseAt(0).name, "朝");
  assert.equal(phaseAt(15).name, "昼");
  assert.equal(phaseAt(38).name, "夕方");
  assert.equal(phaseAt(48).name, "夜");
  assert.equal(phaseAt(60).name, "朝");
});

test("building purchase is atomic and rejects insufficient resources", () => {
  assert.equal(canAfford({ wood: 17, carrots: 99 }, "burrow"), false);
  assert.equal(purchase({ wood: 17, carrots: 99 }, "burrow"), null);
  assert.deepEqual(purchase({ wood: 18, carrots: 4 }, "burrow"), { wood: 0, carrots: 4 });
});

test("production scales with buildings and workers", () => {
  const buildings = [{ type: "farm" }, { type: "farm" }, { type: "lumber" }];
  assert.deepEqual(productionPerSecond(buildings, 10), { carrots: 3.2, wood: 1.1 });
});

test("burrows increase cap and occupied cells are invalid", () => {
  const buildings = [{ type: "burrow", col: 2, row: 3 }, { type: "burrow", col: 4, row: 4 }];
  assert.equal(populationCap(buildings), 12);
  assert.equal(validCell(buildings, 2, 3), false);
  assert.equal(validCell(buildings, 0, 0), true);
  assert.equal(validCell(buildings, 12, 0), false);
});

test("watchtowers prevent losses while weak colonies lose bounded population", () => {
  assert.equal(defenseStrength([{ type: "watch" }], 4), 6);
  const safe = resolveRaid({ day: 2, buildings: [{ type: "watch" }], bunnies: 4, happiness: 80 });
  assert.equal(safe.lost, 0);
  const weak = resolveRaid({ day: 7, buildings: [], bunnies: 4, happiness: 80 });
  assert.equal(weak.bunnies, 1);
  assert.equal(weak.lost, 3);
});
