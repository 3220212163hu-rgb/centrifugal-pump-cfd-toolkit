# -*- coding: utf-8 -*-
"""
Fluent Journal文件生成器——离心泵仿真

生成Fluent TUI journal文件(.jou)，可在Fluent GUI中直接执行。
适用于无PyFluent环境时手动运行仿真。

用法:
    python3 generate_journal.py --output pump_sim.jou --iterations 500
"""

import argparse
import os
from pathlib import Path


def generate_pump_journal(
    output_path="pump_sim.jou",
    case_file="pump.cas.h5",
    iterations=500,
    turb_model="realizable-k-epsilon",
    inlet_pressure=101325.0,
    outlet_pressure=101325.0,
    rotation_speed=2900.0,
    operating_pressure=101325.0,
    save_prefix="pump_result",
):
    """生成离心泵仿真Journal文件。

    Args:
        output_path: 输出.jou文件路径
        case_file: 要读取的case文件
        iterations: 迭代次数
        turb_model: 湍流模型
        inlet_pressure: 进口总压(Pa)
        outlet_pressure: 出口静压(Pa)
        rotation_speed: 转速(rpm)
        operating_pressure: 操作压力(Pa)
        save_prefix: 保存结果文件前缀
    """
    # 转速转换为rad/s
    omega = rotation_speed * 2 * 3.14159 / 60.0

    lines = [
        "; ====== 离心泵稳态仿真 Journal文件 ======",
        "; 生成时间: 自动",
        f"; 湍流模型: {turb_model}",
        f"; 转速: {rotation_speed} rpm",
        f"; 迭代次数: {iterations}",
        "; ==========================================",
        "",
        "; 1. 读取Case文件",
        f'/file/read-case "{case_file}"',
        "  yes",
        "",
        "; 2. 设置求解器：压力基、稳态",
        "/solve/set/pressure-based",
        "/solve/set/steady",
        "",
    ]

    # 湍流模型
    if turb_model == "realizable-k-epsilon":
        lines.extend([
            "; 3. 设置湍流模型：Realizable k-epsilon + Enhanced Wall Treatment",
            "/define/models/viscous/realizable yes",
            "/define/models/viscous/near-wall-treatment enhanced-wall-treatment yes",
            "",
        ])
    elif turb_model == "sst-k-omega":
        lines.extend([
            "; 3. 设置湍流模型：SST k-omega",
            "/define/models/viscous/k-omega sst yes",
            "",
        ])
    elif turb_model == "standard-k-epsilon":
        lines.extend([
            "; 3. 设置湍流模型：Standard k-epsilon",
            "/define/models/viscous/standard yes",
            "",
        ])

    lines.extend([
        "; 4. 设置材料：水-液态",
        '/define/materials/copy-fluid-database "water-liquid" "water-liquid"',
        "",
        "; 5. 设置操作条件",
        f"/define/operating-conditions/pressure {operating_pressure}",
        "; 如需重力: /define/operating-conditions/gravity yes 0 -9.81 0",
        "",
        "; 6. 设置边界条件（zone名需根据实际网格修改）",
        f'; /define/boundary-conditions/pressure-inlet "inlet" {inlet_pressure} 0',
        f'; /define/boundary-conditions/pressure-outlet "outlet" {outlet_pressure}',
        "; /define/boundary-conditions/wall \"impeller\" moving-frame yes ...",
        "",
        "; 7. 设置MRF旋转区域（zone名需修改）",
        f'; /define/cell-zone-conditions/fluid "impeller-zone" rotating yes',
        f";   rotation-speed {omega} rotation-axis 0 0 1",
        "",
        "; 8. 设置残差监视",
        "/solve/monitors/residual plot yes",
        "/solve/monitors/residual convergence-criteria 1e-5 1e-5 1e-5 1e-5 1e-5 1e-5",
        "",
        "; 9. 初始化流场",
        "/solve/initialize/hybrid-initialization",
        "",
        "; 10. 计算迭代",
        f"/solve/iterate {iterations}",
        "",
        "; 11. 保存结果",
        f'/file/write-case-data "{save_prefix}.cas.h5"',
        "",
        "; 12. 导出报告（可选）",
        "; /report/fluxes/mass-flow inlet (),",
        "; /report/surface-integrals/area-average inlet pressure (),",
        "",
        "; ====== 仿真结束 ======",
    ])

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[INFO] Journal文件已生成: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="生成Fluent Journal文件")
    parser.add_argument("--output", default="pump_sim.jou", help="输出文件路径")
    parser.add_argument("--case", default="pump.cas.h5", help="Case文件路径")
    parser.add_argument("--iterations", type=int, default=500, help="迭代次数")
    parser.add_argument("--turb-model", default="realizable-k-epsilon",
                        help="湍流模型")
    parser.add_argument("--inlet-p", type=float, default=101325, help="进口总压")
    parser.add_argument("--outlet-p", type=float, default=101325, help="出口静压")
    parser.add_argument("--rpm", type=float, default=2900, help="转速(rpm)")
    parser.add_argument("--save-prefix", default="pump_result", help="保存文件前缀")

    args = parser.parse_args()
    generate_pump_journal(
        output_path=args.output,
        case_file=args.case,
        iterations=args.iterations,
        turb_model=args.turb_model,
        inlet_pressure=args.inlet_p,
        outlet_pressure=args.outlet_p,
        rotation_speed=args.rpm,
        save_prefix=args.save_prefix,
    )


if __name__ == "__main__":
    main()
