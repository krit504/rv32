/* mmio.h: the simulation MMIO window (stores only; see tb/sys_monitor.sv). */
#ifndef MMIO_H
#define MMIO_H

#define MMIO_BASE   0xF0000000u
#define MMIO_HALT   (*(volatile unsigned *)(MMIO_BASE + 0x00))
#define MMIO_START  (*(volatile unsigned *)(MMIO_BASE + 0x04))
#define MMIO_STOP   (*(volatile unsigned *)(MMIO_BASE + 0x08))
#define MMIO_PHASE  (*(volatile unsigned *)(MMIO_BASE + 0x0C))
#define MMIO_PUTCH  (*(volatile unsigned *)(MMIO_BASE + 0x10))

/* Measurement window around a region of interest (counted by sys_monitor). */
static inline void perf_start(void) { MMIO_START = 1; __asm__ volatile ("nop"); }
static inline void perf_stop(void)  { MMIO_STOP = 1; }
static inline void phase(unsigned id) { MMIO_PHASE = id; }
static inline void putch(char c) { MMIO_PUTCH = (unsigned char)c; }

#endif
