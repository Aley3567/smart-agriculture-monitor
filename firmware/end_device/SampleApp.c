/**
 * @file    SampleApp.c
 * @brief   智慧农业监测系统 - 终端节点主应用
 * @note    功能：DHT11温湿度采集、模拟光照/土壤湿度、ZigBee发送、接收控制命令、OLED显示
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

/* OLED 驱动头文件（可选：如果项目中没有该文件，在 IAR 预编译宏中不定义 HAL_OLED 即可跳过） */
#ifdef HAL_OLED
#include "HalOled.h"
#endif

#include <string.h>
#include <stdio.h>

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

/* 点播发送目标地址（协调器 0x0000） */
static afAddrType_t SampleApp_DstAddr;

/*********************************************************************
 * 传感器数据变量
 *********************************************************************/
static uint8  dht11_temp  = 25;   /* 温度（整数部分） */
static uint8  dht11_humi  = 60;   /* 湿度（整数部分） */
static uint16 light_value = 800;  /* 光照强度 (lux) */
static uint8  soil_value  = 45;   /* 土壤湿度 (%) */

/* 执行器状态：0=关, 1=开 */
static uint8 pump_state   = 0;    /* 水泵继电器 P0.6 + 指示灯 P1.0 */
static uint8 fert_state   = 0;    /* 施肥指示灯 P1.1 */
static uint8 window_state = 0;    /* 天窗指示灯 P1.6 */

/* 随机种子（用于模拟传感器波动） */
static uint16 rand_seed = 12345;

/*********************************************************************
 * 本地函数声明
 *********************************************************************/
static void SampleApp_GPIO_Init(void);
static void SampleApp_MessageMSGCB(afIncomingMSGPacket_t *pckt);
static void SampleApp_SendPeriodicMessage(void);

static uint8 DHT11_ReadData(uint8 *temp, uint8 *humi);
static uint8 DHT11_ReadByte(void);
static void  DHT11_DelayUs(uint16 us);

static void SampleApp_SimulateLight(void);
static void SampleApp_SimulateSoil(void);
static uint16 SampleApp_SimpleRand(void);

#ifdef HAL_OLED
static void SampleApp_UpdateOLED(void);
#endif

/*********************************************************************
 * @fn      SampleApp_SimpleRand
 * @brief   简易伪随机数生成（8051 没有 stdlib rand）
 * @return  0~32767 之间的伪随机数
 *********************************************************************/
static uint16 SampleApp_SimpleRand(void)
{
    rand_seed = rand_seed * 1103 + 12345;
    return (rand_seed >> 1) & 0x7FFF;
}

/*********************************************************************
 * @fn      DHT11_DelayUs
 * @brief   微秒级延时（CC2530 主频32MHz，粗略延时）
 * @param   us - 延时微秒数
 * @note    8051 每个指令周期约4个时钟周期，循环体约8个周期
 *          32MHz / 4 = 8 MIPS，1us 约 8 条指令
 *********************************************************************/
static void DHT11_DelayUs(uint16 us)
{
    while (us--)
    {
        asm("NOP"); asm("NOP"); asm("NOP"); asm("NOP");
        asm("NOP"); asm("NOP"); asm("NOP"); asm("NOP");
    }
}

/*********************************************************************
 * @fn      DHT11_ReadByte
 * @brief   从 DHT11 读取1个字节（8bit）
 * @return  读到的字节值
 * @note    时序：每个 bit 以 50us 低电平开始，
 *          高电平持续 26-28us 表示 '0'，70us 表示 '1'
 *********************************************************************/
static uint8 DHT11_ReadByte(void)
{
    uint8 i;
    uint8 byte = 0;
    uint8 timeout;

    for (i = 0; i < 8; i++)
    {
        byte <<= 1;

        /* 等待低电平结束（bit 起始的 50us 低电平） */
        timeout = 100;
        while (!DHT11_READ() && timeout--)
        {
            DHT11_DelayUs(1);
        }

        /* 延时 30us 后判断：如果还是高电平说明是 '1' */
        DHT11_DelayUs(30);

        if (DHT11_READ())
        {
            byte |= 0x01;

            /* 等待高电平结束 */
            timeout = 100;
            while (DHT11_READ() && timeout--)
            {
                DHT11_DelayUs(1);
            }
        }
    }

    return byte;
}

