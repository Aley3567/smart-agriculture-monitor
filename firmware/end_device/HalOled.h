/**
 * @file    HalOled.h
 * @brief   SSD1306 128x64 SPI OLED driver for the CC2530 end device.
 * @note    Ported from the 中景园电子 0.96" C51 SPI demo (oled.c/oled.h),
 *          re-pinned for the 创思通信 integrated board schematic:
 *
 *            OLED signal | CC2530 pin | note
 *            ------------+------------+------------------------
 *            SCK / D0    | P1.2       | SPI clock
 *            MOSI / D1   | P1.3       | SPI data
 *            RES         | P1.7       | active-low reset
 *            DC          | P0.0       | command/data select
 *            CS          | GND        | tied low, no IO used
 *            VCC         | 3.3V       | power
 *
 *          Controller: SSD1306, 128x64, page addressing.
 *          Only enabled when HAL_OLED is defined in the IAR project options.
 */
#ifndef HALOLED_H
#define HALOLED_H

#ifdef __cplusplus
extern "C" {
#endif

#include "hal_types.h"

/*********************************************************************
 * OLED pin mapping (CC2530) — do NOT reuse the demo's P1.0~P1.4.
 *********************************************************************/
#define OLED_RST_Set()   (P1_7 = 1)
#define OLED_RST_Clr()   (P1_7 = 0)
#define OLED_DC_Set()    (P0_0 = 1)
#define OLED_DC_Clr()    (P0_0 = 0)
#define OLED_SCLK_Set()  (P1_2 = 1)
#define OLED_SCLK_Clr()  (P1_2 = 0)
#define OLED_SDIN_Set()  (P1_3 = 1)
#define OLED_SDIN_Clr()  (P1_3 = 0)
/* CS is tied to GND on this board, so chip select is a no-op. */

/* Command / data flag for the byte writer. */
#define OLED_CMD    0
#define OLED_DATA   1

/*********************************************************************
 * Public API expected by SampleApp.c
 *********************************************************************/
extern void HalOledInit(void);
extern void HalOledClear(void);
extern void HalOledShowStr(uint8 x, uint8 y, uint8 *str);

#ifdef __cplusplus
}
#endif

#endif /* HALOLED_H */
