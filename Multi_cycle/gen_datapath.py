import cairo
import math

W, H = 1500, 950
BLACK = (0, 0, 0)
BLUE = (0.10, 0.45, 0.85)

surf = cairo.SVGSurface(
    "/tmp/claude-1000/-home-kritin-Scratch-personal-sv-practice/ea23d7ca-c808-4043-b3b6-ee06e427b1a5/scratchpad/rv32i_datapath.svg",
    W, H,
)
ctx = cairo.Context(surf)
ctx.set_source_rgb(1, 1, 1)
ctx.rectangle(0, 0, W, H)
ctx.fill()

LABELS = []  # deferred: drawn last, on top of every line/shape, with a white halo


def set_color(c):
    ctx.set_source_rgb(*c)


def line(pts, color=BLACK, width=1.6):
    set_color(color)
    ctx.set_line_width(width)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.stroke()


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


def rect(x, y, w, h, color=BLACK, lw=1.8):
    set_color(color)
    ctx.set_line_width(lw)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()


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
    text(x + w * 0.55, y + h * 0.5 + 5, "ALU", size=16, bold=True, anchor="c")


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
    text(x + w * 0.55, y + h * 0.5 + 6, "+", size=20, bold=True, anchor="c")


def blue(pts):
    line(pts, color=BLUE, width=1.6)


# ============================================================= CONTROL UNIT
CU_X, CU_Y, CU_W, CU_H = 470, 55, 150, 230
rect(CU_X, CU_Y, CU_W, CU_H, lw=2.2)
text(CU_X + CU_W / 2, CU_Y + 20, "Control", size=15, bold=True, anchor="c")
text(CU_X + CU_W / 2, CU_Y + 40, "Unit", size=15, bold=True, anchor="c")

# ============================================================= PCNext mux
PCM_X, PCM_Y, PCM_W, PCM_H = 55, 255, 42, 95
mux4_style = None
set_color(BLACK)
ctx.set_line_width(1.8)
ctx.move_to(PCM_X, PCM_Y)
ctx.line_to(PCM_X, PCM_Y + PCM_H)
ctx.line_to(PCM_X + PCM_W, PCM_Y + PCM_H * 0.78)
ctx.line_to(PCM_X + PCM_W, PCM_Y + PCM_H * 0.22)
ctx.close_path()
ctx.stroke()
text(PCM_X + 5, PCM_Y + PCM_H * 0.22 + 12, "0", size=10)
text(PCM_X + 5, PCM_Y + PCM_H * 0.5 + 12, "1", size=10)
text(PCM_X + 5, PCM_Y + PCM_H - 6, "2", size=10)
text(PCM_X - 30, PCM_Y - 10, "PCNext", size=11)

# ============================================================= PC register
PC_X, PC_Y, PC_W, PC_H = 160, 260, 44, 60
rect(PC_X, PC_Y, PC_W, PC_H)
text(PC_X + PC_W / 2, PC_Y + PC_H / 2 + 4, "PC", size=13, bold=True, anchor="c")
clk_tri_up(PC_X + PC_W / 2, PC_Y + PC_H)
text(PC_X + PC_W / 2, PC_Y + PC_H + 20, "CLK", size=10, anchor="c")

# ============================================================= Instruction Memory
IM_X, IM_Y, IM_W, IM_H = 240, 220, 150, 220
rect(IM_X, IM_Y, IM_W, IM_H)
text(IM_X + IM_W / 2, IM_Y + IM_H / 2 - 4, "Instruction", size=14, bold=True, anchor="c")
text(IM_X + IM_W / 2, IM_Y + IM_H / 2 + 16, "Memory", size=14, bold=True, anchor="c")
text(IM_X + 8, IM_Y + 24, "A", size=12)
text(IM_X + IM_W - 12, IM_Y + IM_H - 20, "RD", size=12, anchor="r")

