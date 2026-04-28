/**
 * Pattern: Raglan Sweater with Mock Neck
 * Construction: bottom-up, worked in the round.
 *
 * Two public exports:
 *   compute(gauge, measurements) → stats object (all the numbers)
 *   buildInstructions(stats)     → string of knitting instructions
 */

import { cmToSt, cmToRow } from "../utils/gauge.js";

// ─── Constants ────────────────────────────────────────────────────────────────

const RIBBING_CM        = 5;    // wrist and body rib height
const MOCK_NECK_CM      = 8;    // mock neck height
const NECK_CIRC_CM      = 36;   // standard neck circumference
const WRIST_CIRC_CM     = 18;   // standard wrist circumference
const UNDERARM_CM       = 3;    // underarm stitches width (per side)
const UPPER_ARM_RATIO   = 0.37; // upper arm circ as fraction of chest
const YOKE_DEPTH_RATIO  = 0.22; // yoke depth as fraction of chest

// ─── Compute ──────────────────────────────────────────────────────────────────

/**
 * Compute all stitch and row counts for a raglan yoke sweater.
 * Returns a plain object — no formatting, just numbers.
 */
export function compute(gauge, measurements) {
  const { stPer10, rowPer10 } = gauge;
  const { chest, bodyLength, sleeveLength } = measurements;

  const toSt  = (cm) => cmToSt(cm, stPer10);
  const toRow = (cm) => cmToRow(cm, rowPer10);

  // ── Derived measurements ────────────────────────────────────────
  const upperArm   = Math.round(chest * UPPER_ARM_RATIO);
  const yokeDepth  = Math.round(chest * YOKE_DEPTH_RATIO);

  // ── Body ────────────────────────────────────────────────────────
  const bodyCO     = toSt(chest);
  const ribRows    = toRow(RIBBING_CM);
  const bodyStRows = toRow(bodyLength - yokeDepth - RIBBING_CM);

  // Underarm hold: same width each side on body and sleeve
  const underarmSts = Math.max(4, toSt(UNDERARM_CM));

  // ── Sleeves ─────────────────────────────────────────────────────
  const sleeveCO     = toSt(WRIST_CIRC_CM);
  const sleeveTopSts = toSt(upperArm);
  const slvRibRows   = toRow(RIBBING_CM);
  const slvWorkRows  = toRow(sleeveLength - RIBBING_CM);

  // Increase pairs needed (each inc round adds 2 sts)
  const slvIncs     = Math.max(0, (sleeveTopSts - sleeveCO) / 2);
  const slvIncEvery = slvIncs > 0
    ? Math.max(2, Math.floor(slvWorkRows / slvIncs))
    : 0;

  // ── Yoke ────────────────────────────────────────────────────────
  // After separating underarms, remaining live sts:
  const bodyYoke = bodyCO - 2 * underarmSts;       // front + back combined
  const slvYoke  = sleeveTopSts - underarmSts;     // per sleeve

  // Join total: body + 2 sleeves + 4 raglan seam sts (1 per seam)
  const totalYoke = bodyYoke + 2 * slvYoke + 4;

  const neckSts    = toSt(NECK_CIRC_CM);
  const yokeRows   = toRow(yokeDepth);

  // Each dec round removes 8 sts (k2tog + ssk × 4 seams)
  const stToRemove = Math.max(0, totalYoke - neckSts);
  const decRounds  = Math.min(
    Math.floor(stToRemove / 8),
    Math.floor(yokeRows / 2),
  );
  const extraRows  = Math.max(0, yokeRows - decRounds * 2);
  const neckStsAfterDec = totalYoke - decRounds * 8;

  // ── Mock neck ───────────────────────────────────────────────────
  const mockNeckRows = toRow(MOCK_NECK_CM);

  return {
    // gauge
    stPer10, rowPer10,
    // user inputs
    chest, bodyLength, sleeveLength,
    // derived measurements
    upperArm, yokeDepth,
    wristCirc: WRIST_CIRC_CM,
    neckCirc: NECK_CIRC_CM,
    mockNeckCm: MOCK_NECK_CM,
    ribbingCm: RIBBING_CM,
    // body
    bodyCO, ribRows, bodyStRows,
    halfBody: bodyCO / 2,
    underarmSts,
    // sleeves
    sleeveCO, sleeveTopSts, slvRibRows, slvWorkRows, slvIncs, slvIncEvery,
    // yoke
    bodyYoke, slvYoke, totalYoke, neckSts, neckStsAfterDec,
    stToRemove, decRounds, yokeRows, extraRows,
    // mock neck
    mockNeckRows,
  };
}

