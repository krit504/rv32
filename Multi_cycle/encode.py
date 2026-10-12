def r_type(funct7, rs2, rs1, funct3, rd, opcode=0b0110011):
    return (funct7<<25)|(rs2<<20)|(rs1<<15)|(funct3<<12)|(rd<<7)|opcode

def i_type(imm, rs1, funct3, rd, opcode=0b0010011):
    imm = imm & 0xFFF
    return (imm<<20)|(rs1<<15)|(funct3<<12)|(rd<<7)|opcode

def i_type_load(imm, rs1, funct3, rd, opcode=0b0000011):
    return i_type(imm, rs1, funct3, rd, opcode)

def s_type(imm, rs2, rs1, funct3, opcode=0b0100011):
    imm &= 0xFFF
    imm11_5 = (imm>>5)&0x7F
    imm4_0 = imm&0x1F
    return (imm11_5<<25)|(rs2<<20)|(rs1<<15)|(funct3<<12)|(imm4_0<<7)|opcode

def b_type(imm, rs2, rs1, funct3, opcode=0b1100011):
    imm &= 0x1FFF
    imm12 = (imm>>12)&1
    imm11 = (imm>>11)&1
    imm10_5 = (imm>>5)&0x3F
    imm4_1 = (imm>>1)&0xF
    return (imm12<<31)|(imm10_5<<25)|(rs2<<20)|(rs1<<15)|(funct3<<12)|(imm4_1<<8)|(imm11<<7)|opcode

def u_type(imm20, rd, opcode):
    return ((imm20&0xFFFFF)<<12)|(rd<<7)|opcode

def addi(rd,rs1,imm): return i_type(imm,rs1,0b000,rd)
def add(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b000,rd)
def sub(rd,rs1,rs2): return r_type(0b0100000,rs2,rs1,0b000,rd)
def AND(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b111,rd)
def OR(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b110,rd)
def XOR(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b100,rd)
def slt(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b010,rd)
def sltu(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b011,rd)
def sll(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b001,rd)
def srl(rd,rs1,rs2): return r_type(0b0000000,rs2,rs1,0b101,rd)
def sra(rd,rs1,rs2): return r_type(0b0100000,rs2,rs1,0b101,rd)
def lw(rd,imm,rs1): return i_type_load(imm,rs1,0b010,rd,0b0000011)
def sw(rs2,imm,rs1): return s_type(imm,rs2,rs1,0b010,0b0100011)
def beq(rs1,rs2,imm): return b_type(imm,rs2,rs1,0b000,0b1100011)
def lui(rd,imm20): return u_type(imm20,rd,0b0110111)
def auipc(rd,imm20): return u_type(imm20,rd,0b0010111)

prog = [
    addi(1, 0, 5),          # 0  x1=5
    addi(2, 0, 10),         # 1  x2=10
    addi(3, 0, -3 & 0xFFF), # 2  x3=-3
    lui(4, 0x12345),        # 3  x4=0x12345000
    auipc(5, 0x1),          # 4  x5=PC+0x1000
    add(6, 1, 2),           # 5  x6=x1+x2
    sub(7, 2, 1),           # 6  x7=x2-x1
    AND(8, 1, 2),           # 7  x8=x1&x2
    OR(9, 1, 2),            # 8  x9=x1|x2
    XOR(10, 1, 2),          # 9  x10=x1^x2
    slt(11, 3, 1),          # 10 x11=(x3<x1 signed)
    sltu(12, 3, 1),         # 11 x12=(x3<x1 unsigned)
    sll(13, 1, 2),          # 12 x13=x1<<(x2&0x1F)
    srl(14, 3, 1),          # 13 x14=x3>>(x1&0x1F) logical
    sra(15, 3, 1),          # 14 x15=x3>>>(x1&0x1F) arithmetic
    addi(16, 1, 100),       # 15 x16=x1+100
    beq(1, 3, 40),          # 16 not taken (x1 != x3)
    sw(6, 0, 0),            # 17 mem[0]=x6
    lw(17, 0, 0),           # 18 x17=mem[0]
    addi(19, 0, 42),        # 19 x19=42  (writer, 3-gap test)
    addi(20, 0, 1),         # 20 filler
    addi(21, 0, 2),         # 21 filler
    add(22, 19, 0),         # 22 x22=x19+x0  (reader, gap=3, same-cycle W/D falling-edge case)
    addi(0, 0, 0),          # 23 drain
    addi(0, 0, 0),          # 24 drain
    addi(0, 0, 0),          # 25 drain
    addi(0, 0, 0),          # 26 drain
]

with open('/home/kritin/Scratch/personal/sv_practice/PROJECTS/RV32I/Multi_cycle/program.hex', 'w') as f:
    for w in prog:
        f.write(f"{w & 0xFFFFFFFF:08x}\n")

def s32(x):
    x &= 0xFFFFFFFF
    return x - (1<<32) if x & 0x80000000 else x

def u32(x):
    return x & 0xFFFFFFFF

x1 = 5
x2 = 10
x3 = u32(-3)
x4 = 0x12345000
PC4 = 4*4
x5 = u32(PC4 + 0x1000)
x6 = u32(x1 + x2)
x7 = u32(x2 - x1)
x8 = u32(x1 & x2)
x9 = u32(x1 | x2)
x10 = u32(x1 ^ x2)
x11 = 1 if s32(x3) < s32(x1) else 0
x12 = 1 if u32(x3) < u32(x1) else 0
shamt2 = x2 & 0x1F
x13 = u32(x1 << shamt2)
shamt1 = x1 & 0x1F
x14 = u32(x3) >> shamt1
x15 = u32(s32(x3) >> shamt1)
x16 = u32(x1 + 100)
mem0 = x6
x17 = mem0
x19 = 42
x20 = 1
x21 = 2
x22 = u32(x19 + 0)

expected = {
    1:x1,2:x2,3:x3,4:x4,5:x5,6:x6,7:x7,8:x8,9:x9,10:x10,
    11:x11,12:x12,13:x13,14:x14,15:x15,16:x16,17:x17,
    19:x19,20:x20,21:x21,22:x22
}
for r,v in expected.items():
    print(f"x{r} = 0x{v:08x} ({s32(v)})")

print()
print("N_INSTR =", len(prog))