# ============================================================= Register File
RF_X, RF_Y, RF_W, RF_H = 470, 300, 190, 200
rect(RF_X, RF_Y, RF_W, RF_H)
text(RF_X + RF_W / 2, RF_Y + RF_H / 2 - 4, "Register", size=14, bold=True, anchor="c")
text(RF_X + RF_W / 2, RF_Y + RF_H / 2 + 16, "File", size=14, bold=True, anchor="c")
text(RF_X + 8, RF_Y + 25, "A1", size=11)
text(RF_X + 8, RF_Y + 50, "A2", size=11)
text(RF_X + 8, RF_Y + 75, "A3", size=11)
text(RF_X + 8, RF_Y + 100, "WD3", size=11)
text(RF_X + RF_W - 12, RF_Y + 25, "RD1", size=11, anchor="r")
text(RF_X + RF_W - 12, RF_Y + 90, "RD2", size=11, anchor="r")
text(RF_X + 8, RF_Y + RF_H - 10, "WE3", size=11)
clk_tri_up(RF_X + 30, RF_Y + RF_H)
text(RF_X + 30, RF_Y + RF_H + 20, "CLK", size=10, anchor="c")

# ============================================================= SrcA / SrcB muxes
MA_X, MA_Y, MA_W, MA_H = 715, 300, 40, 60
mux2(MA_X, MA_Y, MA_W, MA_H)
text(MA_X + MA_W + 4, MA_Y - 8, "SrcA", size=11)

MB_X, MB_Y, MB_W, MB_H = 715, 430, 40, 60
mux2(MB_X, MB_Y, MB_W, MB_H)
text(MB_X + MB_W + 4, MB_Y - 8, "SrcB", size=11)

# ============================================================= ALU
ALU_X, ALU_Y, ALU_W, ALU_H = 800, 290, 120, 210
alu_trap(ALU_X, ALU_Y, ALU_W, ALU_H)
text(ALU_X - 30, ALU_Y + ALU_H * 0.25 - 6, "SrcA", size=11)
text(ALU_X - 30, ALU_Y + ALU_H * 0.75 - 6, "SrcB", size=11)
text(ALU_X + ALU_W + 8, ALU_Y + ALU_H * 0.25 + 4, "ALUResult", size=11)
text(ALU_X + ALU_W + 8, ALU_Y + ALU_H * 0.75 + 4, "Zero", size=11)

# ============================================================= Data Memory
DM_X, DM_Y, DM_W, DM_H = 1080, 260, 160, 220
rect(DM_X, DM_Y, DM_W, DM_H)
text(DM_X + DM_W / 2, DM_Y + DM_H / 2 - 4, "Data", size=14, bold=True, anchor="c")
text(DM_X + DM_W / 2, DM_Y + DM_H / 2 + 16, "Memory", size=14, bold=True, anchor="c")
text(DM_X + 8, DM_Y + 24, "A", size=12)
text(DM_X + 8, DM_Y + DM_H - 14, "WD", size=12)
text(DM_X + DM_W - 12, DM_Y + 24, "RD", size=12, anchor="r")
text(DM_X + 34, DM_Y - 4, "WE", size=11)
clk_tri_down(DM_X + 90, DM_Y)
text(DM_X + 90, DM_Y - 14, "CLK", size=10, anchor="c")

# ============================================================= Result mux (4:1)
RM_X, RM_Y, RM_W, RM_H = 1320, 260, 46, 220
mux4(RM_X, RM_Y, RM_W, RM_H)
text(RM_X - 4, RM_Y - 10, "Result", size=11)

# ============================================================= Immediate Generator
EX_X, EX_Y, EX_W, EX_H = 470, 590, 190, 60
skew = 16
set_color(BLACK)
ctx.set_line_width(1.8)
ctx.move_to(EX_X + skew, EX_Y)
ctx.line_to(EX_X + EX_W, EX_Y)
ctx.line_to(EX_X + EX_W - skew, EX_Y + EX_H)
ctx.line_to(EX_X, EX_Y + EX_H)
ctx.close_path()
ctx.stroke()
text(EX_X + EX_W / 2, EX_Y + EX_H / 2 + 5, "Immediate Generator", size=13, bold=True, anchor="c")

