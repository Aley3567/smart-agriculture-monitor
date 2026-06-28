/**
 * @file    SampleApp.c
 * @brief   智慧农业监测系统 - 协调器主应用
 * @note    功能：接收终端节点 ZigBee 数据转发到 UART0，接收 UART0 命令转发到终端节点
 *          基于 Z-Stack 2.5.1a SampleApp 例程修改，CC2530 (8051内核)
 */

/*********************************************************************
 * 头文件包含
 *********************************************************************/
#include "OSAL.h"
#include "ZGlobals.h"
#include "AF.h"
#include "aps_groups.h"
#include "ZDApp.h"
#include "ZDObject.h"
#include "ZDProfile.h"

#include "SampleApp.h"
#include "DebugTrace.h"

#include "OnBoard.h"
#include "hal_lcd.h"
#include "hal_led.h"
#include "hal_key.h"
#include "hal_uart.h"

#include <string.h>

/*********************************************************************
 * 全局变量
 *********************************************************************/

/* 任务 ID，由 OSAL 分配 */
static uint8 SampleApp_TaskID;

/* 发送序列号 */
static uint8 SampleApp_TransID;

/* 应用层端点描述符 */
static endPointDesc_t SampleApp_epDesc;

/* 簇列表 */
static const cId_t SampleApp_ClusterList[SAMPLEAPP_MAX_CLUSTERS] =
{
    SAMPLEAPP_PERIODIC_CLUSTERID,
    SAMPLEAPP_CTRL_CLUSTERID
};

/* SimpleDescription（应用层描述） */
static const SimpleDescriptionFormat_t SampleApp_SimpleDesc =
{
    SAMPLEAPP_ENDPOINT,
    SAMPLEAPP_PROFID,
    SAMPLEAPP_DEVICEID,
    SAMPLEAPP_DEVICE_VERSION,
    SAMPLEAPP_FLAGS,
    SAMPLEAPP_MAX_CLUSTERS,
    (cId_t *)SampleApp_ClusterList,
    SAMPLEAPP_MAX_CLUSTERS,
    (cId_t *)SampleApp_ClusterList
};

/* 串口接收缓冲区 */
static uint8 uart_rx_buf[SAMPLEAPP_UART_RX_BUF_SIZE];

/*********************************************************************
 * 本地函数声明
 *********************************************************************/
static void SampleApp_MessageMSGCB(afIncomingMSGPacket_t *pckt);
static void SampleApp_UartInit(void);
static void SampleApp_UartCB(uint8 port, uint8 event);
static void SampleApp_SendToEndDevice(uint8 *data, uint16 len);

/*********************************************************************
 * @fn      SampleApp_UartInit
 * @brief   初始化 UART0 串口通信
 *          波特率 115200，用于与 PC 上位机通信
 *          P0.2 = RX, P0.3 = TX (UART0 备用位置1)
 *********************************************************************/
static void SampleApp_UartInit(void)
{
    halUARTCfg_t uartConfig;

    /* 配置串口参数 */
    uartConfig.configured           = TRUE;
    uartConfig.baudRate             = SAMPLEAPP_UART_BAUD;
    uartConfig.flowControl          = FALSE;              /* 无硬件流控 */
    uartConfig.flowControlThreshold = 0;
    uartConfig.rx.maxBufSize        = SAMPLEAPP_UART_RX_BUF_SIZE;
    uartConfig.tx.maxBufSize        = SAMPLEAPP_UART_TX_BUF_SIZE;
    uartConfig.idleTimeout          = 6;                  /* 空闲超时(字符周期) */
    uartConfig.intEnable            = TRUE;               /* 使能中断 */
    uartConfig.callBackFunc         = SampleApp_UartCB;   /* 注册回调函数 */

    /* 打开串口 */
    HalUARTOpen(SAMPLEAPP_UART_PORT, &uartConfig);
}

/*********************************************************************
 * @fn      SampleApp_UartCB
 * @brief   UART0 接收回调函数
 *          当串口收到 PC 发来的数据时被调用，
 *          将数据通过 ZigBee 转发给终端节点
 * @param   port  - 串口端口号
 * @param   event - 串口事件
 *********************************************************************/
static void SampleApp_UartCB(uint8 port, uint8 event)
{
    uint16 rx_len;
    (void)event;  /* 消除未使用参数的警告 */

    /* 读取串口接收到的数据 */
    rx_len = HalUARTRead(port, uart_rx_buf, SAMPLEAPP_UART_RX_BUF_SIZE - 1);

    if (rx_len > 0)
    {
        /* 确保字符串结尾 */
        uart_rx_buf[rx_len] = '\0';

        /* 将 PC 发来的控制命令通过 ZigBee 转发给终端节点 */
        SampleApp_SendToEndDevice(uart_rx_buf, rx_len);
    }
}

