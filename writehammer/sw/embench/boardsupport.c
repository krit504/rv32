/* boardsupport.c: Embench-IoT board hooks for this core (included by support/board.c via -I).
 * start_trigger/stop_trigger open and close the MMIO measurement window counted by tb/sys_monitor.sv
 * (this core has no readable cycle counter); there is no board to initialise. */
#include "../mmio.h"

void initialise_board(void) { }
void __attribute__((noinline)) start_trigger(void) { perf_start(); }
void __attribute__((noinline)) stop_trigger(void) { perf_stop(); }