# ============================================================= PCTarget adder
PT_X, PT_Y, PT_W, PT_H = 800, 585, 90, 70
add_trap(PT_X, PT_Y, PT_W, PT_H)
text(PT_X + PT_W + 8, PT_Y + PT_H / 2 + 4, "PCTarget", size=11)

# ============================================================= PCPlus4 adder
P4_X, P4_Y, P4_W, P4_H = 240, 730, 90, 70
add_trap(P4_X, P4_Y, P4_W, P4_H)
text(P4_X + P4_W + 8, P4_Y + P4_H / 2 + 4, "PCPlus4", size=11)
text(P4_X - 22, P4_Y + P4_H * 0.75 + 4, "4", size=11)

# ================================================================================
# WIRES - datapath (black)
# ================================================================================

line([(PCM_X + PCM_W, PCM_Y + PCM_H * 0.5), (PC_X, PC_Y + PC_H / 2)])
line([(PC_X + PC_W, PC_Y + PC_H / 2), (IM_X, PC_Y + PC_H / 2)])
text(IM_X - 26, PC_Y + PC_H / 2 - 6, "PC", size=11)

PC_BUS_X = PC_X + PC_W / 2
line([(PC_BUS_X, PC_Y + PC_H), (PC_BUS_X, 775), (P4_X, 775)])
line([(PC_BUS_X, 775), (PC_BUS_X + 260, 775), (PC_BUS_X + 260, PT_Y + PT_H * 0.75), (PT_X, PT_Y + PT_H * 0.75)])
line([(PC_BUS_X, 775), (PC_BUS_X, 860), (MA_X - 90, 860), (MA_X - 90, MA_Y + MA_H * 0.72), (MA_X, MA_Y + MA_H * 0.72)])

INSTR_X = IM_X + IM_W
INSTR_MIDY = IM_Y + IM_H - 20
bus_x = INSTR_X + 20
line([(INSTR_X, INSTR_MIDY), (bus_x, INSTR_MIDY)])
text(INSTR_X + 24, INSTR_MIDY + 4, "Instr", size=11)

line([(bus_x, INSTR_MIDY), (bus_x, CU_Y + 86), (CU_X, CU_Y + 86)])
line([(bus_x + 6, INSTR_MIDY), (bus_x + 6, INSTR_MIDY), (bus_x + 6, CU_Y + 111), (CU_X, CU_Y + 111)])
line([(bus_x + 12, INSTR_MIDY), (bus_x + 12, CU_Y + 136), (CU_X, CU_Y + 136)])
line([(bus_x, INSTR_MIDY), (bus_x, RF_Y + 25), (RF_X, RF_Y + 25)])
line([(bus_x + 6, INSTR_MIDY), (bus_x + 6, RF_Y + 50), (RF_X, RF_Y + 50)])
line([(bus_x + 12, INSTR_MIDY), (bus_x + 12, RF_Y + 75), (RF_X, RF_Y + 75)])
line([(bus_x, INSTR_MIDY), (bus_x, EX_Y + 15), (EX_X, EX_Y + 15)])

text(CU_X - 4, CU_Y + 82, "op", size=11)
text(CU_X - 30, CU_Y + 78, "6:0", size=9)
text(CU_X - 4, CU_Y + 107, "funct3", size=11)
text(CU_X - 38, CU_Y + 103, "14:12", size=9)
text(CU_X - 4, CU_Y + 132, "funct7_5", size=11)
text(CU_X - 24, CU_Y + 128, "30", size=9)
text(CU_X - 4, CU_Y + 172, "Zero", size=11)
text(CU_X - 4, CU_Y + 200, "ALUResult0", size=11)

text(RF_X - 30, RF_Y + 21, "19:15", size=9)
text(RF_X - 30, RF_Y + 46, "24:20", size=9)
text(RF_X - 24, RF_Y + 71, "11:7", size=9)
text(EX_X - 24, EX_Y + 11, "31:7", size=9)

line([(RF_X + RF_W, RF_Y + 25), (MA_X, MA_Y + MA_H * 0.28)])
line([(RF_X + RF_W, RF_Y + 90), (MB_X, MB_Y + MB_H * 0.28)])
line([(RF_X + RF_W, RF_Y + 90), (RF_X + RF_W + 12, RF_Y + 90), (RF_X + RF_W + 12, DM_Y + DM_H - 14), (DM_X, DM_Y + DM_H - 14)])

