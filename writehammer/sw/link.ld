/* link.ld: memory map for the bare-metal RV32I flow (T1.4).
 *
 * One 256 KiB address space, 0x0000_0000 to 0x0003_FFFF, used by both the instruction memory and
 * the data memory (each holds the whole linked image; see spec T2.1/T2.5). Code and data regions
 * are disjoint: text and read-only data come first, then .data, .bss and the stack on separate
 * 4 KiB pages, so no cache line holds both code and data and self-modifying code is never needed.
 * The stack grows down from the top of memory. MMIO (0xF000_0000) is outside this space.
 */
OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x00000000, LENGTH = 256K
}

SECTIONS
{
    .text : {
        KEEP(*(.text.init))
        *(.text .text.*)
    } > RAM

    .rodata : ALIGN(16) {
        *(.rodata .rodata.* .srodata .srodata.*)
    } > RAM

    /* data region starts on a fresh 4 KiB page, never sharing a page (or cache line) with code */
    .data : ALIGN(4096) {
        __data_start = .;
        *(.data .data.* .sdata .sdata.*)
        __data_end = .;
    } > RAM

    .bss (NOLOAD) : ALIGN(16) {
        __bss_start = .;
        *(.bss .bss.* .sbss .sbss.* COMMON)
        . = ALIGN(16);
        __bss_end = .;
    } > RAM

    /* stack: top 16 KiB of memory, own page range */
    __stack_top = ORIGIN(RAM) + LENGTH(RAM) - 16;
    __stack_limit = ORIGIN(RAM) + LENGTH(RAM) - 16K;

    ASSERT(__bss_end <= __stack_limit, "image overlaps the stack")

    /DISCARD/ : { *(.comment .note* .eh_frame*) }   /* .riscv.attributes is kept: build.py reads the ELF architecture from it */
}
