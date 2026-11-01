"""toolchain_mutants.py: T1.4 mutants of the image-loading path (protected; add only).

Same tuple format as core_mutants.py (file names relative to rtl/).
"""

MUTANTS = [
    ("T1_dmem_ignores_image", "dmem.sv",
     "    if (INIT_FILE != \"\") $readmemh(INIT_FILE, mem);   // initialized .data / .rodata of a linked image",
     "    ;",
     "caches-off data memory never loads the initialized .data / .rodata"),
    ("T2_data_backing_mem_ignores_image", "backing_mem.sv",
     "    if (INIT_FILE != \"\") $readmemh(INIT_FILE, mem);",
     "    if (INIT_FILE != \"\" && DEPTH == 256) $readmemh(INIT_FILE, mem);",
     "256 KiB backing memories (data and instruction) never load the image"),
    ("T3_imem_word_order", "imem.sv",
     "    RD=mem[A[$clog2(DEPTH)+1:2]];",
     "    RD=mem[{A[$clog2(DEPTH)+1:3], ~A[2]}];",
     "adjacent instruction words are swapped"),
]
