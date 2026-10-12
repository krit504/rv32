import cairo

W, H = 2200, 1150
BLACK = (0, 0, 0)
BLUE = (0.10, 0.45, 0.85)
RED = (0.75, 0.15, 0.15)
GREY = (0.55, 0.55, 0.55)

OUT = "/tmp/claude-1000/-home-kritin-Scratch-personal-sv-practice/pipeline_diagram_scratch/rv32i_pipeline_datapath.svg"

surf = cairo.SVGSurface(OUT, W, H)
ctx = cairo.Context(surf)
ctx.set_source_rgb(1, 1, 1)
ctx.rectangle(0, 0, W, H)
ctx.fill()

LABELS = []


def set_color(c):
    ctx.set_source_rgb(*c)


def line(pts, color=BLACK, width=1.6, dash=None):
    set_color(color)
    ctx.set_line_width(width)
    if dash:
        ctx.set_dash(dash)
    else:
        ctx.set_dash([])
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.stroke()
    ctx.set_dash([])


def text(x, y, s, size=13, color=BLACK, bold=False, italic=False, anchor="l"):
    LABELS.append((x, y, s, size, color, bold, italic, anchor))


def flush_labels():
    for (x, y, s, size, color, bold, italic, anchor) in LABELS:
        slant = cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL
        weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
        ctx.select_font_face("DejaVu Sans", slant, weight)
        ctx.set_font_size(size)
        xb, yb, tw, th, _, _ = ctx.text_extents(s)
        xx = x
        if anchor == "c":
            xx = x - tw / 2
        elif anchor == "r":
            xx = x - tw
        pad = 2
        ctx.set_source_rgb(1, 1, 1)
        ctx.rectangle(xx + xb - pad, y + yb - pad, tw + 2 * pad, th + 2 * pad)
        ctx.fill()
        set_color(color)
        ctx.move_to(xx, y)
        ctx.show_text(s)


def rect(x, y, w, h, color=BLACK, lw=1.8, dash=None):
    set_color(color)
    ctx.set_line_width(lw)
    if dash:
        ctx.set_dash(dash)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    ctx.set_dash([])


def clk_tri_up(x, y):
    set_color(BLACK)
    ctx.set_line_width(1.6)
    ctx.move_to(x - 6, y)
    ctx.line_to(x + 6, y)
    ctx.line_to(x, y - 9)
    ctx.close_path()
    ctx.stroke()


def clk_tri_down(x, y):
    set_color(BLACK)
    ctx.set_line_width(1.6)
    ctx.move_to(x - 6, y)
    ctx.line_to(x + 6, y)
    ctx.line_to(x, y + 9)
    ctx.close_path()
    ctx.stroke()


def mux2(x, y, w, h):
    set_color(BLACK)
    ctx.set_line_width(1.8)
    ctx.move_to(x, y)
    ctx.line_to(x, y + h)
    ctx.line_to(x + w, y + h * 0.72)
    ctx.line_to(x + w, y + h * 0.28)
    ctx.close_path()
    ctx.stroke()
    text(x + 4, y + h * 0.28 + 10, "0", size=10)
    text(x + 4, y + h - 4, "1", size=10)


def mux3(x, y, w, h):
    set_color(BLACK)
    ctx.set_line_width(1.8)
    ctx.move_to(x, y)
    ctx.line_to(x, y + h)
    ctx.line_to(x + w, y + h * 0.78)
    ctx.line_to(x + w, y + h * 0.22)
    ctx.close_path()
    ctx.stroke()
    text(x + 4, y + h * 0.22 + 10, "0", size=10)
    text(x + 4, y + h * 0.5 + 4, "1", size=10)
    text(x + 4, y + h - 5, "2", size=10)


def mux4(x, y, w, h):
    set_color(BLACK)
    ctx.set_line_width(1.8)
    ctx.move_to(x, y)
    ctx.line_to(x, y + h)
    ctx.line_to(x + w, y + h * 0.80)
    ctx.line_to(x + w, y + h * 0.20)
    ctx.close_path()
    ctx.stroke()
    for i, frac in enumerate([0.14, 0.38, 0.62, 0.86]):
        text(x + 5, y + h * frac + 4, str(i), size=10)


