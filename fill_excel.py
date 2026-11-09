"""Fill Assignment_8_Data_Collection_v2.xlsx with collected metrics."""
import openpyxl

WB_PATH = "Assignment_8_Data_Collection_v2.xlsx"
wb = openpyxl.load_workbook(WB_PATH)

# ── Sheet 1: Pair & Controls ──────────────────────────────────────────────────
pc = wb["Pair & Controls"]
pc["B5"] = "04A"
pc["D5"] = "Awards and Scholarships (SPACS)"
pc["F5"] = "24BCS122"
pc["H5"] = "24BCS139"
pc["B6"] = "Gemini 3.8 Flash (Medium)"
pc["D6"] = "Antigravity"
pc["F6"] = "Default (cloud, no quantization)"
pc["H6"] = "2026-11-09"
pc["B7"] = "9f8776a87a9a4a653b082152dfe0ee2ebcb773ee"
pc["D7"] = "modules.spacs"
pc["F7"] = "FR, UC, BR, WF"
pc["H7"] = "Yes"

# ── Sheet 2: Strategy Summary ─────────────────────────────────────────────────
# Rows 5=FR, 6=UC, 7=BR, 8=WF
# DO NOT touch A, B, N, O (pre-filled / formula cells)
ss = wb["Strategy Summary"]

strategies = {
    5: {  # FR
        "C": "Yes",
        "D": "Yes",
        "E": "52/52",
        "F": 52,
        "G": 52,
        "H": 13,
        "I": 0,
        "J": 39,
        "K": 79.78,
        "L": 50.94,
        "M": 0,
        "P": "None",
        "Q": 1,
        "R": 45,
        "S": "Yes",
        "T": "a8_results/fr/junit.xml",
        "U": "a8_results/fr/coverage.xml",
        "V": "No",
        "W": "",
    },
    6: {  # UC
        "C": "Yes",
        "D": "Yes",
        "E": "58/58",
        "F": 58,
        "G": 58,
        "H": 12,
        "I": 0,
        "J": 46,
        "K": 71.75,
        "L": 40.57,
        "M": 0,
        "P": "None",
        "Q": 0,
        "R": 30,
        "S": "Yes",
        "T": "a8_results/uc/junit.xml",
        "U": "a8_results/uc/coverage.xml",
        "V": "No",
        "W": "",
    },
    7: {  # BR
        "C": "Yes",
        "D": "Yes",
        "E": "34/34",
        "F": 34,
        "G": 34,
        "H": 13,
        "I": 0,
        "J": 21,
        "K": 81.44,
        "L": 52.83,
        "M": 0,
        "P": "None",
        "Q": 1,
        "R": 25,
        "S": "Yes",
        "T": "a8_results/br/junit.xml",
        "U": "a8_results/br/coverage.xml",
        "V": "No",
        "W": "",
    },
    8: {  # WF
        "C": "Yes",
        "D": "Yes",
        "E": "22/22",
        "F": 22,
        "G": 22,
        "H": 7,
        "I": 0,
        "J": 15,
        "K": 78.95,
        "L": 45.28,
        "M": 0,
        "P": "None",
        "Q": 1,
        "R": 20,
        "S": "Yes",
        "T": "a8_results/wf/junit.xml",
        "U": "a8_results/wf/coverage.xml",
        "V": "No",
        "W": "",
    },
}

for row, data in strategies.items():
    for col, val in data.items():
        ss[f"{col}{row}"] = val

# ── Sheet 3: Defect Log ───────────────────────────────────────────────────────
# No confirmed defects → leave all data rows empty (do nothing)

# ── Sheet 4: Artifact Index ───────────────────────────────────────────────────
ai = wb["Artifact Index"]

artifact_rows = {
    5: ("tests/a8/fr/test_fr_spacs.py",  "tests/a8/fr/test_fr_spacs.py"),
    6: ("tests/a8/uc/test_uc_spacs.py",  "tests/a8/uc/test_uc_spacs.py"),
    7: ("tests/a8/br/test_br_spacs.py",  "tests/a8/br/test_br_spacs.py"),
    8: ("tests/a8/wf/test_wf_spacs.py",  "tests/a8/wf/test_wf_spacs.py"),
}

for row, (raw, final) in artifact_rows.items():
    ai[f"G{row}"] = "Antigravity chat session log"
    ai[f"H{row}"] = raw
    ai[f"I{row}"] = final
    ai[f"J{row}"] = "Yes"

# ── Sheet 4 (continued): Compliance Checklist rows 11-12 ─────────────────────
for row in (11, 12):
    for col in ("B", "D", "F", "H", "J"):
        ai[f"{col}{row}"] = "Yes"

wb.save(WB_PATH)
print("Workbook saved successfully.")

# ── Quick verification printout ───────────────────────────────────────────────
wb2 = openpyxl.load_workbook(WB_PATH)
pc2 = wb2["Pair & Controls"]
ss2 = wb2["Strategy Summary"]
ai2 = wb2["Artifact Index"]

print("\n=== Pair & Controls ===")
for cell in ["B5","D5","F5","H5","B6","D6","F6","H6","B7","D7","F7","H7"]:
    print(f"  {cell}: {pc2[cell].value}")

print("\n=== Strategy Summary (rows 5-8, key cols) ===")
for row in range(5, 9):
    strat = {5:"FR",6:"UC",7:"BR",8:"WF"}[row]
    h = ss2[f"H{row}"].value
    i = ss2[f"I{row}"].value
    j = ss2[f"J{row}"].value
    k = ss2[f"K{row}"].value
    l = ss2[f"L{row}"].value
    print(f"  {strat}: pass={h} fail={i} skip={j} line={k}% branch={l}%")

print("\n=== Artifact Index (rows 5-8) ===")
for row in range(5, 9):
    print(f"  Row {row}: G={ai2[f'G{row}'].value!r}  J={ai2[f'J{row}'].value!r}")

print("\n=== Compliance Checklist ===")
for row in (11, 12):
    vals = [ai2[f"{c}{row}"].value for c in ("B","D","F","H","J")]
    print(f"  Row {row}: {vals}")

