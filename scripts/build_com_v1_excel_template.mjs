import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const rootDir = path.resolve(".");
const outputDir = path.join(rootDir, "templates");
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const headerFill = "#1F4E78";
const subHeaderFill = "#D9EAF7";
const borderColor = "#D9D9D9";

function styleTitle(sheet, range, title) {
  sheet.getRange(range).values = [[title]];
  sheet.getRange(range).format = {
    fill: headerFill,
    font: { bold: true, color: "#FFFFFF" },
  };
}

function writeTable(sheet, startCell, rows) {
  const range = sheet.getRange(startCell).resize(rows.length, rows[0].length);
  range.values = rows;
  range.format.borders = { preset: "all", style: "thin", color: borderColor };
  range.format.wrapText = true;
  range.getRow(0).format = {
    fill: subHeaderFill,
    font: { bold: true, color: "#000000" },
  };
  return range;
}

function finishSheet(sheet, usedRange) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(3);
  sheet.getRange(usedRange).format.autofitColumns();
  sheet.getRange(usedRange).format.autofitRows();
}

const fixed = workbook.worksheets.add("fixed_config");
styleTitle(fixed, "A1", "Fixed Parameters");
writeTable(fixed, "A3", [
  ["Domain", "Parameter", "Value", "Unit", "Description"],
  ["link", "fb", 106.25e9, "Hz", "Signaling rate / baud rate."],
  ["link", "per_ui", 32, "samples/UI", "Oversampling ratio M."],
  ["link", "target_df", 50e6, "Hz", "Target frequency step."],
  ["filter", "c_m3", 0, "dimensionless", "TX FFE c(-3), fixed default for single run."],
  ["filter", "c_m2", 0, "dimensionless", "TX FFE c(-2), fixed default if no search."],
  ["filter", "c_m1", 0, "dimensionless", "TX FFE c(-1), fixed default if no search."],
  ["filter", "c_1", 0, "dimensionless", "TX FFE c(1), fixed default if no search."],
  ["filter", "num_pre", 3, "tap index", "Main cursor index in TX FFE vector."],
  ["filter", "Tr", 4e-12, "s", "20%-80% transition time."],
  ["filter", "fr", 0.58 * 106.25e9, "Hz", "Receiver noise-filter 3 dB bandwidth."],
  ["filter", "g_DC", 2, "dB", "CTLE DC gain default if no search."],
  ["filter", "g_DC2", 0, "dB", "CTLE second DC gain default if no search."],
  ["filter", "f_z", 1000e9, "Hz", "CTLE zero frequency."],
  ["filter", "f_LF", 1.328125e9, "Hz", "Low-frequency pole/zero term."],
  ["filter", "f_p1", 1000e9, "Hz", "CTLE pole 1."],
  ["filter", "f_p2", 1000e9, "Hz", "CTLE pole 2."],
  ["filter", "A_v", 0.413, "V", "Victim pulse amplitude."],
  ["filter", "A_fe", 0.413, "V", "FEXT aggressor pulse amplitude."],
  ["filter", "A_ne", 0.45, "V", "NEXT aggressor pulse amplitude."],
  ["txpkg_victim", "txpkg_victim.enable", true, "boolean", "Enable victim TX package model."],
  ["txpkg_victim", "txpkg_victim.C_d", 4e-14, "F", "Victim TX device shunt capacitance."],
  ["txpkg_victim", "txpkg_victim.L_s", 0.13e-9, "H", "Victim TX series inductance."],
  ["txpkg_victim", "txpkg_victim.C_b", 0.3e-13, "F", "Victim TX bump/interface shunt capacitance."],
  ["txpkg_victim", "txpkg_victim.z_p", 34, "mm", "Victim TX package transmission-line length."],
  ["txpkg_victim", "txpkg_victim.C_p", 0.4e-13, "F", "Victim TX package-to-board shunt capacitance."],
  ["txpkg_victim", "txpkg_victim.R0", 50, "ohm", "Victim TX single-ended reference resistance."],
  ["txpkg_victim", "txpkg_victim.Z_c", 87.5, "ohm", "Victim TX differential characteristic impedance."],
  ["txpkg_victim", "txpkg_victim.z_p2", "", "mm", "Victim TX optional package TL segment 2. Blank means disabled."],
  ["txpkg_victim", "txpkg_victim.Z_c2", 87.5, "ohm", "Victim TX optional segment 2 differential impedance."],
  ["txpkg_fext", "txpkg_fext.enable", true, "boolean", "Enable FEXT TX package model."],
  ["txpkg_fext", "txpkg_fext.C_d", 4e-14, "F", "FEXT TX device shunt capacitance."],
  ["txpkg_fext", "txpkg_fext.L_s", 0.13e-9, "H", "FEXT TX series inductance."],
  ["txpkg_fext", "txpkg_fext.C_b", 0.3e-13, "F", "FEXT TX bump/interface shunt capacitance."],
  ["txpkg_fext", "txpkg_fext.z_p", 34, "mm", "FEXT TX package transmission-line length."],
  ["txpkg_fext", "txpkg_fext.C_p", 0.4e-13, "F", "FEXT TX package-to-board shunt capacitance."],
  ["txpkg_fext", "txpkg_fext.R0", 50, "ohm", "FEXT TX single-ended reference resistance."],
  ["txpkg_fext", "txpkg_fext.Z_c", 87.5, "ohm", "FEXT TX differential characteristic impedance."],
  ["txpkg_fext", "txpkg_fext.z_p2", "", "mm", "FEXT TX optional package TL segment 2. Blank means disabled."],
  ["txpkg_fext", "txpkg_fext.Z_c2", 87.5, "ohm", "FEXT TX optional segment 2 differential impedance."],
  ["txpkg_next", "txpkg_next.enable", true, "boolean", "Enable NEXT TX package model."],
  ["txpkg_next", "txpkg_next.C_d", 4e-14, "F", "NEXT TX device shunt capacitance."],
  ["txpkg_next", "txpkg_next.L_s", 0.13e-9, "H", "NEXT TX series inductance."],
  ["txpkg_next", "txpkg_next.C_b", 0.3e-13, "F", "NEXT TX bump/interface shunt capacitance."],
  ["txpkg_next", "txpkg_next.z_p", 34, "mm", "NEXT TX package transmission-line length."],
  ["txpkg_next", "txpkg_next.C_p", 0.4e-13, "F", "NEXT TX package-to-board shunt capacitance."],
  ["txpkg_next", "txpkg_next.R0", 50, "ohm", "NEXT TX single-ended reference resistance."],
  ["txpkg_next", "txpkg_next.Z_c", 87.5, "ohm", "NEXT TX differential characteristic impedance."],
  ["txpkg_next", "txpkg_next.z_p2", "", "mm", "NEXT TX optional package TL segment 2. Blank means disabled."],
  ["txpkg_next", "txpkg_next.Z_c2", 87.5, "ohm", "NEXT TX optional segment 2 differential impedance."],
  ["rxpkg", "rxpkg.enable", true, "boolean", "Enable shared RX package model."],
  ["rxpkg", "rxpkg.C_d", 4e-14, "F", "RX device shunt capacitance."],
  ["rxpkg", "rxpkg.L_s", 0.13e-9, "H", "RX series inductance."],
  ["rxpkg", "rxpkg.C_b", 0.3e-13, "F", "RX bump/interface shunt capacitance."],
  ["rxpkg", "rxpkg.z_p", 34, "mm", "RX package transmission-line length."],
  ["rxpkg", "rxpkg.C_p", 0.4e-13, "F", "RX package-to-board shunt capacitance."],
  ["rxpkg", "rxpkg.R0", 50, "ohm", "RX single-ended reference resistance."],
  ["rxpkg", "rxpkg.Z_c", 87.5, "ohm", "RX differential characteristic impedance."],
  ["rxpkg", "rxpkg.z_p2", "", "mm", "RX optional package TL segment 2. Blank means disabled."],
  ["rxpkg", "rxpkg.Z_c2", 87.5, "ohm", "RX optional segment 2 differential impedance."],
  ["dfe", "N_b", 1, "UI/taps", "Fixed DFE tap count."],
  ["dfe", "b_max", 0.85, "dimensionless", "Normalized fixed DFE coefficient limit."],
  ["impairment", "R_LM", 0.95, "dimensionless", "Level separation mismatch ratio."],
  ["impairment", "SNR_TX", 33, "dB", "Transmitter SNR."],
  ["impairment", "sigma_RJ", 0.01, "UI", "Random jitter RMS."],
  ["impairment", "A_DD", 0.02, "UI", "Dual-Dirac jitter peak."],
  ["impairment", "eta_0", 6e-18, "V^2/Hz", "One-sided noise spectral density."],
  ["com", "L", 4, "levels", "Number of signal levels."],
  ["com", "DER_0", 0.0002, "dimensionless", "Target detector error ratio."],
  ["pmf", "dy_override", "", "V", "Blank means derive from As."],
  ["pmf", "dy_rel_As", 0.001, "dimensionless", "PMF dy relative to As."],
  ["pmf", "dy_abs_max", 0.00001, "V", "PMF dy absolute maximum."],
  ["pmf", "tap_abs_th_override", "", "V", "Blank means derive from As."],
  ["pmf", "tap_rel_As", 0.001, "dimensionless", "Tap threshold relative to As."],
  ["pmf", "keep_mass", 1, "probability", "PMF truncation target."],
  ["pmf", "gaussian_n_sigma", 8, "sigma", "Gaussian PMF half span."],
]);
fixed.getRange("C4:C90").format.numberFormat = "0.000000E+00";
finishSheet(fixed, "A1:E90");