def alu_trap(x, y, w, h):
    set_color(BLACK)
    ctx.set_line_width(2.0)
    ctx.move_to(x, y)
    ctx.line_to(x, y + h * 0.32)
    ctx.line_to(x + w * 0.35, y + h * 0.5)
    ctx.line_to(x, y + h * 0.68)
    ctx.line_to(x, y + h)
    ctx.line_to(x + w, y + h * 0.75)
    ctx.line_to(x + w, y + h * 0.25)
    ctx.close_path()
    ctx.stroke()
    text(x + w * 0.55, y + h * 0.5 + 5, "ALU", size=15, bold=True, anchor="c")


def add_trap(x, y, w, h):
    set_color(BLACK)
    ctx.set_line_width(1.8)
    ctx.move_to(x, y)
    ctx.line_to(x, y + h * 0.32)
    ctx.line_to(x + w * 0.35, y + h * 0.5)
    ctx.line_to(x, y + h * 0.68)
    ctx.line_to(x, y + h)
    ctx.line_to(x + w, y + h * 0.75)
    ctx.line_to(x + w, y + h * 0.25)
    ctx.close_path()
    ctx.stroke()
    text(x + w * 0.55, y + h * 0.5 + 6, "+", size=18, bold=True, anchor="c")


def blue(pts, width=1.6, dash=None):
    line(pts, color=BLUE, width=width, dash=dash)


# ================================================================================
# LANES
# ================================================================================
LANE_TOP = 140
LANE_DY = 25
lanes_datapath = [
    ("PC",        "F D E"),
    ("PCPlus4",   "F D E M W"),
    ("Instr",     "F D"),
    ("RD1",       "D E"),
    ("RD2/WriteData", "D E M"),
    ("ImmExt",    "D E M W"),
    ("Rd",        "D E M W"),
    ("funct3",    "D E"),
    ("ALUResult", "E M W"),
    ("ReadData",  "M W"),
]
lanes_control = [
    ("RegWrite",   "D E M W"),
    ("ImmSrc",     "D"),
    ("ALUSrc",     "D E"),
    ("ALUSrcA",    "D E"),
    ("MemWrite",   "D E M"),
    ("Branch",     "D E"),
    ("ResultSrc",  "D E M W"),
    ("ALUControl", "D E"),
    ("PCSrc",      "D E"),
]
LANES = lanes_datapath + lanes_control
LANE_Y = {name: LANE_TOP + i * LANE_DY for i, (name, _) in enumerate(LANES)}
LANE_STAGES = {name: set(stages.split()) for name, stages in LANES}
LANE_COLOR = {name: BLACK for name, _ in lanes_datapath}
LANE_COLOR.update({name: BLUE for name, _ in lanes_control})
LANE_BOTTOM = LANE_TOP + (len(LANES) - 1) * LANE_DY

# ================================================================================
# STAGE COLUMNS  (each stage sized to what it actually needs to hold — Decode and
# Execute are the wide ones: Decode holds regfile+immgen+control_unit side by side,
# Execute holds the SrcA/SrcB muxes, the ALU, the PCTarget adder, and the
# branch/PCNextSelE resolve block)
# ================================================================================
BAR_W = 30
STAGE_W = {"F": 380, "D": 470, "E": 460, "M": 320, "W": 280}

F_X = 50
FD_X = F_X + STAGE_W["F"]
D_X = FD_X + BAR_W
DE_X = D_X + STAGE_W["D"]
E_X = DE_X + BAR_W
EM_X = E_X + STAGE_W["E"]
M_X = EM_X + BAR_W
MW_X = M_X + STAGE_W["M"]
Wb_X = MW_X + BAR_W
END_X = Wb_X + STAGE_W["W"]