/*********************************************************************
 * @fn      DHT11_ReadData
 * @brief   读取 DHT11 温湿度数据（完整时序）
 * @param   temp - 输出温度值（整数部分）
 * @param   humi - 输出湿度值（整数部分）
 * @return  0=成功, 1=无响应, 2=校验失败
 *
 * 时序流程：
 *   1. 主机拉低数据线至少 18ms（这里用20ms），通知 DHT11 准备
 *   2. 主机释放总线，切换为输入模式
 *   3. DHT11 响应：拉低 80us + 拉高 80us
 *   4. 传输 40bit 数据（5字节）
 *   5. 校验：前4字节之和的低8位 == 第5字节
 *********************************************************************/
static uint8 DHT11_ReadData(uint8 *temp, uint8 *humi)
{
    uint8 buf[5];
    uint8 timeout;
    uint8 i;

    /* ---- 第1步：主机发送起始信号 ---- */
    DHT11_DIR_OUT();          /* 设置为输出 */
    DHT11_LOW();              /* 拉低数据线 */
    DHT11_DelayUs(20000);     /* 保持 20ms（>18ms） */
    DHT11_HIGH();             /* 释放总线 */
    DHT11_DelayUs(30);        /* 等待 20-40us */

    /* ---- 第2步：切换为输入，等待 DHT11 响应 ---- */
    DHT11_DIR_IN();

    /* 等待 DHT11 拉低（响应信号，约 80us） */
    timeout = 100;
    while (DHT11_READ() && timeout--)
    {
        DHT11_DelayUs(1);
    }
    if (timeout == 0) return 1;  /* 超时，DHT11 无响应 */

    /* 等待低电平结束（约 80us） */
    timeout = 100;
    while (!DHT11_READ() && timeout--)
    {
        DHT11_DelayUs(1);
    }
    if (timeout == 0) return 1;

    /* 等待高电平结束（约 80us） */
    timeout = 100;
    while (DHT11_READ() && timeout--)
    {
        DHT11_DelayUs(1);
    }
    if (timeout == 0) return 1;

    /* ---- 第3步：读取 40bit 数据（5字节） ---- */
    for (i = 0; i < 5; i++)
    {
        buf[i] = DHT11_ReadByte();
    }

    /* ---- 第4步：校验 ---- */
    if ((uint8)(buf[0] + buf[1] + buf[2] + buf[3]) != buf[4])
    {
        return 2;  /* 校验失败 */
    }

    /* 数据有效，赋值 */
    *humi = buf[0];  /* 湿度整数部分 */
    *temp = buf[2];  /* 温度整数部分 */

    return 0;  /* 成功 */
}

/*********************************************************************
 * @fn      SampleApp_SimulateLight
 * @brief   模拟光照传感器数据（基础值 + 随机波动）
 * @note    范围 500~1500 lux，每次波动 +/- 50
 *********************************************************************/
static void SampleApp_SimulateLight(void)
{
    int16 delta;

    /* 生成 -50 ~ +50 的波动 */
    delta = (int16)(SampleApp_SimpleRand() % 101) - 50;
    light_value = (uint16)((int16)light_value + delta);

    /* 限幅 */
    if (light_value < 500)  light_value = 500;
    if (light_value > 1500) light_value = 1500;
}

/*********************************************************************
 * @fn      SampleApp_SimulateSoil
 * @brief   模拟土壤湿度传感器数据（基础值 + 随机波动）
 * @note    范围 40~60%，每次波动 +/- 3
 *********************************************************************/
static void SampleApp_SimulateSoil(void)
{
    int8 delta;

    /* 生成 -3 ~ +3 的波动 */
    delta = (int8)(SampleApp_SimpleRand() % 7) - 3;
    soil_value = (uint8)((int8)soil_value + delta);

    /* 限幅 */
    if (soil_value < 40) soil_value = 40;
    if (soil_value > 60) soil_value = 60;
}

/*********************************************************************
 * @fn      SampleApp_GPIO_Init
 * @brief   初始化 GPIO 引脚
 *          P0.6 → 通用输出（继电器控制）
 *          P1.0, P1.1, P1.6 → 通用输出（板载 LED，低电平亮）
 *          P2.0 → DHT11 数据线（初始设为输出）
 *********************************************************************/