// ─── Validate ─────────────────────────────────────────────────────────────────

/**
 * Returns an array of error strings. Empty array = all good.
 */
export function validateInputs(gauge, measurements) {
  const errors = [];
  const { stPer10, rowPer10 } = gauge;
  const { chest, bodyLength, sleeveLength } = measurements;

  if (!stPer10  || stPer10  < 8  || stPer10  > 50) errors.push("Stitches per 10 cm must be between 8 and 50.");
  if (!rowPer10 || rowPer10 < 8  || rowPer10 > 80) errors.push("Rows per 10 cm must be between 8 and 80.");
  if (!chest        || chest        < 60  || chest        > 200) errors.push("Chest must be between 60 and 200 cm.");
  if (!bodyLength   || bodyLength   < 20  || bodyLength   > 80)  errors.push("Body length must be between 20 and 80 cm.");
  if (!sleeveLength || sleeveLength < 30  || sleeveLength > 80)  errors.push("Sleeve length must be between 30 and 80 cm.");

  if (errors.length === 0) {
    const yokeDepth = Math.round(chest * YOKE_DEPTH_RATIO);
    if (bodyLength - yokeDepth - RIBBING_CM < 2) {
      errors.push(
        `Body length (${bodyLength} cm) is too short for a yoke of ${yokeDepth} cm. ` +
        `Increase body length to at least ${yokeDepth + RIBBING_CM + 5} cm.`
      );
    }
  }

  return errors;
}

// ─── Instruction builder ──────────────────────────────────────────────────────