STAGES = [
    ("FETCH", "F", F_X),
    ("DECODE", "D", D_X),
    ("EXECUTE", "E", E_X),
    ("MEMORY", "M", M_X),
    ("WRITEBACK", "W", Wb_X),
]
BARS = [
    ("F/D", FD_X),
    ("D/E", DE_X),
    ("E/M", EM_X),
    ("M/W", MW_X),
]
STAGE_LETTER_X = {"F": F_X, "D": D_X, "E": E_X, "M": M_X, "W": Wb_X}
STAGE_ORDER = ["F", "D", "E", "M", "W"]

for name, letter, x in STAGES:
    w = STAGE_W[letter]
    text(x + w / 2, 30, name, size=17, bold=True, anchor="c")
    line([(x, 45), (x, LANE_BOTTOM + 30)], color=GREY, width=1.0, dash=[3, 4])
    line([(x + w, 45), (x + w, LANE_BOTTOM + 30)], color=GREY, width=1.0, dash=[3, 4])

for name, x in BARS:
    rect(x, 60, BAR_W, LANE_BOTTOM - 60 + 40, lw=2.2)
    text(x + BAR_W / 2, 50, name, size=14, bold=True, anchor="c")

for name, stages_str in LANES:
    stages_here = LANE_STAGES[name]
    y = LANE_Y[name]
    col = LANE_COLOR[name]
    present_seq = [s for s in STAGE_ORDER if s in stages_here]
    if len(present_seq) >= 1:
        x_start = STAGE_LETTER_X[present_seq[0]]
        x_end = STAGE_LETTER_X[present_seq[-1]] + STAGE_W[present_seq[-1]]
        line([(x_start, y), (x_end, y)], color=col, width=1.3)
        text(x_start - 6, y - 5, name, size=10, color=col, anchor="r")

# ================================================================================
# FETCH
# ================================================================================
pc_y = LANE_Y["PC"]
pcp4_y = LANE_Y["PCPlus4"]
instr_y = LANE_Y["Instr"]

PCM_X, PCM_W, PCM_H = F_X + 15, 40, 105
PCM_Y = pc_y - PCM_H * 0.5
mux3(PCM_X, PCM_Y, PCM_W, PCM_H)
text(PCM_X - 4, PCM_Y - 10, "PCNext", size=11)

PC_X2, PC_W2, PC_H2 = PCM_X + PCM_W + 35, 50, 55
PC_Y2 = pc_y - PC_H2 / 2
rect(PC_X2, PC_Y2, PC_W2, PC_H2, lw=1.8)
text(PC_X2 + PC_W2 / 2, PC_Y2 + PC_H2 / 2 + 4, "PC", size=13, bold=True, anchor="c")
clk_tri_up(PC_X2 + PC_W2 / 2, PC_Y2 + PC_H2)
text(PC_X2 + PC_W2 / 2, PC_Y2 + PC_H2 + 18, "CLK", size=9, anchor="c")
line([(PCM_X + PCM_W, pc_y), (PC_X2, pc_y)])

IM_X2, IM_W2, IM_H2 = PC_X2 + PC_W2 + 55, 160, 170
IM_Y2 = instr_y - IM_H2 * 0.65
rect(IM_X2, IM_Y2, IM_W2, IM_H2, lw=1.8)
text(IM_X2 + IM_W2 / 2, IM_Y2 + IM_H2 / 2 - 20, "Instruction", size=13, bold=True, anchor="c")
text(IM_X2 + IM_W2 / 2, IM_Y2 + IM_H2 / 2, "Memory", size=13, bold=True, anchor="c")
text(IM_X2 + 6, IM_Y2 + 18, "A", size=11)
text(IM_X2 + IM_W2 - 10, IM_Y2 + IM_H2 - 14, "RD", size=11, anchor="r")

line([(PC_X2 + PC_W2, pc_y), (PC_X2 + PC_W2 + 15, pc_y), (PC_X2 + PC_W2 + 15, IM_Y2 + 18), (IM_X2, IM_Y2 + 18)])
line([(IM_X2 + IM_W2, IM_Y2 + IM_H2 - 14), (FD_X, instr_y)])

