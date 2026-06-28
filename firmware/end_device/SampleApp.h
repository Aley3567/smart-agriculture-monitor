/**
 * @file    SampleApp.h
 * @brief   智慧农业监测系统 - 终端节点头文件
 * @note    基于 Z-Stack SampleApp 例程修改，用于 CC2530 + DHT11 传感器采集
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

/* 应用层端点号 */
#define SAMPLEAPP_ENDPOINT           20

/* 应用层 Profile ID（使用自定义值） */
#define SAMPLEAPP_PROFID             0x0F08

/* 应用层 Device ID */
#define SAMPLEAPP_DEVICEID           0x0001

/* 应用层版本号 */
#define SAMPLEAPP_DEVICE_VERSION     0

/* 应用层标志位 */
#define SAMPLEAPP_FLAGS              0

/* 簇 ID（用于区分消息类型） */
#define SAMPLEAPP_PERIODIC_CLUSTERID 1   /* 周期性传感器数据 */
#define SAMPLEAPP_CTRL_CLUSTERID     2   /* 控制命令 */

/* 最大簇数量 */
#define SAMPLEAPP_MAX_CLUSTERS       2

/* 传感器数据发送周期（毫秒） */
#define SAMPLEAPP_SEND_PERIODIC_MSG_TIMEOUT   2000

/* 用户自定义事件 */
#define SAMPLEAPP_SEND_PERIODIC_MSG_EVT       0x0001

/*********************************************************************
 * DHT11 引脚定义 (P2.0)
 *********************************************************************/
#define DHT11_PORT        P2
#define DHT11_BIT         0
#define DHT11_PIN         P2_0

/* P2.0 方向寄存器：P2DIR bit0 */
#define DHT11_DIR_OUT()   (P2DIR |= 0x01)   /* 设置为输出 */
#define DHT11_DIR_IN()    (P2DIR &= ~0x01)  /* 设置为输入 */
#define DHT11_HIGH()      (DHT11_PIN = 1)
#define DHT11_LOW()       (DHT11_PIN = 0)
#define DHT11_READ()      (DHT11_PIN)

/*********************************************************************
 * 执行器引脚定义
 *********************************************************************/
/* P1.0 - LED1/水泵 */
#define ACTUATOR_PUMP_PIN     P1_0
/* P1.1 - LED2/施肥 */
#define ACTUATOR_FERT_PIN     P1_1
/* P1.6 - LED3/天窗 */
#define ACTUATOR_WINDOW_PIN   P1_6

/*********************************************************************
 * 函数声明
 *********************************************************************/
extern void SampleApp_Init(uint8 task_id);
extern uint16 SampleApp_ProcessEvent(uint8 task_id, uint16 events);

#ifdef __cplusplus
}
#endif

#endif /* SAMPLEAPP_H */
