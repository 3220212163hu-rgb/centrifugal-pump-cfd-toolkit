================================================================
  离心泵 CFD 模拟 — Workbench 项目交付包
  课题：基于节能优化的离心泵叶轮 β₂–Z 双参数设计与仿真
  模型：β₂=22°, Z=6（基准叶轮）, 130W 网格
================================================================

【快速开始】
  1. 将整个 ONE_! 文件夹解压到英文路径（路径不能有中文）
  2. 双击 ONE.wbpj → ANSYS Workbench 打开项目
  3. 在 Workbench 中可查看：
     - 几何结构（Geometry）→ 双击查看叶轮+蜗壳模型
     - 网格（Mesh）→ 双击查看 130W 网格划分
     - 设置（Setup）→ 双击打开 Fluent，查看模型设置

【查看后处理结果（重要）】
  由于计算是通过 PyFluent 外部完成的，Workbench 的 Solution/Results 
  组件不包含结果数据。查看收敛结果请按以下步骤：

  方法一：从 Workbench 进入
    ① 在 Workbench 中双击 "设置 (Setup)" → Fluent 启动
    ② Fluent 菜单：File → Read → Case & Data...
    ③ 选择 results/Z6_B22_Q20.cas.h5 + Z6_B22_Q20.dat.h5
    ④ 加载后直接在 Fluent 中操作：
       - Results → Graphics → Contours（云图）
       - Results → Graphics → Vectors（矢量图）
       - Results → Reports → Surface Integrals（面积分）

  方法二：独立启动 Fluent
    ① 启动 ANSYS Fluent (3D, Double Precision, Serial)
    ② File → Read → Case & Data...
    ③ 选择 results/ 下的 cas+dat 文件


【文件清单】

  ONE.wbpj                     Workbench 项目文件（双击打开）
  ONE_files/                   项目数据（几何、网格、设置）

  results/                     收敛的仿真结果
    ├── Z6_B22_Q8.cas.h5  + .dat.h5     (Q=8 m³/h)
    ├── Z6_B22_Q12.cas.h5 + .dat.h5     (Q=12 m³/h)
    ├── Z6_B22_Q16.cas.h5 + .dat.h5     (Q=16 m³/h)
    ├── Z6_B22_Q20.cas.h5 + .dat.h5     (Q=20 m³/h，设计工况)
    ├── Z6_B22_Q24.cas.h5 + .dat.h5     (Q=24 m³/h)
    ├── images/                          已导出的云图（8张PNG）
    └── csv/                             中截面数据（4个CSV）

  加载脚本（附在 results/ 下）：
    └── load_*.jou                  Fluent Journal 一键加载脚本


【模型参数】

  叶轮：
    进口直径 D₁ = 65 mm      出口直径 D₂ = 180 mm
    出口宽度 b₂ = 18 mm       叶片数 Z = 6
    出口安放角 β₂ = 22°       进口安放角 β₁ = 18°
    转速 n = 900 rpm

  设计工况：Qd = 18 m³/h, Hd = 4 m

  CFD 设置：
    介质：water-liquid (ρ=998.2 kg/m³)
    湍流模型：k-ω SST
    求解器：Steady, Pressure-Based, Double Precision
    旋转域：MRF, ω = -94.25 rad/s
    进口：Mass Flow Inlet
    出口：Pressure Outlet (Gauge = 0 Pa)
    网格：约 130 万 cells (Poly-Hexcore)


【后处理操作示例】

  ■ 压力云图（叶片壁面）：
    Results → Graphics → Contours → New...
    → Contours of: Pressure → Static Pressure
    → Surfaces: yepian → 勾选 Filled → Display

  ■ 进出口扬程计算：
    Results → Reports → Surface Integrals → Area-Weighted Average
    → Field: Pressure → Total Pressure
    → Surfaces: 先选 inlet 记录 p_in, 再选 outlet 记录 p_out
    → H = (p_out - p_in) / (998.2 × 9.81)  [m]

  ■ 中截面云图（轴面）：
    先创建截面：Domain → Surface → Create → Plane...
    → Method: XY Plane → 选择合适的 Z 位置
    → 然后对该截面画云图


【注意事项】
  ● ANSYS 版本要求：2024 R2（必须，否则可能打不开）
  ● 路径不能包含中文字符
  ● 首次加载 .dat.h5 时 Fluent 可能提示，选 Yes 继续
  ● 所有工况均已完全收敛（残差 < 1×10⁻⁴）
  ● Q=20 m³/h 是最接近设计工况 Qd=18 m³/h 的实际计算点
  ● 如果需重新计算，可在 Workbench 中右键 Solution → Update
    （需要正确配置 MRF、材料、边界条件等）


================================================================
  如有问题，联系项目作者获取支持
================================================================