line([(MA_X + MA_W, MA_Y + MA_H * 0.5), (ALU_X, ALU_Y + ALU_H * 0.25)])
line([(MB_X + MB_W, MB_Y + MB_H * 0.5), (ALU_X, ALU_Y + ALU_H * 0.75)])

IMMX = EX_X + EX_W + 40
line([(EX_X + EX_W, EX_Y + EX_H / 2), (IMMX, EX_Y + EX_H / 2)])
line([(IMMX, EX_Y + EX_H / 2), (IMMX, MB_Y + MB_H * 0.72), (MB_X, MB_Y + MB_H * 0.72)])
line([(IMMX, EX_Y + EX_H / 2), (IMMX, PT_Y + PT_H * 0.25), (PT_X, PT_Y + PT_H * 0.25)])
line([(IMMX, EX_Y + EX_H / 2), (IMMX, 890), (RM_X - 40, 890), (RM_X - 40, RM_Y + RM_H * 0.62), (RM_X, RM_Y + RM_H * 0.62)])
text(EX_X + EX_W + 6, EX_Y - 6, "ImmExt", size=11)

line([(PT_X + PT_W, PT_Y + PT_H * 0.5), (PT_X + PT_W + 30, PT_Y + PT_H * 0.5), (PT_X + PT_W + 30, 790),
      (10, 790), (10, PCM_Y + PCM_H * 0.5), (PCM_X, PCM_Y + PCM_H * 0.5)])

line([(P4_X + P4_W, P4_Y + P4_H * 0.5), (P4_X + P4_W + 20, P4_Y + P4_H * 0.5), (P4_X + P4_W + 20, 810),
      (20, 810), (20, PCM_Y + PCM_H * 0.22 + 6), (PCM_X, PCM_Y + PCM_H * 0.22 + 6)])

line([(P4_X + P4_W + 20, P4_Y + P4_H * 0.5), (P4_X + P4_W + 20, 905), (RM_X - 30, 905),
      (RM_X - 30, RM_Y + RM_H * 0.86), (RM_X, RM_Y + RM_H * 0.86)])
text(600, 900, "PCPlus4", size=10, italic=True)

ALU_RES_Y = ALU_Y + ALU_H * 0.25
line([(ALU_X + ALU_W, ALU_RES_Y), (DM_X, DM_Y + 24)])
line([(ALU_X + ALU_W, ALU_RES_Y), (ALU_X + ALU_W + 30, ALU_RES_Y)])
line([(ALU_X + ALU_W + 30, ALU_RES_Y), (ALU_X + ALU_W + 30, RM_Y + RM_H * 0.14), (RM_X - 130, RM_Y + RM_H * 0.14),
      (RM_X - 130, RM_Y + RM_H * 0.14), (RM_X, RM_Y + RM_H * 0.14)])
text(ALU_X + ALU_W + 34, ALU_RES_Y - 8, "jalr: [31:1],0", size=8, italic=True)
line([(ALU_X + ALU_W + 30, ALU_RES_Y), (ALU_X + ALU_W + 30, 845), (30, 845),
      (30, PCM_Y + PCM_H - 6), (PCM_X, PCM_Y + PCM_H - 6)])

line([(DM_X + DM_W, DM_Y + 24), (RM_X, RM_Y + RM_H * 0.38)])
text(DM_X + DM_W + 8, DM_Y + 18, "ReadData", size=11)

RES_MIDY = RM_Y + RM_H * 0.5
line([(RM_X + RM_W, RES_MIDY), (RM_X + RM_W + 20, RES_MIDY), (RM_X + RM_W + 20, 920),
      (400, 920), (400, RF_Y + 100), (RF_X, RF_Y + 100)])
text(900, 915, "Result", size=11)

