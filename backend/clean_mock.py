"""清理线上 mock/test 数据 —— 删除 is_test=1 和 bridge_mode='mock' 的记录。

在后端停止时运行，避免 SQLite 锁。先统计再确认，支持 --dry-run 预览。

用法:
    cd backend && python3 clean_mock.py              # 交互确认后删除
    cd backend && python3 clean_mock.py --dry-run     # 只统计不删除
    cd backend && python3 clean_mock.py --yes          # 跳过确认直接删除
"""
import argparse
import sqlite3

DB = "agriculture.db"


def count_mock(conn):
    sensor_mock = conn.execute(
        "SELECT COUNT(*) FROM sensor_data WHERE is_test = 1 OR bridge_mode = 'mock'"
    ).fetchone()[0]
    sensor_unknown = conn.execute(
        "SELECT COUNT(*) FROM sensor_data WHERE bridge_mode = 'unknown'"
    ).fetchone()[0]
    alarm_mock = conn.execute(
        "SELECT COUNT(*) FROM alarm_log WHERE is_test = 1 OR bridge_mode IN ('mock', 'unknown')"
    ).fetchone()[0]
    sensor_total = conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    alarm_total = conn.execute("SELECT COUNT(*) FROM alarm_log").fetchone()[0]
    return {
        "sensor_mock": sensor_mock,
        "sensor_unknown": sensor_unknown,
        "alarm_mock": alarm_mock,
        "sensor_total": sensor_total,
        "alarm_total": alarm_total,
    }


def clean(conn):
    alarm_del = conn.execute(
        "DELETE FROM alarm_log WHERE is_test = 1 OR bridge_mode IN ('mock', 'unknown')"
    ).rowcount
    sensor_del = conn.execute(
        "DELETE FROM sensor_data WHERE is_test = 1 OR bridge_mode = 'mock'"
    ).rowcount
    conn.commit()
    conn.execute("VACUUM")
    return sensor_del, alarm_del


def main():
    parser = argparse.ArgumentParser(description="清理 mock/test 数据")
    parser.add_argument("--dry-run", action="store_true", help="只统计不删除")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认直接删除")
    parser.add_argument("--db", default=DB, help="数据库路径")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    stats = count_mock(conn)

    print(f"sensor_data: {stats['sensor_total']} 条总计, {stats['sensor_mock']} 条 mock/test, {stats['sensor_unknown']} 条 unknown")
    print(f"alarm_log:   {stats['alarm_total']} 条总计, {stats['alarm_mock']} 条 mock/test/unknown")

    if stats["sensor_mock"] == 0 and stats["alarm_mock"] == 0:
        print("没有需要清理的数据。")
        conn.close()
        return

    if args.dry_run:
        print("[dry-run] 不执行删除。")
        conn.close()
        return

    if not args.yes:
        answer = input(f"将删除 {stats['sensor_mock']} 条 sensor + {stats['alarm_mock']} 条 alarm，确认？[y/N] ")
        if answer.strip().lower() != "y":
            print("已取消。")
            conn.close()
            return

    sensor_del, alarm_del = clean(conn)
    print(f"已删除 sensor_data {sensor_del} 条, alarm_log {alarm_del} 条, 已 VACUUM。")
    conn.close()


if __name__ == "__main__":
    main()
