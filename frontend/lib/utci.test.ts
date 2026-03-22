import assert from "node:assert/strict";

import type { PriorityZonesCollection } from "./artifacts";
import { classifyUtciEquivalentTemperature, decoratePriorityZonesWithUtci } from "./utci";

const input: PriorityZonesCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { priority_score: 0.846, zone_id: "zone-a" },
      geometry: { type: "Polygon", coordinates: [] },
    },
    {
      type: "Feature",
      properties: { priority_score: 1.0, zone_id: "zone-b" },
      geometry: { type: "Polygon", coordinates: [] },
    },
  ],
};

const zones = decoratePriorityZonesWithUtci(input);

assert.equal(classifyUtciEquivalentTemperature(30).label, "no thermal stress");
assert.equal(classifyUtciEquivalentTemperature(40).label, "strong heat stress");
assert.equal(zones.features[0].properties.utci_level, "no thermal stress");
assert.equal(zones.features[1].properties.utci_level, "very strong heat stress");
assert.equal(typeof zones.features[0].properties.utci_equivalent_temperature, "number");