/*********************************************************************
 * @fn      SampleApp_SendToEndDevice
 * @brief   通过 ZigBee 向终端节点发送控制命令（广播方式）
 * @param   data - 要发送的数据指针
 * @param   len  - 数据长度
 * @note    使用广播地址 0xFFFF，所有终端节点都能收到
 *          如果只有一个终端节点，也可以改为点播
 *********************************************************************/
static void SampleApp_SendToEndDevice(uint8 *data, uint16 len)
{
    afAddrType_t dstAddr;

    /* 广播发送，所有终端节点都接收 */
    dstAddr.addrMode       = (afAddrMode_t)AddrBroadcast;
    dstAddr.addr.shortAddr = 0xFFFF;
    dstAddr.endPoint       = SAMPLEAPP_ENDPOINT;

    AF_DataRequest(&dstAddr,
                   &SampleApp_epDesc,
                   SAMPLEAPP_CTRL_CLUSTERID,   /* 使用控制命令簇 ID */
                   len,
                   data,
                   &SampleApp_TransID,
                   AF_DISCV_ROUTE,
                   AF_DEFAULT_RADIUS);
}

/*********************************************************************
 * @fn      SampleApp_Init
 * @brief   协调器应用初始化（OSAL 任务初始化时调用）
 * @param   task_id - OSAL 分配的任务 ID
 *********************************************************************/
void SampleApp_Init(uint8 task_id)
{
    SampleApp_TaskID = task_id;
    SampleApp_TransID = 0;

    /* 注册应用层端点 */
    SampleApp_epDesc.endPoint   = SAMPLEAPP_ENDPOINT;
    SampleApp_epDesc.task_id    = &SampleApp_TaskID;
    SampleApp_epDesc.simpleDesc = (SimpleDescriptionFormat_t *)&SampleApp_SimpleDesc;
    SampleApp_epDesc.latencyReq = noLatencyReqs;

    afRegister(&SampleApp_epDesc);

    /* 初始化 UART0 串口 */
    SampleApp_UartInit();
}

/*********************************************************************
 * @fn      SampleApp_ProcessEvent
 * @brief   协调器事件处理函数（OSAL 事件循环调用）
 * @param   task_id - 任务 ID
 * @param   events  - 待处理事件位掩码
 * @return  未处理的事件位掩码
 *********************************************************************/
uint16 SampleApp_ProcessEvent(uint8 task_id, uint16 events)
{
    afIncomingMSGPacket_t *MSGpkt;
    (void)task_id;

    /* ---- 系统消息事件 ---- */
    if (events & SYS_EVENT_MSG)
    {
        MSGpkt = (afIncomingMSGPacket_t *)osal_msg_receive(SampleApp_TaskID);

        while (MSGpkt)
        {
            switch (MSGpkt->hdr.event)
            {
                /* ZigBee 网络状态变化 */
                case ZDO_STATE_CHANGE:
                    /* 协调器建网成功，可在此添加指示（如点亮LED） */
                    if ((devStates_t)(MSGpkt->hdr.status) == DEV_ZB_COORD)
                    {
                        HalLedSet(HAL_LED_1, HAL_LED_MODE_ON);
                    }
                    break;

                /* 收到 ZigBee 数据（终端节点发来的传感器数据） */
                case AF_INCOMING_MSG_CMD:
                    SampleApp_MessageMSGCB(MSGpkt);
                    break;

                default:
                    break;
            }

            /* 释放消息内存，获取下一条消息 */
            osal_msg_deallocate((uint8 *)MSGpkt);
            MSGpkt = (afIncomingMSGPacket_t *)osal_msg_receive(SampleApp_TaskID);
        }

        return (events ^ SYS_EVENT_MSG);
    }

    return 0;  /* 丢弃未知事件 */
}

/*********************************************************************
 * @fn      SampleApp_MessageMSGCB
 * @brief   处理收到的 ZigBee 消息（终端节点发来的传感器数据）
 *          将数据原样通过 UART0 转发到 PC，末尾追加 \r\n
 * @param   pckt - 收到的消息包指针
 *
 * 终端节点数据格式: "t:25-h:60-l:800-s:45"
 * 转发到 PC 格式:   "t:25-h:60-l:800-s:45\r\n"
 *********************************************************************/
static void SampleApp_MessageMSGCB(afIncomingMSGPacket_t *pckt)
{
    uint8 *rx_data;
    uint16 rx_len;

    if (pckt->clusterId != SAMPLEAPP_PERIODIC_CLUSTERID)
    {
        return;  /* 不是传感器数据簇，忽略 */
    }

    rx_data = pckt->cmd.Data;
    rx_len  = pckt->cmd.DataLength;

    if (rx_len > 0)
    {
        /* 将传感器数据原样通过串口发送到 PC */
        HalUARTWrite(SAMPLEAPP_UART_PORT, rx_data, rx_len);

        /* 追加换行符 \r\n 方便 PC 端解析 */
        HalUARTWrite(SAMPLEAPP_UART_PORT, (uint8 *)"\r\n", 2);
    }
}