P4_X2, P4_W2, P4_H2 = PC_X2, 55, 55
P4_Y2 = pcp4_y - P4_H2 / 2
add_trap(P4_X2, P4_Y2, P4_W2, P4_H2)
text(P4_X2 - 18, P4_Y2 + P4_H2 * 0.75 + 4, "4", size=10)
line([(PC_X2 + PC_W2 / 2, PC_Y2 + PC_H2), (PC_X2 + PC_W2 / 2, P4_Y2 + P4_H2 * 0.25), (P4_X2, P4_Y2 + P4_H2 * 0.25)])
line([(P4_X2 + P4_W2, pcp4_y), (FD_X, pcp4_y)])

text(F_X + 10, 60, "PCF = PC.PCOut    PCPlus4F = PCF + 4", size=10, italic=True)

# ================================================================================
# DECODE
# ================================================================================
rd1_y = LANE_Y["RD1"]
rd2_y = LANE_Y["RD2/WriteData"]
immext_y = LANE_Y["ImmExt"]
rd_y = LANE_Y["Rd"]
funct3_y = LANE_Y["funct3"]

RF_X2, RF_W2, RF_H2 = D_X + 40, 190, 210
RF_Y2 = rd1_y - 40
rect(RF_X2, RF_Y2, RF_W2, RF_H2, lw=1.8)
text(RF_X2 + RF_W2 / 2, RF_Y2 + 24, "Register", size=13, bold=True, anchor="c")
text(RF_X2 + RF_W2 / 2, RF_Y2 + 44, "File", size=13, bold=True, anchor="c")
text(RF_X2 + 8, RF_Y2 + 68, "A1", size=10)
text(RF_X2 + 8, RF_Y2 + 88, "A2", size=10)
text(RF_X2 + 8, RF_Y2 + RF_H2 - 40, "A3", size=10)
text(RF_X2 + 8, RF_Y2 + RF_H2 - 20, "WD3", size=10)
text(RF_X2 + RF_W2 - 10, RF_Y2 + 68, "RD1", size=10, anchor="r")
text(RF_X2 + RF_W2 - 10, RF_Y2 + 88, "RD2", size=10, anchor="r")
clk_tri_up(RF_X2 + 30, RF_Y2 + RF_H2)
text(RF_X2 + 30, RF_Y2 + RF_H2 + 16, "negedge CLK", size=9, anchor="c")

line([(FD_X, instr_y), (RF_X2 - 24, instr_y), (RF_X2 - 24, RF_Y2 + 68), (RF_X2, RF_Y2 + 68)])
text(RF_X2 - 46, RF_Y2 + 62, "19:15", size=8)
line([(RF_X2 - 16, instr_y), (RF_X2 - 16, RF_Y2 + 88), (RF_X2, RF_Y2 + 88)])
text(RF_X2 - 46, RF_Y2 + 100, "24:20", size=8)

line([(RF_X2 + RF_W2, RF_Y2 + 68), (DE_X, rd1_y)])
line([(RF_X2 + RF_W2, RF_Y2 + 88), (DE_X, rd2_y)])

EX_X2, EX_W2, EX_H2 = RF_X2, 190, 55
EX_Y2 = immext_y - EX_H2 / 2
skew = 14
set_color(BLACK)
ctx.set_line_width(1.8)
ctx.move_to(EX_X2 + skew, EX_Y2)
ctx.line_to(EX_X2 + EX_W2, EX_Y2)
ctx.line_to(EX_X2 + EX_W2 - skew, EX_Y2 + EX_H2)
ctx.line_to(EX_X2, EX_Y2 + EX_H2)
ctx.close_path()
ctx.stroke()
text(EX_X2 + EX_W2 / 2, EX_Y2 + EX_H2 / 2 + 4, "Immediate Gen", size=11, bold=True, anchor="c")
line([(FD_X, instr_y), (EX_X2 - 32, instr_y), (EX_X2 - 32, EX_Y2 + 14), (EX_X2, EX_Y2 + 14)])
text(EX_X2 - 30, EX_Y2 + 6, "31:7", size=8)
line([(EX_X2 + EX_W2, immext_y), (DE_X, immext_y)])

