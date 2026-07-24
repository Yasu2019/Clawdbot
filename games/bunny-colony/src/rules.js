export const GRID = { columns: 12, rows: 7, cell: 72, left: 208, top: 126 };
export const DAY_LENGTH = 60;
export const PHASES = [
  { name: "朝", start: 0, color: "#92b678" },
  { name: "昼", start: 15, color: "#79a968" },
  { name: "夕方", start: 38, color: "#b9855d" },
  { name: "夜", start: 48, color: "#263852" }
];
export const BUILDINGS = {
  burrow: { label: "巣穴", wood: 18, carrots: 0, color: "#9b6b45" },
  farm: { label: "畑", wood: 12, carrots: 0, color: "#d39b45" },
  lumber: { label: "木こり場", wood: 0, carrots: 10, color: "#5a7745" },
  watch: { label: "見張り台", wood: 22, carrots: 0, color: "#6a5966" }
};

export function phaseAt(second) {
  const t = ((second % DAY_LENGTH) + DAY_LENGTH) % DAY_LENGTH;
  return [...PHASES].reverse().find((phase) => t >= phase.start);
}

export function canAfford(resources, type) {
  const cost = BUILDINGS[type];
  return Boolean(cost) && resources.wood >= cost.wood && resources.carrots >= cost.carrots;
}

export function purchase(resources, type) {
  if (!canAfford(resources, type)) return null;
  const cost = BUILDINGS[type];
  return { ...resources, wood: resources.wood - cost.wood, carrots: resources.carrots - cost.carrots };
}

export function productionPerSecond(buildings, bunnies) {
  const farms = buildings.filter((b) => b.type === "farm").length;
  const lumber = buildings.filter((b) => b.type === "lumber").length;
  const workers = Math.max(1, bunnies);
  return {
    carrots: farms * Math.min(1.8, workers * 0.16),
    wood: lumber * Math.min(1.25, workers * 0.11)
  };
}

export function populationCap(buildings) {
  return 4 + buildings.filter((b) => b.type === "burrow").length * 4;
}

export function raidStrength(day) {
  return 2 + day * 2;
}

export function defenseStrength(buildings, bunnies) {
  const towers = buildings.filter((b) => b.type === "watch").length;
  return towers * 5 + Math.floor(bunnies / 4);
}

export function resolveRaid(state) {
  const attack = raidStrength(state.day);
  const defense = defenseStrength(state.buildings, state.bunnies);
  const deficit = Math.max(0, attack - defense);
  const lost = Math.min(state.bunnies - 1, Math.ceil(deficit / 3));
  return {
    attack,
    defense,
    lost: Math.max(0, lost),
    bunnies: Math.max(1, state.bunnies - Math.max(0, lost)),
    happiness: Math.max(0, state.happiness - deficit * 2)
  };
}

export function validCell(buildings, col, row) {
  return col >= 0 && row >= 0 && col < GRID.columns && row < GRID.rows &&
    !buildings.some((building) => building.col === col && building.row === row);
}