const search = workbook.worksheets.add("search_config");
styleTitle(search, "A1", "93A Search Parameters");
writeTable(search, "A3", [
  ["Parameter", "Enabled", "Values", "Unit", "Description"],
  ["c_m2", true, "0:0.1:0.4", "dimensionless", "TX FFE c(-2). Values support start:step:stop or comma-separated list."],
  ["c_m1", true, "-0.6:0.1:0", "dimensionless", "TX FFE c(-1)."],
  ["c_1", true, "-0.6:0.1:0", "dimensionless", "TX FFE c(1)."],
  ["g_DC", true, "2:1:12", "dB", "CTLE DC gain."],
  ["g_DC2", true, "0:0.5:3", "dB", "CTLE second DC gain."],
  ["keep_top_n", true, 10, "count", "Number of successful candidate summary rows retained."],
  ["keep_all_rows", true, false, "boolean", "True keeps all summary rows. Usually false for full search."],
  ["continue_on_error", true, false, "boolean", "True stores candidate errors instead of stopping immediately."],
]);
finishSheet(search, "A1:E13");

const channels = workbook.worksheets.add("channels");
styleTitle(channels, "A1", "Channel Files");
writeTable(channels, "A3", [
  ["Kind", "Index", "S4P Path", "Port Order", "R0 Ohm", "Gamma Source", "Gamma Load", "Use", "Description"],
  ["victim", 0, "reference_data/pychopmarg_example2/chnl_data/example2_THRU.s4p", "0,2,1,3", 50, 0, 0, true, "Victim through channel."],
  ["next", 1, "reference_data/pychopmarg_example2/chnl_data/example2_NEXT1.s4p", "0,2,1,3", 50, 0, 0, true, "NEXT path 1."],
  ["next", 2, "reference_data/pychopmarg_example2/chnl_data/example2_NEXT2.s4p", "0,2,1,3", 50, 0, 0, true, "NEXT path 2."],
  ["next", 3, "reference_data/pychopmarg_example2/chnl_data/example2_NEXT3.s4p", "0,2,1,3", 50, 0, 0, true, "NEXT path 3."],
  ["next", 4, "", "0,2,1,3", 50, 0, 0, false, "Optional NEXT path. Fill path and set Use=TRUE."],
  ["fext", 1, "reference_data/pychopmarg_example2/chnl_data/example2_FEXT1.s4p", "0,2,1,3", 50, 0, 0, true, "FEXT path 1."],
  ["fext", 2, "reference_data/pychopmarg_example2/chnl_data/example2_FEXT2.s4p", "0,2,1,3", 50, 0, 0, true, "FEXT path 2."],
  ["fext", 3, "", "0,2,1,3", 50, 0, 0, false, "Optional FEXT path. Fill path and set Use=TRUE."],
]);
finishSheet(channels, "A1:I13");

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

const fixedPreview = await workbook.render({
  sheetName: "fixed_config",
  range: "A1:E20",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "com_v1_params_template_preview.png"),
  new Uint8Array(await fixedPreview.arrayBuffer()),
);

const searchPreview = await workbook.render({
  sheetName: "search_config",
  range: "A1:E13",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "com_v1_search_config_preview.png"),
  new Uint8Array(await searchPreview.arrayBuffer()),
);

const channelPreview = await workbook.render({
  sheetName: "channels",
  range: "A1:I13",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "com_v1_channels_preview.png"),
  new Uint8Array(await channelPreview.arrayBuffer()),
);

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(path.join(outputDir, "com_v1_params_template.xlsx"));