CU_X2, CU_W2, CU_H2 = RF_X2 + RF_W2 + 70, 160, 240
CU_Y2 = 150
rect(CU_X2, CU_Y2, CU_W2, CU_H2, lw=2.2)
text(CU_X2 + CU_W2 / 2, CU_Y2 + 22, "Control", size=14, bold=True, anchor="c")
text(CU_X2 + CU_W2 / 2, CU_Y2 + 42, "Unit", size=14, bold=True, anchor="c")
text(CU_X2 + 8, CU_Y2 + 66, "op", size=10)
text(CU_X2 + 8, CU_Y2 + 84, "funct3", size=10)
text(CU_X2 + 8, CU_Y2 + 102, "funct7_5", size=10)

line([(FD_X, instr_y), (CU_X2 - 44, instr_y), (CU_X2 - 44, CU_Y2 + 66), (CU_X2, CU_Y2 + 66)])
text(CU_X2 - 40, CU_Y2 + 60, "6:0", size=8)
line([(CU_X2 - 34, instr_y), (CU_X2 - 34, CU_Y2 + 84), (CU_X2, CU_Y2 + 84)])
text(CU_X2 - 44, CU_Y2 + 96, "14:12", size=8)
line([(CU_X2 - 24, instr_y), (CU_X2 - 24, CU_Y2 + 102), (CU_X2, CU_Y2 + 102)])
text(CU_X2 - 24, CU_Y2 + 116, "30", size=8)

# funct3D tapped independently straight through to D/E bar
line([(FD_X, instr_y), (FD_X + 8, instr_y), (FD_X + 8, funct3_y), (DE_X, funct3_y)])
# RdD = InstrD[11:7] tapped straight through to D/E bar
line([(FD_X, instr_y), (FD_X + 16, instr_y), (FD_X + 16, rd_y), (DE_X, rd_y)])
text(FD_X + 4, rd_y - 6, "RdD = InstrD[11:7]", size=8, italic=True)

cu_outs = [
    ("RegWrite", LANE_Y["RegWrite"]),
    ("ImmSrc", LANE_Y["ImmSrc"]),
    ("ALUSrc", LANE_Y["ALUSrc"]),
    ("ALUSrcA", LANE_Y["ALUSrcA"]),
    ("MemWrite", LANE_Y["MemWrite"]),
    ("Branch", LANE_Y["Branch"]),
    ("ResultSrc", LANE_Y["ResultSrc"]),
    ("ALUControl", LANE_Y["ALUControl"]),
    ("PCSrc", LANE_Y["PCSrc"]),
]
for i, (nm, ly) in enumerate(cu_outs):
    cu_internal_y = CU_Y2 + 140 + i * 9
    stub_x = CU_X2 + CU_W2 + 14 + i * 4
    blue([(CU_X2 + CU_W2, cu_internal_y), (stub_x, cu_internal_y), (stub_x, ly), (DE_X, ly)])
blue([(EX_X2 + 60, EX_Y2 - 18), (EX_X2 + 60, EX_Y2)], width=1.4)
text(EX_X2 + 30, EX_Y2 - 22, "ImmSrc", size=9, color=BLUE)

# ================================================================================
# EXECUTE
# ================================================================================
SA_X, SA_W, SA_H = E_X + 60, 40, 55
SA_Y = rd1_y - SA_H / 2
mux2(SA_X, SA_Y, SA_W, SA_H)
text(SA_X + SA_W + 4, SA_Y - 6, "SrcA", size=10)

SB_X, SB_W, SB_H = E_X + 60, 40, 55
SB_Y = rd2_y - SB_H / 2
mux2(SB_X, SB_Y, SB_W, SB_H)
text(SB_X + SB_W + 4, SB_Y - 6, "SrcB", size=10)

line([(DE_X, rd1_y), (SA_X, SA_Y + SA_H * 0.28)])
line([(DE_X, rd2_y), (SB_X, SB_Y + SB_H * 0.28)])
line([(DE_X, immext_y), (SB_X - 18, immext_y), (SB_X - 18, SB_Y + SB_H * 0.72), (SB_X, SB_Y + SB_H * 0.72)])
line([(DE_X, pc_y), (SA_X - 18, pc_y), (SA_X - 18, SA_Y + SA_H * 0.72), (SA_X, SA_Y + SA_H * 0.72)])

