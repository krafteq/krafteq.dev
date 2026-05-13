/**
 * Core gauge math helpers.
 * All stitch/row calculations go through here so rounding
 * is consistent across every pattern.
 */

/** Round to nearest even number (keeps symmetry for 2-sided shaping) */
export const roundEven = (n) => Math.round(n / 2) * 2;

/** Convert cm to stitch count */
export const cmToSt = (cm, stPer10) =>
  roundEven(Math.round((cm * stPer10) / 10));

/** Convert cm to row count */
export const cmToRow = (cm, rowPer10) =>
  Math.round((cm * rowPer10) / 10);

/** Convert stitch count back to cm (for display / sanity checks) */
export const stToCm = (sts, stPer10) =>
  Math.round((sts / stPer10) * 10 * 10) / 10;

/** Validate gauge inputs */
export const validateGauge = ({ stPer10, rowPer10 }) => {
  const errors = [];
  if (!stPer10 || stPer10 < 8 || stPer10 > 50)
    errors.push("Stitches per 10 cm must be between 8 and 50.");
  if (!rowPer10 || rowPer10 < 8 || rowPer10 > 80)
    errors.push("Rows per 10 cm must be between 8 and 80.");
  return errors;
};
