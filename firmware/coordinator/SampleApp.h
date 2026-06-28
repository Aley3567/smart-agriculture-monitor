/**
 * @file    SampleApp.h
 * @brief   智慧农业监测系统 - 协调器头文件
 * @note    基于 Z-Stack SampleApp 例程修改，负责 ZigBee-UART 数据桥接
 */

#ifndef SAMPLEAPP_H
#define SAMPLEAPP_H

#ifdef __cplusplus
extern "C" {
#endif

/*********************************************************************
 * 头文件包含
 *********************************************************************/
#include "ZComDef.h"

/*********************************************************************
 * 宏定义
 *********************************************************************/

/* 应用层端点号（与终端节点保持一致） */
#define SAMPLEAPP_ENDPOINT           20

/* 应用层 Profile ID */
#define SAMPLEAPP_PROFID             0x0F08

/* 应用层 Device ID */
#define SAMPLEAPP_DEVICEID           0x0001

/* 应用层版本号 */
#define SAMPLEAPP_DEVICE_VERSION     0

/* 应用层标志位 */
#define SAMPLEAPP_FLAGS              0

/* 簇 ID（与终端节点保持一致） */
#define SAMPLEAPP_PERIODIC_CLUSTERID 1   /* 周期性传感器数据 */
#define SAMPLEAPP_CTRL_CLUSTERID     2   /* 控制命令 */

/* 最大簇数量 */
#define SAMPLEAPP_MAX_CLUSTERS       2

/* 串口配置 */
#define SAMPLEAPP_UART_PORT          HAL_UART_PORT_0   /* UART0 */
#define SAMPLEAPP_UART_BAUD          HAL_UART_BR_115200
#define SAMPLEAPP_UART_RX_BUF_SIZE   128
#define SAMPLEAPP_UART_TX_BUF_SIZE   128

/* 用户自定义事件 */
#define SAMPLEAPP_UART_RX_EVT        0x0001

/*********************************************************************
 * 函数声明
 *********************************************************************/
extern void SampleApp_Init(uint8 task_id);
extern uint16 SampleApp_ProcessEvent(uint8 task_id, uint16 events);

#ifdef __cplusplus
}
#endif

#endif /* SAMPLEAPP_H */