ALU_X2, ALU_W2, ALU_H2 = SA_X + SA_W + 60, 110, 180
ALU_Y2 = rd1_y - ALU_H2 * 0.28
alu_trap(ALU_X2, ALU_Y2, ALU_W2, ALU_H2)
line([(SA_X + SA_W, SA_Y + SA_H * 0.5), (ALU_X2, ALU_Y2 + ALU_H2 * 0.25)])
line([(SB_X + SB_W, SB_Y + SB_H * 0.5), (ALU_X2, ALU_Y2 + ALU_H2 * 0.75)])
ALURES_Y = ALU_Y2 + ALU_H2 * 0.25
ZERO_Y2 = ALU_Y2 + ALU_H2 * 0.75
text(ALU_X2 + ALU_W2 + 6, ALURES_Y + 4, "ALUResultE", size=10)
text(ALU_X2 + ALU_W2 + 6, ZERO_Y2 + 4, "ZeroE", size=10)

aluresult_y = LANE_Y["ALUResult"]
line([(ALU_X2 + ALU_W2, ALURES_Y), (ALU_X2 + ALU_W2 + 30, ALURES_Y), (ALU_X2 + ALU_W2 + 30, aluresult_y), (EM_X, aluresult_y)])

blue([(DE_X, LANE_Y["ALUControl"]), (ALU_X2 + ALU_W2 * 0.5, LANE_Y["ALUControl"]), (ALU_X2 + ALU_W2 * 0.5, ALU_Y2)])
blue([(DE_X, LANE_Y["ALUSrc"]), (SB_X + SB_W * 0.5, LANE_Y["ALUSrc"]), (SB_X + SB_W * 0.5, SB_Y)])
blue([(DE_X, LANE_Y["ALUSrcA"]), (SA_X + SA_W * 0.5, LANE_Y["ALUSrcA"]), (SA_X + SA_W * 0.5, SA_Y)])

# PCTarget adder: PCE + ImmExtE  (below the ALU, same x)
PT_X2, PT_W2, PT_H2 = ALU_X2, 90, 60
PT_Y2 = 480
add_trap(PT_X2, PT_Y2, PT_W2, PT_H2)
line([(DE_X, pc_y), (PT_X2 - 34, pc_y), (PT_X2 - 34, PT_Y2 + PT_H2 * 0.25), (PT_X2, PT_Y2 + PT_H2 * 0.25)])
line([(DE_X, immext_y), (PT_X2 - 20, immext_y), (PT_X2 - 20, PT_Y2 + PT_H2 * 0.75), (PT_X2, PT_Y2 + PT_H2 * 0.75)])
text(PT_X2 + PT_W2 + 6, PT_Y2 + PT_H2 / 2 + 4, "PCTargetE", size=10)

# branch-taken / PCNextSelE resolve logic — sits to the right of PCTarget, well
# inside the Execute column (checked against EM_X below)
BR_W2, BR_H2 = 170, 110
BR_X2 = min(PT_X2 + PT_W2 + 60, EM_X - BR_W2 - 20)
BR_Y2 = 470
rect(BR_X2, BR_Y2, BR_W2, BR_H2, lw=1.6, dash=[4, 3])
text(BR_X2 + BR_W2 / 2, BR_Y2 + 20, "branch-taken +", size=11, bold=True, anchor="c")
text(BR_X2 + BR_W2 / 2, BR_Y2 + 38, "PCNextSelE resolve", size=11, bold=True, anchor="c")
text(BR_X2 + 8, BR_Y2 + 62, "funct3E, ZeroE, ALUResultE[0],", size=9, italic=True)
text(BR_X2 + 8, BR_Y2 + 78, "BranchE, PCSrcE", size=9, italic=True)

