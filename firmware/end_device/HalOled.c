/**
 * @file    HalOled.c
 * @brief   SSD1306 128x64 software-SPI OLED driver for CC2530.
 * @note    Ported from the 中景园电子 0.96" C51 SPI demo. Init sequence and
 *          timing kept identical to the vendor demo (matches this panel);
 *          only the pin layer, integer types and GPIO setup are re-targeted
 *          to the 创思通信 CC2530 board. CS is tied to GND, so no chip-select
 *          toggling is emitted. Compiled only when HAL_OLED is defined.
 */
#include <ioCC2530.h>
#include "hal_types.h"
#include "HalOled.h"
#include "HalOledFont.h"

#define OLED_MAX_COLUMN   128

/*********************************************************************
 * @fn      OledDelayMs
 * @brief   Rough millisecond delay for the reset pulse (CC2530 @32MHz).
 *          Precision is not critical; erring long is safe for reset.
 *********************************************************************/
static void OledDelayMs(uint16 ms)
{
    uint16 i;
    while (ms--)
    {
        for (i = 0; i < 1200; i++)
        {
            asm("NOP");
        }
    }
}

/*********************************************************************
 * @fn      OledWrByte
 * @brief   Shift one byte out over software SPI, MSB first.
 * @param   dat - byte to send
 * @param   cmd - OLED_CMD for a command, OLED_DATA for display data
 *********************************************************************/
static void OledWrByte(uint8 dat, uint8 cmd)
{
    uint8 i;

    if (cmd)
        OLED_DC_Set();
    else
        OLED_DC_Clr();

    for (i = 0; i < 8; i++)
    {
        OLED_SCLK_Clr();
        if (dat & 0x80)
            OLED_SDIN_Set();
        else
            OLED_SDIN_Clr();
        OLED_SCLK_Set();
        dat <<= 1;
    }

    OLED_DC_Set();
}

/*********************************************************************
 * @fn      OledSetPos
 * @brief   Set the page (y) and column (x) cursor. Column low nibble keeps
 *          the vendor demo's |0x01 offset so it matches this panel.
 *********************************************************************/
static void OledSetPos(uint8 x, uint8 y)
{
    OledWrByte(0xb0 + y, OLED_CMD);
    OledWrByte(((x & 0xf0) >> 4) | 0x10, OLED_CMD);
    OledWrByte((x & 0x0f) | 0x01, OLED_CMD);
}

/*********************************************************************
 * @fn      OledInitGpio
 * @brief   Drive OLED lines (P0.0 DC, P1.2 SCK, P1.3 MOSI, P1.7 RES) as
 *          general-purpose outputs. Does not touch the actuator/DHT11 pins
 *          configured by SampleApp_GPIO_Init.
 *********************************************************************/
static void OledInitGpio(void)
{
    P0SEL &= ~0x01;   /* P0.0 as GPIO (DC) */
    P0DIR |=  0x01;   /* P0.0 output */

    P1SEL &= ~0x8C;   /* P1.2 SCK, P1.3 MOSI, P1.7 RES as GPIO */
    P1DIR |=  0x8C;   /* those three as output */
}

/*********************************************************************
 * @fn      HalOledClear
 * @brief   Blank the whole 128x64 frame (all 8 pages).
 *********************************************************************/
void HalOledClear(void)
{
    uint8 i, n;

    for (i = 0; i < 8; i++)
    {
        OledWrByte(0xb0 + i, OLED_CMD);   /* page address 0~7 */
        OledWrByte(0x00, OLED_CMD);       /* column low  nibble */
        OledWrByte(0x10, OLED_CMD);       /* column high nibble */
        for (n = 0; n < 128; n++)
        {
            OledWrByte(0x00, OLED_DATA);
        }
    }
}

/*********************************************************************
 * @fn      OledShowChar
 * @brief   Draw one 8x16 ASCII glyph at column x, page y.
 *********************************************************************/
static void OledShowChar(uint8 x, uint8 y, uint8 chr)
{
    uint8 i, c;

    c = (uint8)(chr - ' ');
    if (c >= 95)          /* out-of-range char -> blank */
    {
        c = 0;
    }

    if (x > OLED_MAX_COLUMN - 1)
    {
        x = 0;
        y = y + 2;
    }

    OledSetPos(x, y);
    for (i = 0; i < 8; i++)
    {
        OledWrByte(HalOled_F8x16[c][i], OLED_DATA);
    }

    OledSetPos(x, y + 1);
    for (i = 0; i < 8; i++)
    {
        OledWrByte(HalOled_F8x16[c][i + 8], OLED_DATA);
    }
}

/*********************************************************************
 * @fn      HalOledShowStr
 * @brief   Draw a NUL-terminated ASCII string starting at column x, page y.
 *          Wraps to the next text row when it runs off the right edge.
 *********************************************************************/
void HalOledShowStr(uint8 x, uint8 y, uint8 *str)
{
    uint8 j = 0;

    while (str[j] != '\0')
    {
        OledShowChar(x, y, str[j]);
        x += 8;
        if (x > 120)
        {
            x = 0;
            y += 2;
        }
        j++;
    }
}

/*********************************************************************
 * @fn      HalOledInit
 * @brief   Reset and initialise the SSD1306 panel, then clear it.
 *          Command sequence matches the vendor demo for this module.
 *********************************************************************/
void HalOledInit(void)
{
    OledInitGpio();

    OLED_RST_Set();
    OledDelayMs(100);
    OLED_RST_Clr();
    OledDelayMs(100);
    OLED_RST_Set();

    OledWrByte(0xAE, OLED_CMD);  /* turn off panel */
    OledWrByte(0x00, OLED_CMD);  /* set low column address */
    OledWrByte(0x10, OLED_CMD);  /* set high column address */
    OledWrByte(0x40, OLED_CMD);  /* set start line address */
    OledWrByte(0x81, OLED_CMD);  /* set contrast control register */
    OledWrByte(0xCF, OLED_CMD);  /* brightness */
    OledWrByte(0xA1, OLED_CMD);  /* set SEG/column remap */
    OledWrByte(0xC8, OLED_CMD);  /* set COM/row scan direction */
    OledWrByte(0xA6, OLED_CMD);  /* normal display */
    OledWrByte(0xA8, OLED_CMD);  /* set multiplex ratio */
    OledWrByte(0x3F, OLED_CMD);  /* 1/64 duty */
    OledWrByte(0xD3, OLED_CMD);  /* set display offset */
    OledWrByte(0x00, OLED_CMD);  /* no offset */
    OledWrByte(0xD5, OLED_CMD);  /* set display clock divide ratio */
    OledWrByte(0x80, OLED_CMD);
    OledWrByte(0xD9, OLED_CMD);  /* set pre-charge period */
    OledWrByte(0xF1, OLED_CMD);
    OledWrByte(0xDA, OLED_CMD);  /* set COM pins hardware config */
    OledWrByte(0x12, OLED_CMD);
    OledWrByte(0xDB, OLED_CMD);  /* set vcomh */
    OledWrByte(0x40, OLED_CMD);
    OledWrByte(0x20, OLED_CMD);  /* set page addressing mode */
    OledWrByte(0x02, OLED_CMD);
    OledWrByte(0x8D, OLED_CMD);  /* charge pump setting */
    OledWrByte(0x14, OLED_CMD);  /* enable charge pump */
    OledWrByte(0xA4, OLED_CMD);  /* disable entire display on */
    OledWrByte(0xA6, OLED_CMD);  /* disable inverse display */
    OledWrByte(0xAF, OLED_CMD);  /* turn on panel */

    HalOledClear();
    OledSetPos(0, 0);
}
