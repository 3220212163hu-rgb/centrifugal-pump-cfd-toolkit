"""
PyFluent: 单流道周期性 RANS 求解 (k-omega SST)
运行: python 03_fluent_solve.py
端到端链路 - 单case测试 (C04_Z5_Beta30)

设计点: Qd=18 m³/h, Hd=4 m, n=900 r/min
"""
import os
import csv
import ansys.fluent.core as pyfluent

# ========= 配置 =========
CASE_NAME    = os.environ.get("CASE_NAME", "test_C04")
WORK_DIR     = os.environ.get(
    "WORK_DIR",
    os.path.join(os.path.dirname(__file__), "..", "output", CASE_NAME)
)
MESH_FILE    = os.path.join(WORK_DIR, f"{CASE_NAME}.gtm")
RESULT_CSV   = os.path.join(WORK_DIR, "result.csv")

Q_M3H        = 18.0
N_RPM        = 900.0
Z_BLADES     = 5
RHO          = 998.2
G            = 9.81
D2           = 0.180  # m

# ========= 启动 Fluent =========
session = pyfluent.launch_fluent(
    version="3d",
    precision="double",
    processor_count=4,
    mode="solver",
    show_gui=False,
)

# ========= 读网格 =========
session.tui.file.read_case(MESH_FILE)
session.tui.mesh.check()
session.tui.mesh.repair_improve.repair()

# ========= 物理模型 =========
session.tui.define.models.viscous.kw_sst("yes")
session.tui.define.materials.copy("fluid", "water-liquid")
session.tui.define.boundary_conditions.fluid("*", "yes", "water-liquid",
    "no", "no", "no", "no", "no", "no", "no",
    "yes", "1", str(N_RPM/60.0*2*3.14159), "no", "0", "no", "0",
    "no", "no", "no", "no", "no", "no", "no")

# ========= 边界 =========
# 周期: 5叶片 -> 1/Z 单流道
mass_flow = RHO * (Q_M3H/3600.0) / Z_BLADES  # 单流道质量流量

session.tui.define.boundary_conditions.modify_zones.zone_type("inlet", "mass-flow-inlet")
session.tui.define.boundary_conditions.mass_flow_inlet("inlet",
    "yes", "no", str(mass_flow), "no", "0", "no", "300", "no", "yes",
    "no", "no", "yes", "5", "10")

session.tui.define.boundary_conditions.modify_zones.zone_type("outlet", "pressure-outlet")
session.tui.define.boundary_conditions.pressure_outlet("outlet",
    "yes", "no", "0", "no", "300", "no", "yes", "no", "no", "no",
    "yes", "5", "10", "yes")

# ========= 求解控制 =========
session.tui.solve.set.discretization_scheme.pressure("12")
session.tui.solve.set.discretization_scheme.mom("1")
session.tui.solve.set.discretization_scheme.k("1")
session.tui.solve.set.discretization_scheme.omega("1")
session.tui.solve.set.p_v_coupling("24")  # Coupled

session.tui.solve.monitors.residual.convergence_criteria(
    "1e-5", "1e-5", "1e-5", "1e-5", "1e-5", "1e-5")

# ========= 初始化 + 迭代 =========
session.tui.solve.initialize.hyb_initialization()
session.tui.solve.iterate(800)

# ========= 后处理: 扬程+效率 =========
p_in  = session.scheme_eval.scheme_eval('(ti-menu-load-string "report/surface-integrals/area-weighted-avg inlet () pressure no")')
p_out = session.scheme_eval.scheme_eval('(ti-menu-load-string "report/surface-integrals/area-weighted-avg outlet () pressure no")')
torque = session.scheme_eval.scheme_eval('(ti-menu-load-string "report/forces/wall-moments * 0 0 1 () no")')

# 解析数值（Fluent输出格式依赖版本，可能需调整）
def parse_num(s):
    import re
    m = re.search(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?", str(s))
    return float(m.group()) if m else 0.0

dp = parse_num(p_out) - parse_num(p_in)  # Pa
H  = dp / (RHO * G)
T  = parse_num(torque) * Z_BLADES        # 整圆扭矩 N·m
P_shaft = T * (N_RPM/60.0) * 2*3.14159
P_water = RHO * G * (Q_M3H/3600.0) * H
eta = P_water / P_shaft if P_shaft > 0 else 0.0

# ========= 保存 =========
session.tui.file.write_case_data(os.path.join(WORK_DIR, f"{CASE_NAME}.cas.h5"))

with open(RESULT_CSV, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["case","Z","beta2","Q_m3h","H_m","eta","P_shaft_W","T_Nm"])
    w.writerow([CASE_NAME, Z_BLADES, 30, Q_M3H, f"{H:.4f}", f"{eta:.4f}",
                f"{P_shaft:.2f}", f"{T:.4f}"])

print(f"\n========= {CASE_NAME} 完成 =========")
print(f"H     = {H:.3f} m   (target 4.0)")
print(f"eta   = {eta*100:.2f} %")
print(f"P_shaft = {P_shaft:.1f} W")

session.exit()
