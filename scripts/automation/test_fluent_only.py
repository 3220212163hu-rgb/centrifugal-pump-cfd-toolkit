# -*- coding: utf-8 -*-
"""
Test PyFluent solve chain with existing mesh
Read .cas.h5 -> solve RANS -> extract H and eta
"""
import sys
sys.path.insert(0, r"D:\AI\SJK\biyesheji\venv_pyfluent_win\Lib\site-packages")

import ansys.fluent.core as pyfluent

MESH_FILE = r"D:\AI\SJK\biyesheji\04-results\FFF_1.1.cas.h5"
OUTPUT_DIR = r"D:\AI\SJK\biyesheji\04-results"

print("Launching Fluent ...")
session = pyfluent.launch_fluent(
    version="3d",
    precision="double",
    processor_count=4,
    mode="solver",
    show_gui=False,
)

print("Reading mesh:", MESH_FILE)
session.file.read_case(file_name=MESH_FILE)

print("Mesh check ...")
session.mesh.check()

print("Setting up physics ...")
session.setup.models.viscous.model = "k-omega"
session.setup.models.viscous.k_omega_model = "sst"

print("Initializing ...")
session.solution.initialization.hybrid_initialize()

print("Iterating 50 steps (quick test) ...")
session.solution.run_calculation.iterate(iter_count=50)

print("Extracting results ...")
# Simple report
report = session.solution.report_definitions
print("Available reports:", dir(report))

print("\nDONE. Session active. Check manually or add post-processing.")
session.exit()