static void SampleApp_GPIO_Init(void)
{
    /* P0.6 设置为通用 IO 输出模式（继电器） */
    P0SEL &= ~0x40;   /* P0.6 设为通用 IO */
    P0DIR |= 0x40;    /* P0.6 设为输出 */

    /* P1.0, P1.1, P1.6 设置为通用 IO 输出模式（LED） */
    P1SEL &= ~0x43;   /* P1.0, P1.1, P1.6 设为通用 IO */
    P1DIR |= 0x43;    /* P1.0, P1.1, P1.6 设为输出 */

    /* 初始状态：全部关闭 */
    ACTUATOR_RELAY_OFF();
    ACTUATOR_LED_OFF(ACTUATOR_PUMP_LED_PIN);
    ACTUATOR_LED_OFF(ACTUATOR_FERT_PIN);
    ACTUATOR_LED_OFF(ACTUATOR_WINDOW_PIN);

    /* P2.0 设置为通用 IO（DHT11 数据线） */
    P2SEL &= ~0x01;   /* P2.0 设为通用 IO */
    DHT11_DIR_OUT();   /* 初始设为输出 */
    DHT11_HIGH();      /* 空闲状态为高电平 */
}

#ifdef HAL_OLED
/*********************************************************************
 * @fn      SampleApp_UpdateOLED
 * @brief   刷新 OLED 显示内容
 *          行1: "Smart Agri"
 *          行2: "T:xxC H:xx%"
 *          行3: "L:xxxx S:xx%"
 *          行4: 执行器状态 "P:ON F:OFF W:ON"
 *********************************************************************/
static void SampleApp_UpdateOLED(void)
{
    uint8 str_buf[20];

    /* 行1：系统名称 */
    HalOledShowStr(0, 0, "Smart Agri");

    /* 行2：温湿度 */
    /* 8051 IAR 环境下 sprintf 对 %d 支持有限，手动拼接更可靠 */
    str_buf[0] = 'T'; str_buf[1] = ':';
    str_buf[2] = (dht11_temp / 10) + '0';
    str_buf[3] = (dht11_temp % 10) + '0';
    str_buf[4] = 'C'; str_buf[5] = ' ';
    str_buf[6] = 'H'; str_buf[7] = ':';
    str_buf[8] = (dht11_humi / 10) + '0';
    str_buf[9] = (dht11_humi % 10) + '0';
    str_buf[10] = '%';
    str_buf[11] = '\0';
    HalOledShowStr(0, 2, str_buf);

    /* 行3：光照和土壤湿度 */
    str_buf[0] = 'L'; str_buf[1] = ':';
    str_buf[2] = (light_value / 1000) + '0';
    str_buf[3] = ((light_value / 100) % 10) + '0';
    str_buf[4] = ((light_value / 10) % 10) + '0';
    str_buf[5] = (light_value % 10) + '0';
    str_buf[6] = ' ';
    str_buf[7] = 'S'; str_buf[8] = ':';
    str_buf[9] = (soil_value / 10) + '0';
    str_buf[10] = (soil_value % 10) + '0';
    str_buf[11] = '%';
    str_buf[12] = '\0';
    HalOledShowStr(0, 4, str_buf);

    /* 行4：执行器状态 P=水泵 F=施肥 W=天窗 */
    str_buf[0] = 'P'; str_buf[1] = ':';
    if (pump_state) { str_buf[2] = 'O'; str_buf[3] = 'N'; str_buf[4] = ' '; }
    else            { str_buf[2] = 'O'; str_buf[3] = 'F'; str_buf[4] = 'F'; }

    str_buf[5] = ' ';
    str_buf[6] = 'F'; str_buf[7] = ':';
    if (fert_state) { str_buf[8] = 'O'; str_buf[9] = 'N'; str_buf[10] = ' '; }
    else            { str_buf[8] = 'O'; str_buf[9] = 'F'; str_buf[10] = 'F'; }

    str_buf[11] = ' ';
    str_buf[12] = 'W'; str_buf[13] = ':';
    if (window_state) { str_buf[14] = 'O'; str_buf[15] = 'N'; str_buf[16] = '\0'; }
    else              { str_buf[14] = 'O'; str_buf[15] = 'F'; str_buf[16] = 'F'; str_buf[17] = '\0'; }

    HalOledShowStr(0, 6, str_buf);
}
#endif /* HAL_OLED */

/*********************************************************************
 * @fn      SampleApp_Init
 * @brief   终端节点应用初始化（OSAL 任务初始化时调用）
 * @param   task_id - OSAL 分配的任务 ID
 *********************************************************************/
