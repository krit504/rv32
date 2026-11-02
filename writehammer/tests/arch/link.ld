/* link.ld for the architectural tests: same layout for the Spike and RTL builds. Linked at
 * 0x80000000 (Spike's RAM base); the core's reset PC is set to it with RESET_PC and its memories
 * ignore the high address bits, so the image sits at word 0 of each 256 KiB memory. */
OUTPUT_ARCH(riscv)
ENTRY(rvtest_entry_point)
SECTIONS
{
    . = 0x80000000;
    .text.init : { *(.text.init) }
    . = ALIGN(0x1000);
    .text : { *(.text) }
    . = ALIGN(0x1000);
    .data : { *(.data) }
    .tohost : ALIGN(0x40) { *(.tohost) }
    .bss : { *(.bss) }
    _end = .;
}