# ================================================================================
# WIRES - control (blue)
# ================================================================================
cu_out_y = {
    "PCSrc": CU_Y + 20,
    "ResultSrc": CU_Y + 40,
    "MemWrite": CU_Y + 60,
    "ALUControl": CU_Y + 80,
    "ALUSrc": CU_Y + 100,
    "ALUSrcA": CU_Y + 118,
    "ImmSrc": CU_Y + 136,
    "RegWrite": CU_Y + 154,
}
cu_out_disp = {
    "PCSrc": "PCSrc[1:0]",
    "ResultSrc": "ResultSrc[1:0]",
    "MemWrite": "MemWrite",
    "ALUControl": "ALUControl[3:0]",
    "ALUSrc": "ALUSrc",
    "ALUSrcA": "ALUSrcA",
    "ImmSrc": "ImmSrc[2:0]",
    "RegWrite": "RegWrite",
}
for name, dy in cu_out_y.items():
    text(CU_X + CU_W + 6, dy - 6, cu_out_disp[name], size=10, color=BLUE)

blue([(CU_X + CU_W, cu_out_y["PCSrc"]), (CU_X + CU_W + 40, cu_out_y["PCSrc"]), (CU_X + CU_W + 40, 20),
      (PCM_X - 20, 20), (PCM_X - 20, PCM_Y + PCM_H * 0.5 + 20), (PCM_X, PCM_Y + PCM_H * 0.5 + 20)])

blue([(CU_X + CU_W, cu_out_y["ResultSrc"]), (CU_X + CU_W + 60, cu_out_y["ResultSrc"]), (CU_X + CU_W + 60, 32),
      (RM_X + RM_W / 2, 32), (RM_X + RM_W / 2, RM_Y)])

blue([(CU_X + CU_W, cu_out_y["MemWrite"]), (CU_X + CU_W + 80, cu_out_y["MemWrite"]), (CU_X + CU_W + 80, 44),
      (DM_X + 30, 44), (DM_X + 30, DM_Y)])

blue([(CU_X + CU_W, cu_out_y["ALUControl"]), (ALU_X + ALU_W * 0.55, cu_out_y["ALUControl"]),
      (ALU_X + ALU_W * 0.55, ALU_Y)])

blue([(CU_X + CU_W, cu_out_y["ALUSrc"]), (MB_X + MB_W * 0.5, cu_out_y["ALUSrc"]), (MB_X + MB_W * 0.5, MB_Y)])

blue([(CU_X + CU_W, cu_out_y["ALUSrcA"]), (MA_X + MA_W * 0.5, cu_out_y["ALUSrcA"]), (MA_X + MA_W * 0.5, MA_Y)])

blue([(CU_X + CU_W, cu_out_y["ImmSrc"]), (CU_X + CU_W + 20, cu_out_y["ImmSrc"]), (CU_X + CU_W + 20, EX_Y - 20),
      (EX_X + 40, EX_Y - 20), (EX_X + 40, EX_Y)])

blue([(CU_X + CU_W, cu_out_y["RegWrite"]), (RF_X + RF_W - 20, cu_out_y["RegWrite"]), (RF_X + RF_W - 20, RF_Y - 10),
      (RF_X + 30, RF_Y - 10), (RF_X + 30, RF_Y)])

# ALU.Zero -> CU.Zero  (feedback loop)
ZERO_Y = ALU_Y + ALU_H * 0.75
line([(ALU_X + ALU_W, ZERO_Y), (ALU_X + ALU_W + 15, ZERO_Y), (ALU_X + ALU_W + 15, 230),
      (CU_X + CU_W + 20, 230), (CU_X + CU_W + 20, CU_Y + 172), (CU_X + CU_W, CU_Y + 172)])

# ALU.ALUResult[0] -> CU.ALUResult0 (feedback, new signal)
line([(ALU_X + ALU_W + 30, ALU_RES_Y), (ALU_X + ALU_W + 30, 245), (CU_X + CU_W + 35, 245),
      (CU_X + CU_W + 35, CU_Y + 200), (CU_X + CU_W, CU_Y + 200)])

# ============================================================= title
text(W / 2, H - 12, "rv32_top — RV32I Single-Cycle Datapath (base ISA, all instruction classes)", size=15, bold=True, anchor="c")

flush_labels()
surf.finish()
print("done")