void SampleApp_Init(uint8 task_id)
{
    SampleApp_TaskID = task_id;
    SampleApp_TransID = 0;

    /* 初始化 GPIO（执行器 + DHT11） */
    SampleApp_GPIO_Init();

    /* 初始化 OLED 显示屏（可选） */
#ifdef HAL_OLED
    HalOledInit();
    HalOledClear();
#endif

    /* 配置点播目标地址：协调器 0x0000 */
    SampleApp_DstAddr.addrMode       = (afAddrMode_t)Addr16Bit;
    SampleApp_DstAddr.addr.shortAddr = 0x0000;
    SampleApp_DstAddr.endPoint       = SAMPLEAPP_ENDPOINT;

    /* 注册应用层端点 */
    SampleApp_epDesc.endPoint   = SAMPLEAPP_ENDPOINT;
    SampleApp_epDesc.task_id    = &SampleApp_TaskID;
    SampleApp_epDesc.simpleDesc = (SimpleDescriptionFormat_t *)&SampleApp_SimpleDesc;
    SampleApp_epDesc.latencyReq = noLatencyReqs;

    afRegister(&SampleApp_epDesc);

    /* 初始显示 */
#ifdef HAL_OLED
    SampleApp_UpdateOLED();
#endif
}

/*********************************************************************
 * @fn      SampleApp_ProcessEvent
 * @brief   终端节点事件处理函数（OSAL 事件循环调用）
 * @param   task_id - 任务 ID
 * @param   events  - 待处理事件位掩码
 * @return  未处理的事件位掩码
 *********************************************************************/