# route funct3E / BranchE / PCSrcE down a clear "highway" just right of the D/E
# bar, well left of the SrcA/SrcB muxes, so nothing crosses the ALU
line([(DE_X, funct3_y), (DE_X + 12, funct3_y), (DE_X + 12, BR_Y2 - 30), (BR_X2 + 30, BR_Y2 - 30), (BR_X2 + 30, BR_Y2)])
blue([(DE_X, LANE_Y["Branch"]), (DE_X + 18, LANE_Y["Branch"]), (DE_X + 18, BR_Y2 - 20), (BR_X2 + 55, BR_Y2 - 20), (BR_X2 + 55, BR_Y2)])
blue([(DE_X, LANE_Y["PCSrc"]), (DE_X + 24, LANE_Y["PCSrc"]), (DE_X + 24, BR_Y2 - 10), (BR_X2 + 80, BR_Y2 - 10), (BR_X2 + 80, BR_Y2)])
# Zero / ALUResult[0] come straight down from the ALU's own output, right of it
line([(ALU_X2 + ALU_W2, ZERO_Y2), (ALU_X2 + ALU_W2 + 15, ZERO_Y2), (ALU_X2 + ALU_W2 + 15, BR_Y2 - 40), (BR_X2 + 15, BR_Y2 - 40), (BR_X2 + 15, BR_Y2)])
text(ALU_X2 + ALU_W2 + 18, ZERO_Y2 - 14, "Zero, ALUResult[0]", size=8, italic=True)

text(BR_X2 + BR_W2 / 2, BR_Y2 + BR_H2 + 20, "PCNextSelE", size=11, bold=True, color=RED, anchor="c")

# ================================================================================
# MEMORY
# ================================================================================
DM_X2, DM_W2, DM_H2 = M_X + 60, 190, 190
DM_Y2 = aluresult_y - 40
rect(DM_X2, DM_Y2, DM_W2, DM_H2, lw=1.8)
text(DM_X2 + DM_W2 / 2, DM_Y2 + 26, "Data", size=13, bold=True, anchor="c")
text(DM_X2 + DM_W2 / 2, DM_Y2 + 46, "Memory", size=13, bold=True, anchor="c")
text(DM_X2 + 8, DM_Y2 + 70, "A", size=10)
text(DM_X2 + 8, DM_Y2 + DM_H2 - 16, "WD", size=10)
text(DM_X2 + DM_W2 - 10, DM_Y2 + 70, "RD", size=10, anchor="r")
text(DM_X2 + 8, DM_Y2 - 14, "WE", size=10)
clk_tri_down(DM_X2 + 40, DM_Y2)
text(DM_X2 + 40, DM_Y2 - 26, "CLK", size=9, anchor="c")

line([(EM_X, aluresult_y), (DM_X2, DM_Y2 + 70)])
line([(EM_X, rd2_y), (DM_X2 - 15, rd2_y), (DM_X2 - 15, DM_Y2 + DM_H2 - 16), (DM_X2, DM_Y2 + DM_H2 - 16)])
text(EM_X + 6, rd2_y - 6, "WriteDataM", size=8, italic=True)

readdata_y = LANE_Y["ReadData"]
line([(DM_X2 + DM_W2, DM_Y2 + 70), (DM_X2 + DM_W2 + 20, DM_Y2 + 70), (DM_X2 + DM_W2 + 20, readdata_y), (MW_X, readdata_y)])
text(DM_X2 + DM_W2 + 4, DM_Y2 + 62, "ReadDataM", size=9)

blue([(EM_X, LANE_Y["MemWrite"]), (DM_X2 + 40, LANE_Y["MemWrite"]), (DM_X2 + 40, DM_Y2 - 14)])

# ================================================================================
# WRITEBACK
# ================================================================================
RM_X2, RM_W2, RM_H2 = Wb_X + 60, 44, 190
RM_Y2 = aluresult_y - RM_H2 * 0.2
mux4(RM_X2, RM_Y2, RM_W2, RM_H2)
text(RM_X2 - 4, RM_Y2 - 10, "Result", size=11)