export function buildInstructions(c) {
  const lines = [];
  const p  = (s = "") => lines.push(s);
  const h  = (s)      => p(`━━━ ${s} ━━━`);

  p(`RAGLAN SWEATER WITH MOCK NECK`);
  p(`Gauge    ${c.stPer10} sts × ${c.rowPer10} rows / 10 cm`);
  p(`Chest    ${c.chest} cm finished`);
  p();

  p(`MATERIALS`);
  p(`- Circular needle, 80 cm or longer`);
  p(`- 5 stitch markers (4 raglan + 1 BOR)`);
  p(`- Stitch holders or waste yarn`);
  p();

  p(`ABBREVIATIONS`);
  p(`CO cast on  |  BOR beginning of round  |  k knit  |  p purl`);
  p(`k2tog knit 2 together (right-leaning dec)  |  ssk slip, slip, knit (left-leaning dec)`);
  p(`m1l / m1r make 1 left / right  |  pm place marker  |  sm slip marker  |  BO bind off`);
  p();

  // ── Body ────────────────────────────────────────────────────────
  h(`BODY`);
  p();
  p(`CO ${c.bodyCO} sts. Join to work in the round, pm for BOR.`);
  p(`Do not twist.`);
  p();
  p(`Ribbing (~${c.ribbingCm} cm / ${c.ribRows} rounds):`);
  p(`Work in 2×2 rib (k2, p2) for ${c.ribRows} rounds.`);
  p();
  p(`Body (~${c.bodyLength - c.yokeDepth - c.ribbingCm} cm / ${c.bodyStRows} rounds):`);
  p(`Work in stockinette (knit every round) for ${c.bodyStRows} rounds.`);
  p(`Piece should measure approx. ${c.bodyLength - c.yokeDepth} cm from CO edge.`);
  p();
  p(`Underarm separation:`);
  p(`Place the first ${c.underarmSts / 2} sts and last ${c.underarmSts / 2} sts`);
  p(`(${c.underarmSts} sts total, centred on the BOR marker) onto waste yarn.`);
  p(`This is the front underarm.`);
  p(`Count to the opposite side of the round. Place the centre ${c.underarmSts} sts`);
  p(`of the back onto a second piece of waste yarn.`);
  p(`${c.bodyYoke} live body sts remain. Set aside.`);
  p();

  // ── Sleeves ─────────────────────────────────────────────────────
  h(`SLEEVES (make 2)`);
  p();
  p(`CO ${c.sleeveCO} sts. Join in the round, pm for BOR.`);
  p();
  p(`Ribbing (~${c.ribbingCm} cm / ${c.slvRibRows} rounds):`);
  p(`Work in 2×2 rib for ${c.slvRibRows} rounds.`);
  p();
  p(`Sleeve shaping:`);
  if (c.slvIncs > 0) {
    p(`Inc round: k1, m1l, knit to last st, m1r, k1. (+2 sts)`);
    p(`Work this inc round every ${c.slvIncEvery} rounds, ${c.slvIncs} times total.`);
    p(`Work plain stockinette between inc rounds.`);
    p(`After all increases: ${c.sleeveTopSts} sts.`);
  } else {
    p(`No shaping needed — work sleeve straight in stockinette.`);
  }
  p();
  p(`Continue in stockinette until sleeve measures ${c.sleeveLength} cm from CO.`);
  p();
  p(`Underarm separation:`);
  p(`Place first ${c.underarmSts / 2} and last ${c.underarmSts / 2} sts onto waste yarn`);
  p(`(${c.underarmSts} sts total). ${c.slvYoke} live sleeve sts remain.`);
  p(`Set aside. Knit second sleeve identically.`);
  p();

  // ── Yoke ────────────────────────────────────────────────────────
  h(`YOKE`);
  p();
  p(`Join all pieces on long circular needle:`);
  p(`  Left sleeve  (${c.slvYoke} sts), pm [raglan],`);
  p(`  Front body   (${c.halfBody - c.underarmSts} sts), pm [raglan],`);
  p(`  Right sleeve (${c.slvYoke} sts), pm [raglan],`);
  p(`  Back body    (${c.halfBody - c.underarmSts} sts), pm [raglan].`);
  p(`Each raglan marker flanks 1 seam stitch (picked up from the join gap).`);
  p(`Total: ~${c.totalYoke} sts. Place BOR marker at start of left sleeve.`);
  p();
  p(`Raglan decrease sequence:`);
  p(`  Dec round  : *k to 1 st before raglan marker, k2tog,`);
  p(`               sm, k1 (seam st), sm, ssk* — repeat 4 times. (−8 sts)`);
  p(`  Plain round: knit all sts.`);
  p();
  p(`Alternate dec round / plain round for ${c.decRounds} dec rounds total`);
  p(`(= ${c.decRounds * 2} rounds, approx. ${c.yokeDepth} cm yoke depth).`);
  if (c.extraRows > 0) {
    p(`Then work ${c.extraRows} plain round(s) to reach full yoke depth.`);
  }
  p(`Approx. ${c.neckStsAfterDec} sts remain after all decreases.`);
  p();

  // ── Mock neck ────────────────────────────────────────────────────
  h(`MOCK NECK`);
  p();
  p(`Work in 2×2 rib (k2, p2) for ${c.mockNeckRows} rounds (~${c.mockNeckCm} cm).`);
  p(`BO all sts loosely in rib pattern.`);
  p();

  // ── Finishing ───────────────────────────────────────────────────
  h(`FINISHING`);
  p();
  p(`Underarms:`);
  p(`Return the held underarm sts to needles (${c.underarmSts} body sts + ${c.underarmSts} sleeve sts`);
  p(`per side). Graft together using Kitchener stitch, or join with 3-needle BO.`);
  p();
  p(`Weave in all ends. Wet block to finished measurements.`);
  p();
  p(`FINISHED MEASUREMENTS`);
  p(`${"─".repeat(42)}`);
  p(`  Chest circumference     ${c.chest} cm`);
  p(`  Body (CO → underarm)    ${c.bodyLength - c.yokeDepth} cm`);
  p(`  Yoke depth              ${c.yokeDepth} cm`);
  p(`  Sleeve (CO → underarm)  ${c.sleeveLength} cm`);
  p(`  Upper arm               ${c.upperArm} cm`);
  p(`  Neck circumference      ${c.neckCirc} cm`);
  p(`  Mock neck height        ${c.mockNeckCm} cm`);
  p(`${"─".repeat(42)}`);

  return lines.join("\n");
}