uint16 SampleApp_ProcessEvent(uint8 task_id, uint16 events)
{
    afIncomingMSGPacket_t *MSGpkt;
    (void)task_id;  /* 消除未使用参数的警告 */

    /* ---- 系统消息事件 ---- */
    if (events & SYS_EVENT_MSG)
    {
        MSGpkt = (afIncomingMSGPacket_t *)osal_msg_receive(SampleApp_TaskID);

        while (MSGpkt)
        {
            switch (MSGpkt->hdr.event)
            {
                /* ZigBee 网络状态变化（入网成功后启动定时发送） */
                case ZDO_STATE_CHANGE:
                    if ((devStates_t)(MSGpkt->hdr.status) == DEV_END_DEVICE)
                    {
                        /* 终端节点入网成功，启动周期发送定时器 */
                        osal_start_timerEx(SampleApp_TaskID,
                                           SAMPLEAPP_SEND_PERIODIC_MSG_EVT,
                                           SAMPLEAPP_SEND_PERIODIC_MSG_TIMEOUT);
                    }
                    break;

                /* 收到 ZigBee 数据（协调器转发的控制命令） */
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

    /* ---- 周期性传感器数据发送事件 ---- */
    if (events & SAMPLEAPP_SEND_PERIODIC_MSG_EVT)
    {
        SampleApp_SendPeriodicMessage();

        /* 重新启动定时器（循环发送） */
        osal_start_timerEx(SampleApp_TaskID,
                           SAMPLEAPP_SEND_PERIODIC_MSG_EVT,
                           SAMPLEAPP_SEND_PERIODIC_MSG_TIMEOUT);

        return (events ^ SAMPLEAPP_SEND_PERIODIC_MSG_EVT);
    }

    return 0;  /* 丢弃未知事件 */
}

/*********************************************************************
 * @fn      SampleApp_SendPeriodicMessage
 * @brief   采集传感器数据并通过 ZigBee 发送到协调器
 *
 * 数据格式字符串: "t:25-h:60-l:800-s:45"
 *   t = 温度, h = 湿度, l = 光照, s = 土壤湿度
 *********************************************************************/
static void SampleApp_SendPeriodicMessage(void)
{
    uint8 send_buf[32];
    uint8 len = 0;

    /* ---- 1. 读取 DHT11 温湿度 ---- */
    {
        uint8 temp_val, humi_val;
        if (DHT11_ReadData(&temp_val, &humi_val) == 0)
        {
            /* 读取成功，更新全局变量 */
            dht11_temp = temp_val;
            dht11_humi = humi_val;
        }
        /* 读取失败则继续使用上次的值 */
    }

    /* ---- 2. 模拟光照和土壤湿度 ---- */
    SampleApp_SimulateLight();
    SampleApp_SimulateSoil();

    /* ---- 3. 组装数据字符串 ---- */
    /* 格式: "t:25-h:60-l:800-s:45" */

    /* t:xx */
    send_buf[len++] = 't';
    send_buf[len++] = ':';
    if (dht11_temp >= 10)
        send_buf[len++] = (dht11_temp / 10) + '0';
    send_buf[len++] = (dht11_temp % 10) + '0';

    send_buf[len++] = '-';

    /* h:xx */
    send_buf[len++] = 'h';
    send_buf[len++] = ':';
    if (dht11_humi >= 10)
        send_buf[len++] = (dht11_humi / 10) + '0';
    send_buf[len++] = (dht11_humi % 10) + '0';

    send_buf[len++] = '-';

    /* l:xxxx */
    send_buf[len++] = 'l';
    send_buf[len++] = ':';
    if (light_value >= 1000)
        send_buf[len++] = (light_value / 1000) + '0';
    if (light_value >= 100)
        send_buf[len++] = ((light_value / 100) % 10) + '0';
    if (light_value >= 10)
        send_buf[len++] = ((light_value / 10) % 10) + '0';
    send_buf[len++] = (light_value % 10) + '0';

    send_buf[len++] = '-';

    /* s:xx */
    send_buf[len++] = 's';
    send_buf[len++] = ':';
    if (soil_value >= 10)
        send_buf[len++] = (soil_value / 10) + '0';
    send_buf[len++] = (soil_value % 10) + '0';

    send_buf[len] = '\0';

    /* ---- 4. 通过 ZigBee 点播发送到协调器 ---- */
    AF_DataRequest(&SampleApp_DstAddr,
                   &SampleApp_epDesc,
                   SAMPLEAPP_PERIODIC_CLUSTERID,
                   len,
                   send_buf,
                   &SampleApp_TransID,
                   AF_DISCV_ROUTE,
                   AF_DEFAULT_RADIUS);

    /* ---- 5. 刷新 OLED 显示 ---- */
#ifdef HAL_OLED
    SampleApp_UpdateOLED();
#endif
}

/*********************************************************************
 * @fn      SampleApp_MessageMSGCB
 * @brief   处理收到的 ZigBee 消息（协调器转发的控制命令）
 * @param   pckt - 收到的消息包指针
 *
 * 命令格式（字符串匹配）：
 *   BLEGLED1 → P0.6继电器吸合 + P1.0指示灯亮
 *   BLEKLED1 → P0.6继电器断开 + P1.0指示灯灭
 *   BLEGLED2 → P1.1指示灯亮        BLEKLED2 → P1.1指示灯灭
 *   BLEGLED3 → P1.6指示灯亮        BLEKLED3 → P1.6指示灯灭
 *********************************************************************/
static void SampleApp_MessageMSGCB(afIncomingMSGPacket_t *pckt)
{
    uint8 *cmd_data;
    uint16 cmd_len;

    if (pckt->clusterId != SAMPLEAPP_CTRL_CLUSTERID)
    {
        return;  /* 不是控制命令簇，忽略 */
    }

    cmd_data = pckt->cmd.Data;
    cmd_len  = pckt->cmd.DataLength;

    /* 确保字符串以 '\0' 结尾，方便 strstr 匹配 */
    if (cmd_len > 0 && cmd_len < 30)
    {
        /* cmd_data 本身可能不含 '\0'，但 strstr 需要，
           这里直接在数据末尾补 '\0'（Z-Stack 消息缓冲区通常有余量） */
        cmd_data[cmd_len] = '\0';
    }

    /* ---- 水泵继电器 (P0.6) + LED1 指示 (P1.0) ---- */
    if (strstr((char *)cmd_data, "BLEGLED1") != NULL)
    {
        ACTUATOR_RELAY_ON();
        ACTUATOR_LED_ON(ACTUATOR_PUMP_LED_PIN);
        pump_state = 1;
    }
    else if (strstr((char *)cmd_data, "BLEKLED1") != NULL)
    {
        ACTUATOR_RELAY_OFF();
        ACTUATOR_LED_OFF(ACTUATOR_PUMP_LED_PIN);
        pump_state = 0;
    }

    /* ---- LED2/施肥 (P1.1，低电平亮) ---- */
    if (strstr((char *)cmd_data, "BLEGLED2") != NULL)
    {
        ACTUATOR_LED_ON(ACTUATOR_FERT_PIN);
        fert_state = 1;
    }
    else if (strstr((char *)cmd_data, "BLEKLED2") != NULL)
    {
        ACTUATOR_LED_OFF(ACTUATOR_FERT_PIN);
        fert_state = 0;
    }

    /* ---- LED3/天窗 (P1.6，低电平亮) ---- */
    if (strstr((char *)cmd_data, "BLEGLED3") != NULL)
    {
        ACTUATOR_LED_ON(ACTUATOR_WINDOW_PIN);
        window_state = 1;
    }
    else if (strstr((char *)cmd_data, "BLEKLED3") != NULL)
    {
        ACTUATOR_LED_OFF(ACTUATOR_WINDOW_PIN);
        window_state = 0;
    }

    /* 更新 OLED 显示执行器状态 */
#ifdef HAL_OLED
    SampleApp_UpdateOLED();
#endif
}