line([(MW_X, aluresult_y), (RM_X2, RM_Y2 + RM_H2 * 0.14)])
line([(MW_X, readdata_y), (RM_X2, RM_Y2 + RM_H2 * 0.38)])
line([(MW_X, immext_y), (RM_X2 - 24, immext_y), (RM_X2 - 24, RM_Y2 + RM_H2 * 0.62), (RM_X2, RM_Y2 + RM_H2 * 0.62)])
line([(MW_X, pcp4_y), (RM_X2 - 34, pcp4_y), (RM_X2 - 34, RM_Y2 + RM_H2 * 0.86), (RM_X2, RM_Y2 + RM_H2 * 0.86)])

blue([(MW_X, LANE_Y["ResultSrc"]), (RM_X2 + RM_W2 * 0.5, LANE_Y["ResultSrc"]), (RM_X2 + RM_W2 * 0.5, RM_Y2)])

text(RM_X2 + RM_W2 + 10, RM_Y2 + RM_H2 * 0.5 + 4, "ResultW", size=11, bold=True)
text(Wb_X + 10, rd_y - 6, "RdW", size=9, italic=True)
text(Wb_X + 10, LANE_Y["RegWrite"] - 6, "RegWriteW", size=9, italic=True, color=BLUE)

# ================================================================================
# LONG COMBINATIONAL FEEDBACK PATHS (not pipelined — drawn distinctly in red)
# ================================================================================
FB1_Y = LANE_BOTTOM + 70
line([(BR_X2 + BR_W2 / 2, BR_Y2 + BR_H2 + 26), (BR_X2 + BR_W2 / 2, FB1_Y), (PT_X2 + PT_W2 + 10, FB1_Y)],
     color=RED, width=1.8)
line([(ALU_X2 + ALU_W2, ALURES_Y), (ALU_X2 + ALU_W2 + 45, ALURES_Y), (ALU_X2 + ALU_W2 + 45, FB1_Y + 12)],
     color=RED, width=1.4, dash=[5, 3])
line([(PT_X2 + PT_W2, PT_Y2 + PT_H2 * 0.5), (PT_X2 + PT_W2 + 20, PT_Y2 + PT_H2 * 0.5), (PT_X2 + PT_W2 + 20, FB1_Y + 6)],
     color=RED, width=1.4, dash=[5, 3])
line([(PT_X2 + PT_W2 + 10, FB1_Y), (PCM_X + PCM_W * 0.5, FB1_Y), (PCM_X + PCM_W * 0.5, PCM_Y + PCM_H)],
     color=RED, width=1.8)
text((PT_X2 + PCM_X) / 2, FB1_Y + 16,
     "PCNextSelE + PCTargetE / ALUResultE  ->  Fetch's PCNext mux   (combinational, not pipelined — spec §8 / Note 5)",
     size=10, italic=True, color=RED, anchor="c")

FB2_Y = FB1_Y + 40
line([(RM_X2 + RM_W2, RM_Y2 + RM_H2 * 0.5), (RM_X2 + RM_W2 + 30, RM_Y2 + RM_H2 * 0.5), (RM_X2 + RM_W2 + 30, FB2_Y)])
line([(Wb_X + 20, rd_y), (Wb_X + 20, FB2_Y + 15)])
line([(Wb_X + 40, LANE_Y["RegWrite"]), (Wb_X + 40, FB2_Y + 22)])
line([(RM_X2 + RM_W2 + 30, FB2_Y), (Wb_X + 40, FB2_Y + 22), (RF_X2 + 30, FB2_Y + 22), (RF_X2 + 30, RF_Y2 + RF_H2)])
line([(Wb_X + 20, FB2_Y + 15), (RF_X2 + 15, FB2_Y + 15), (RF_X2 + 15, RF_Y2 + RF_H2)])
text((RF_X2 + RM_X2) / 2, FB2_Y + 36,
     "ResultW / RdW / RegWriteW  ->  regfile write port (A3, WD3, WE3), negedge clk — Decode-stage read, Writeback-stage write, same cycle",
     size=10, italic=True, anchor="c")

# ================================================================================
# TITLE
# ================================================================================
text(END_X / 2, H - 20,
     "rv32_top_pipelined — RV32I 5-Stage Pipelined Datapath (F / D / E / M / W, no forwarding or hazard logic)",
     size=15, bold=True, anchor="c")

flush_labels()
surf.finish()
print("done", OUT)
