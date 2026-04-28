/**
 * Preset sizes.
 * chest / bodyLength / sleeveLength are the three user-facing measurements.
 * Everything else is derived inside the pattern math.
 *
 * All values in cm. Body length = CO edge to underarm split.
 * Sleeve length = CO edge to underarm split.
 */
export const PRESET_SIZES = {
  XS:  { label: "XS",  chest: 80,  bodyLength: 38, sleeveLength: 46 },
  S:   { label: "S",   chest: 88,  bodyLength: 40, sleeveLength: 48 },
  M:   { label: "M",   chest: 96,  bodyLength: 42, sleeveLength: 50 },
  L:   { label: "L",   chest: 104, bodyLength: 44, sleeveLength: 52 },
  XL:  { label: "XL",  chest: 112, bodyLength: 46, sleeveLength: 54 },
  XXL: { label: "XXL", chest: 120, bodyLength: 48, sleeveLength: 56 },
};

export const PRESET_KEYS = Object.keys(PRESET_SIZES);
